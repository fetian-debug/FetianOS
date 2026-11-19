//! Single-writer durable transactions. Raw SQL never reaches executors or the CLI.
use crate::error::{Error, Result};
use crate::model::*;
use rusqlite::{
    params, Connection, OpenFlags, OptionalExtension, Transaction, TransactionBehavior,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fs::{self, OpenOptions};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt, PermissionsExt};
use std::path::Path;
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Credential {
    pub executor_id: ExecutorId,
    pub lease_id: String,
    pub epoch: u64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Progress {
    pub sequence: u64,
    pub input_position: usize,
    pub next_input_position: usize,
    pub accumulated_result: i64,
    pub idempotency_key: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommitOutcome {
    pub effect_id: String,
    pub sequence: u64,
    pub checkpoint: ContinuationState,
}

pub struct Store {
    connection: Connection,
}

fn load(connection: &Connection, id: &str) -> Result<ContinuationAuthority> {
    AuthorityId::try_from(id.to_owned())?;
    let value: Option<String> = connection
        .query_row(
            "SELECT document FROM authorities WHERE id=?1",
            [id],
            |row| row.get(0),
        )
        .optional()?;
    let authority: ContinuationAuthority = serde_json::from_str(
        &value.ok_or_else(|| Error::new("AUTHORITY_NOT_FOUND", "Unknown authority"))?,
    )?;
    authority.contract.validate()?;
    if authority.id.as_str() != id || authority.continuation.schema_version != 1 {
        return Err(Error::new(
            "STORE_CORRUPT",
            "Authority/checkpoint identity or version mismatch",
        ));
    }
    Ok(authority)
}
fn save(transaction: &Transaction<'_>, authority: &ContinuationAuthority) -> Result<()> {
    transaction.execute(
        "UPDATE authorities SET document=?2 WHERE id=?1",
        params![authority.id.as_str(), serde_json::to_string(authority)?],
    )?;
    Ok(())
}
fn event(
    transaction: &Transaction<'_>,
    authority: &ContinuationAuthority,
    kind: &str,
    details: Value,
) -> Result<()> {
    let last: Option<(i64, String)> = transaction
        .query_row(
            "SELECT sequence,hash FROM events WHERE authority_id=?1 ORDER BY sequence DESC LIMIT 1",
            [authority.id.as_str()],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .optional()?;
    let (sequence, previous) = last.map_or((1, "0".repeat(64)), |(seq, digest)| (seq + 1, digest));
    if sequence > 100_000 {
        return Err(Error::new("JOURNAL_LIMIT", "Prototype event limit reached"));
    }
    let payload = serde_json::to_string(
        &json!({"schema_version":1,"authority_id":authority.id,"sequence":sequence,"epoch":authority.epoch,"kind":kind,"at":timestamp(),"details":details}),
    )?;
    let digest = hash(format!("FCA-EVENT-v1\0{previous}\n{payload}").as_bytes());
    transaction.execute(
        "INSERT INTO events VALUES (?1,?2,?3,?4,?5,?6)",
        params![
            authority.id.as_str(),
            sequence,
            kind,
            payload,
            previous,
            digest
        ],
    )?;
    Ok(())
}
fn transition(
    transaction: &Transaction<'_>,
    authority: &mut ContinuationAuthority,
    next: Lifecycle,
) -> Result<()> {
    let previous = authority.lifecycle;
    authority.transition(next)?;
    event(
        transaction,
        authority,
        "LifecycleTransition",
        json!({"from":previous,"to":next}),
    )
}
fn input(connection: &Connection, reference: &str) -> Result<Vec<i64>> {
    let bytes: Option<Vec<u8>> = connection
        .query_row(
            "SELECT content FROM inputs WHERE id=?1",
            [reference],
            |row| row.get(0),
        )
        .optional()?;
    let bytes = bytes
        .ok_or_else(|| Error::new("INPUT_MISSING", "Managed immutable input is unavailable"))?;
    if format!("sha256:{}", hash(&bytes)) != reference {
        return Err(Error::new(
            "INPUT_CORRUPT",
            "Immutable input digest mismatch",
        ));
    }
    parse_input(&bytes)
}
fn grant(
    authority: &ContinuationAuthority,
    credential: &Credential,
    capability: &str,
) -> Result<()> {
    // Epoch precedence is intentional: even a completed authority rejects an old
    // generation with STALE_EPOCH rather than allowing an idempotent replay.
    if credential.epoch != authority.epoch {
        return Err(Error::new(
            "STALE_EPOCH",
            "Executor generation has been fenced",
        ));
    }
    if authority.lifecycle.terminal() {
        return Err(Error::new("TERMINAL_AUTHORITY", "Authority is terminal"));
    }
    let lease = authority
        .current_executor
        .as_ref()
        .ok_or_else(|| Error::new("LEASE_REVOKED", "No current lease"))?;
    if lease.lease_id != credential.lease_id
        || lease.executor_id != credential.executor_id
        || lease.epoch != credential.epoch
    {
        return Err(Error::new(
            "LEASE_REVOKED",
            "Lease/executor does not match current grant",
        ));
    }
    if authority.lifecycle != Lifecycle::Running {
        return Err(Error::new("INVALID_STATE", "Executor is not running"));
    }
    if !authority
        .contract
        .capabilities
        .iter()
        .any(|value| value == capability)
    {
        return Err(Error::new("CAPABILITY_DENIED", "Operation is not granted"));
    }
    Ok(())
}

impl Store {
    pub fn open(path: &Path) -> Result<Self> {
        for candidate in [
            path.to_path_buf(),
            path.with_extension("sqlite3-wal"),
            path.with_extension("sqlite3-shm"),
        ] {
            if let Ok(info) = fs::symlink_metadata(&candidate) {
                if !info.is_file()
                    || info.uid() != nix::unistd::getuid().as_raw()
                    || info.mode() & 0o077 != 0
                {
                    return Err(Error::new(
                        "UNSAFE_STORE_PATH",
                        "Store files must be private regular files owned by this user",
                    ));
                }
            }
        }
        if !path.exists() {
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .custom_flags(nix::libc::O_NOFOLLOW)
                .open(path)?;
        }
        let connection = Connection::open_with_flags(
            path,
            OpenFlags::SQLITE_OPEN_READ_WRITE
                | OpenFlags::SQLITE_OPEN_CREATE
                | OpenFlags::SQLITE_OPEN_NO_MUTEX
                | OpenFlags::SQLITE_OPEN_NOFOLLOW,
        )?;
        connection.busy_timeout(Duration::from_secs(2))?;
        connection.pragma_update(None, "journal_mode", "WAL")?;
        connection.pragma_update(None, "synchronous", "FULL")?;
        connection.pragma_update(None, "foreign_keys", true)?;
        connection.pragma_update(None, "wal_autocheckpoint", 64)?;
        connection.pragma_update(None, "max_page_count", 65536)?;
        let version: i64 = connection.pragma_query_value(None, "user_version", |row| row.get(0))?;
        if version != 0 && version != 1 {
            return Err(Error::new(
                "UNSUPPORTED_STORE_VERSION",
                "Explicit schema migration is required",
            ));
        }
        connection.execute_batch("BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS inputs(id TEXT PRIMARY KEY,content BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS authorities(id TEXT PRIMARY KEY,document TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(authority_id TEXT NOT NULL REFERENCES authorities(id),sequence INTEGER NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(authority_id,sequence));
            CREATE TABLE IF NOT EXISTS effects(authority_id TEXT NOT NULL REFERENCES authorities(id),sequence INTEGER NOT NULL,effect_id TEXT NOT NULL UNIQUE,epoch INTEGER NOT NULL,operation_key TEXT NOT NULL,request_digest TEXT NOT NULL,outcome TEXT NOT NULL,committed_at INTEGER NOT NULL,PRIMARY KEY(authority_id,sequence),UNIQUE(authority_id,operation_key));
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
            CREATE TRIGGER IF NOT EXISTS effects_no_update BEFORE UPDATE ON effects BEGIN SELECT RAISE(ABORT,'append only'); END;
            CREATE TRIGGER IF NOT EXISTS effects_no_delete BEFORE DELETE ON effects BEGIN SELECT RAISE(ABORT,'append only'); END;
            CREATE TRIGGER IF NOT EXISTS inputs_no_update BEFORE UPDATE ON inputs BEGIN SELECT RAISE(ABORT,'immutable'); END;
            CREATE TRIGGER IF NOT EXISTS inputs_no_delete BEFORE DELETE ON inputs BEGIN SELECT RAISE(ABORT,'immutable'); END;
            PRAGMA user_version=1; COMMIT;")?;
        fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
        let store = Self { connection };
        let integrity: String =
            store
                .connection
                .query_row("PRAGMA integrity_check", [], |row| row.get(0))?;
        if integrity != "ok" {
            return Err(Error::new("STORE_CORRUPT", "SQLite integrity check failed"));
        }
        let journal: String = store
            .connection
            .pragma_query_value(None, "journal_mode", |row| row.get(0))?;
        let synchronous: i64 = store
            .connection
            .pragma_query_value(None, "synchronous", |row| row.get(0))?;
        if journal != "wal" || synchronous != 2 {
            return Err(Error::new(
                "DURABILITY_UNAVAILABLE",
                "WAL and synchronous FULL are required",
            ));
        }
        for authority in store.list()? {
            store.verify(authority.id.as_str())?;
        }
        Ok(store)
    }
    pub fn import(&mut self, bytes: &[u8]) -> Result<String> {
        parse_input(bytes)?;
        let reference = format!("sha256:{}", hash(bytes));
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        transaction.execute(
            "INSERT OR IGNORE INTO inputs VALUES (?1,?2)",
            params![reference, bytes],
        )?;
        let _ = input(&transaction, &reference)?;
        transaction.commit()?;
        Ok(reference)
    }
    pub fn create(
        &mut self,
        id: AuthorityId,
        contract: ExecutionContract,
    ) -> Result<ContinuationAuthority> {
        contract.validate()?;
        input(&self.connection, &contract.input.id)?;
        if self.list()?.len() >= 64 {
            return Err(Error::new(
                "AUTHORITY_LIMIT",
                "Prototype authority limit reached",
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let exists: bool = transaction.query_row(
            "SELECT EXISTS(SELECT 1 FROM authorities WHERE id=?1)",
            [id.as_str()],
            |row| row.get(0),
        )?;
        if exists {
            return Err(Error::new(
                "AUTHORITY_EXISTS",
                "Authority identity already exists",
            ));
        }
        let mut authority = ContinuationAuthority {
            id,
            contract,
            lifecycle: Lifecycle::Created,
            epoch: 0,
            continuation: ContinuationState::initial(),
            current_executor: None,
            previous_executors: Vec::new(),
        };
        transaction.execute(
            "INSERT INTO authorities VALUES (?1,?2)",
            params![authority.id.as_str(), serde_json::to_string(&authority)?],
        )?;
        event(
            &transaction,
            &authority,
            "AuthorityCreated",
            json!({"contract_digest":hash(&serde_json::to_vec(&authority.contract)?)}),
        )?;
        transition(&transaction, &mut authority, Lifecycle::Validated)?;
        event(&transaction, &authority, "ContractValidated", json!({}))?;
        transition(&transaction, &mut authority, Lifecycle::Ready)?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(authority)
    }
    pub fn get(&self, id: &str) -> Result<ContinuationAuthority> {
        load(&self.connection, id)
    }
    pub fn list(&self) -> Result<Vec<ContinuationAuthority>> {
        let mut statement = self
            .connection
            .prepare("SELECT id FROM authorities ORDER BY id")?;
        let ids = statement
            .query_map([], |row| row.get::<_, String>(0))?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        ids.iter().map(|id| self.get(id)).collect()
    }
    pub fn issue_lease(&mut self, id: &str, executor: ExecutorId) -> Result<LeaseRecord> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        if !authority.contract.permitted_executors.contains(&executor) {
            return Err(Error::new(
                "EXECUTOR_NOT_ALLOWED",
                "Executor is incompatible or not permitted",
            ));
        }
        if authority.lifecycle != Lifecycle::Ready || authority.current_executor.is_some() {
            return Err(Error::new(
                "INVALID_STATE",
                "Authority is not ready for a new lease",
            ));
        }
        if authority.epoch == 0 {
            authority.advance_epoch()?;
        }
        let lease = LeaseRecord {
            executor_id: executor,
            lease_id: new_id("lease")?,
            epoch: authority.epoch,
            issued_at: timestamp(),
            pid: None,
            process_start_ticks: None,
        };
        authority.current_executor = Some(lease.clone());
        transition(&transaction, &mut authority, Lifecycle::Leased)?;
        event(
            &transaction,
            &authority,
            "LeaseGranted",
            json!({"executor_id":executor,"issued_at":lease.issued_at,"lease_digest":hash(&serde_json::to_vec(&lease)?)}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(lease)
    }
    pub fn started(&mut self, id: &str, pid: u32, start_ticks: u64) -> Result<()> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        let lease = authority
            .current_executor
            .as_mut()
            .ok_or_else(|| Error::new("LEASE_REVOKED", "No starting executor"))?;
        lease.pid = Some(pid);
        lease.process_start_ticks = Some(start_ticks);
        transition(&transaction, &mut authority, Lifecycle::Running)?;
        event(
            &transaction,
            &authority,
            "ExecutorStarted",
            json!({"pid":pid,"process_start_ticks":start_ticks}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(())
    }
    pub fn read_chunk(&self, id: &str, credential: &Credential, position: usize) -> Result<Value> {
        let authority = self.get(id)?;
        grant(&authority, credential, "input.read")?;
        if position != authority.continuation.next_input_position {
            return Err(Error::new(
                "INVALID_POSITION",
                "Read must start at the committed continuation",
            ));
        }
        let values = input(&self.connection, &authority.contract.input.id)?;
        if position > values.len() {
            return Err(Error::new(
                "CHECKPOINT_CORRUPT",
                "Cursor exceeds managed input",
            ));
        }
        let end = (position + authority.contract.chunk_size).min(values.len());
        Ok(
            json!({"values":&values[position..end],"input_position":position,"next_input_position":end,"total_items":values.len()}),
        )
    }
    pub fn inspect_executor(&self, id: &str, credential: &Credential) -> Result<ContinuationState> {
        let authority = self.get(id)?;
        grant(&authority, credential, "authority.inspect")?;
        Ok(authority.continuation)
    }
    pub fn commit(
        &mut self,
        id: &str,
        credential: &Credential,
        progress: &Progress,
        fail_before_commit: bool,
    ) -> Result<CommitOutcome> {
        self.commit_with_hook(id, credential, progress, fail_before_commit, || {})
    }
    pub fn commit_with_hook(
        &mut self,
        id: &str,
        credential: &Credential,
        progress: &Progress,
        fail_before_commit: bool,
        before_commit: impl FnOnce(),
    ) -> Result<CommitOutcome> {
        self.commit_with_stage_hooks(
            id,
            credential,
            progress,
            fail_before_commit,
            || {},
            before_commit,
        )
    }
    /// Research fault boundaries; normal admission supplies no-op callbacks.
    pub fn commit_with_stage_hooks(
        &mut self,
        id: &str,
        credential: &Credential,
        progress: &Progress,
        fail_before_commit: bool,
        after_effect_insert: impl FnOnce(),
        before_commit: impl FnOnce(),
    ) -> Result<CommitOutcome> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        grant(&authority, credential, "result.commit")?;
        grant(&authority, credential, "checkpoint.commit")?;
        if progress.idempotency_key != format!("chunk-{}", progress.sequence) {
            return Err(Error::new(
                "INVALID_IDEMPOTENCY_KEY",
                "Use the semantic chunk identity",
            ));
        }
        let request_digest = hash(&serde_json::to_vec(progress)?);
        let previous: Option<(String, String)> = transaction.query_row("SELECT request_digest,outcome FROM effects WHERE authority_id=?1 AND operation_key=?2", params![id, progress.idempotency_key], |row| Ok((row.get(0)?, row.get(1)?))).optional()?;
        if let Some((digest, outcome)) = previous {
            if digest != request_digest {
                return Err(Error::new(
                    "IDEMPOTENCY_CONFLICT",
                    "Committed operation key was reused with different content",
                ));
            }
            return Ok(serde_json::from_str(&outcome)?);
        }
        let values = input(&transaction, &authority.contract.input.id)?;
        let old = &authority.continuation;
        let end = (old.next_input_position + authority.contract.chunk_size).min(values.len());
        if old.next_input_position >= values.len()
            || progress.sequence != old.last_committed_chunk + 1
            || progress.input_position != old.next_input_position
            || progress.next_input_position != end
        {
            return Err(Error::new(
                "INVALID_SEQUENCE",
                "Progress does not extend exactly the next input chunk",
            ));
        }
        let mut expected = old.accumulated_result;
        for value in &values[old.next_input_position..end] {
            expected = expected
                .checked_add(*value)
                .ok_or_else(|| Error::new("SUM_OVERFLOW", "Signed 64-bit accumulation overflow"))?;
        }
        if progress.accumulated_result != expected {
            return Err(Error::new(
                "INVALID_RESULT",
                "Executor result does not match workload semantics",
            ));
        }
        transition(&transaction, &mut authority, Lifecycle::Checkpointing)?;
        authority.continuation = ContinuationState {
            schema_version: 1,
            next_input_position: end,
            accumulated_result: expected,
            last_committed_chunk: progress.sequence,
        };
        let outcome = CommitOutcome {
            effect_id: new_id("effect")?,
            sequence: progress.sequence,
            checkpoint: authority.continuation.clone(),
        };
        transaction.execute(
            "INSERT INTO effects VALUES (?1,?2,?3,?4,?5,?6,?7,?8)",
            params![
                id,
                progress.sequence as i64,
                outcome.effect_id,
                authority.epoch as i64,
                progress.idempotency_key,
                request_digest,
                serde_json::to_string(&outcome)?,
                timestamp() as i64
            ],
        )?;
        after_effect_insert();
        event(
            &transaction,
            &authority,
            "EffectCommitted",
            json!({"effect_id":outcome.effect_id,"sequence":progress.sequence,"request_digest":request_digest}),
        )?;
        event(
            &transaction,
            &authority,
            "CheckpointCommitted",
            serde_json::to_value(&authority.continuation)?,
        )?;
        transition(&transaction, &mut authority, Lifecycle::Running)?;
        save(&transaction, &authority)?;
        if fail_before_commit {
            return Err(Error::new(
                "INJECTED_FAILURE",
                "Transaction rolled back before commit",
            ));
        }
        before_commit();
        transaction.commit()?;
        Ok(outcome)
    }
    pub fn begin_revoke(&mut self, id: &str, reason: &str) -> Result<Option<LeaseRecord>> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        event(
            &transaction,
            &authority,
            "HandoffStarted",
            json!({"reason":reason}),
        )?;
        transition(&transaction, &mut authority, Lifecycle::Revoking)?;
        let previous = authority.current_executor.take();
        if let Some(lease) = &previous {
            authority.previous_executors.push(lease.clone());
            if authority.previous_executors.len() > 64 {
                authority.previous_executors.remove(0);
            }
            event(
                &transaction,
                &authority,
                "LeaseRevoked",
                json!({"executor_id":lease.executor_id,"revoked_epoch":lease.epoch}),
            )?;
        }
        authority.advance_epoch()?;
        event(
            &transaction,
            &authority,
            "EpochAdvanced",
            json!({"epoch":authority.epoch}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(previous)
    }
    pub fn finish_revoke(&mut self, id: &str, next: Lifecycle) -> Result<()> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        if authority.lifecycle != Lifecycle::Revoking {
            return Err(Error::new("INVALID_STATE", "No revocation in progress"));
        }
        transition(&transaction, &mut authority, next)?;
        event(
            &transaction,
            &authority,
            "ExecutorExited",
            json!({"continuation":authority.continuation}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(())
    }
    pub fn set_idle_state(&mut self, id: &str, next: Lifecycle) -> Result<()> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        if authority.current_executor.is_some() {
            return Err(Error::new(
                "INVALID_STATE",
                "An executor must be revoked first",
            ));
        }
        transition(&transaction, &mut authority, next)?;
        event(
            &transaction,
            &authority,
            match next {
                Lifecycle::Cancelled => "AuthorityCancelled",
                Lifecycle::Suspended => "AuthoritySuspended",
                _ => "AuthorityReady",
            },
            json!({}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(())
    }
    pub fn checkpoint(&mut self, id: &str) -> Result<ContinuationState> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let authority = load(&transaction, id)?;
        if !matches!(
            authority.lifecycle,
            Lifecycle::Ready | Lifecycle::Running | Lifecycle::Suspended
        ) {
            return Err(Error::new(
                "INVALID_STATE",
                "Checkpoint barrier requires a nonterminal available authority",
            ));
        }
        event(
            &transaction,
            &authority,
            "CheckpointCommitted",
            json!({"barrier":true,"continuation":authority.continuation}),
        )?;
        transaction.commit()?;
        Ok(authority.continuation)
    }
    pub fn complete(&mut self, id: &str, credential: &Credential) -> Result<i64> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        grant(&authority, credential, "result.commit")?;
        if authority.continuation.next_input_position
            != input(&transaction, &authority.contract.input.id)?.len()
        {
            return Err(Error::new(
                "INCOMPLETE",
                "Managed input has not been fully committed",
            ));
        }
        transition(&transaction, &mut authority, Lifecycle::Completed)?;
        if let Some(previous) = authority.current_executor.take() {
            authority.previous_executors.push(previous);
        }
        authority.advance_epoch()?;
        event(
            &transaction,
            &authority,
            "EpochAdvanced",
            json!({"epoch":authority.epoch}),
        )?;
        event(
            &transaction,
            &authority,
            "AuthorityCompleted",
            json!({"result":authority.continuation.accumulated_result}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(authority.continuation.accumulated_result)
    }
    pub fn audit(&mut self, id: &str, kind: &str, details: Value) -> Result<()> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let authority = load(&transaction, id)?;
        event(&transaction, &authority, kind, details)?;
        transaction.commit()?;
        Ok(())
    }
    pub fn recover(&mut self, id: &str, orphaned: bool) -> Result<()> {
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)?;
        let mut authority = load(&transaction, id)?;
        if authority.lifecycle.terminal() {
            return Ok(());
        }
        let was_suspended = authority.lifecycle == Lifecycle::Suspended;
        event(&transaction, &authority, "RecoveryStarted", json!({}))?;
        if let Some(previous) = authority.current_executor.take() {
            authority.previous_executors.push(previous);
        }
        if authority.previous_executors.len() > 64 {
            authority.previous_executors.remove(0);
        }
        authority.advance_epoch()?;
        if matches!(
            authority.lifecycle,
            Lifecycle::Leased
                | Lifecycle::Running
                | Lifecycle::Checkpointing
                | Lifecycle::Suspending
        ) {
            transition(&transaction, &mut authority, Lifecycle::Revoking)?;
        }
        transition(&transaction, &mut authority, Lifecycle::Recovering)?;
        event(
            &transaction,
            &authority,
            "EpochAdvanced",
            json!({"epoch":authority.epoch}),
        )?;
        transition(
            &transaction,
            &mut authority,
            if orphaned {
                Lifecycle::Orphaned
            } else if was_suspended {
                Lifecycle::Suspended
            } else {
                Lifecycle::Ready
            },
        )?;
        event(
            &transaction,
            &authority,
            if orphaned {
                "AuthorityOrphaned"
            } else {
                "RecoveryCompleted"
            },
            json!({}),
        )?;
        save(&transaction, &authority)?;
        transaction.commit()?;
        Ok(())
    }
    pub fn events(&self, id: &str, after: u64, limit: usize) -> Result<Vec<Value>> {
        self.get(id)?;
        if limit == 0 || limit > 64 {
            return Err(Error::new(
                "EVENT_LIMIT",
                "Event page must contain 1–64 entries",
            ));
        }
        let mut statement = self.connection.prepare("SELECT payload,previous_hash,hash FROM events WHERE authority_id=?1 AND sequence>?2 ORDER BY sequence LIMIT ?3")?;
        let rows = statement
            .query_map(
                params![id, i64::try_from(after).unwrap_or(i64::MAX), limit as i64],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                    ))
                },
            )?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        rows.into_iter().map(|(payload, previous, digest)| Ok(json!({"event":serde_json::from_str::<Value>(&payload)?,"previous_hash":previous,"hash":digest}))).collect()
    }
    pub fn verify(&self, id: &str) -> Result<Value> {
        let authority = self.get(id)?;
        let values = input(&self.connection, &authority.contract.input.id)?;
        let mut previous = "0".repeat(64);
        let mut count = 0_u64;
        let mut after = 0;
        let mut committed = std::collections::BTreeMap::new();
        let mut lease_grants = std::collections::BTreeMap::new();
        let mut started_processes = std::collections::BTreeMap::new();
        let mut last_epoch = 0_u64;
        let contract_digest = hash(&serde_json::to_vec(&authority.contract)?);
        let mut contract_verified = false;
        let mut lifecycle = Lifecycle::Created;
        loop {
            let page = self.events(id, after, 64)?;
            if page.is_empty() {
                break;
            }
            for record in page {
                count += 1;
                let payload = &record["event"];
                let canonical = serde_json::to_string(payload)?;
                if payload["schema_version"] != 1
                    || payload["authority_id"] != id
                    || payload["sequence"] != count
                    || record["previous_hash"] != previous
                    || record["hash"]
                        != hash(format!("FCA-EVENT-v1\0{previous}\n{canonical}").as_bytes())
                {
                    return Err(Error::new(
                        "JOURNAL_CORRUPT",
                        "Event sequence or hash chain failed verification",
                    ));
                }
                let epoch = payload["epoch"]
                    .as_u64()
                    .ok_or_else(|| Error::new("JOURNAL_CORRUPT", "Invalid epoch"))?;
                if epoch < last_epoch {
                    return Err(Error::new("JOURNAL_CORRUPT", "Epoch regressed"));
                }
                last_epoch = epoch;
                if payload["kind"] == "AuthorityCreated" {
                    if count != 1 || payload["details"]["contract_digest"] != contract_digest {
                        return Err(Error::new(
                            "CONTRACT_CORRUPT",
                            "Contract differs from creation record",
                        ));
                    }
                    contract_verified = true;
                }
                if payload["kind"] == "EffectCommitted" {
                    let sequence = payload["details"]["sequence"]
                        .as_u64()
                        .ok_or_else(|| Error::new("JOURNAL_CORRUPT", "Missing effect sequence"))?;
                    if committed
                        .insert(
                            sequence,
                            (
                                payload["details"]["effect_id"].clone(),
                                payload["details"]["request_digest"].clone(),
                                epoch,
                            ),
                        )
                        .is_some()
                    {
                        return Err(Error::new(
                            "JOURNAL_CORRUPT",
                            "Duplicate committed effect event",
                        ));
                    }
                }
                if payload["kind"] == "LeaseGranted" {
                    lease_grants.insert(epoch, payload["details"]["lease_digest"].clone());
                }
                if payload["kind"] == "ExecutorStarted" {
                    started_processes.insert(epoch, payload["details"].clone());
                }
                if payload["kind"] == "LifecycleTransition" {
                    let from: Lifecycle =
                        serde_json::from_value(payload["details"]["from"].clone())?;
                    let to: Lifecycle = serde_json::from_value(payload["details"]["to"].clone())?;
                    if from != lifecycle || !from.permits(to) {
                        return Err(Error::new("JOURNAL_CORRUPT", "Invalid lifecycle history"));
                    }
                    lifecycle = to;
                }
                previous = record["hash"]
                    .as_str()
                    .ok_or_else(|| Error::new("JOURNAL_CORRUPT", "Invalid hash encoding"))?
                    .to_owned();
                after = count;
            }
        }
        let mut checkpoint = ContinuationState::initial();
        let mut statement = self.connection.prepare("SELECT sequence,outcome,request_digest,epoch FROM effects WHERE authority_id=?1 ORDER BY sequence")?;
        let rows = statement
            .query_map([id], |row| {
                Ok((
                    row.get::<_, i64>(0)? as u64,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, i64>(3)? as u64,
                ))
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        let effects = rows.len();
        if !contract_verified
            || last_epoch != authority.epoch
            || lifecycle != authority.lifecycle
            || committed.len() != effects
        {
            return Err(Error::new(
                "STORE_CORRUPT",
                "Authority/effect ledger does not match audit history",
            ));
        }
        if let Some(lease) = &authority.current_executor {
            if !matches!(lifecycle, Lifecycle::Leased | Lifecycle::Running)
                || lease.epoch != authority.epoch
                || !valid_id(&lease.lease_id, "lease")
            {
                return Err(Error::new("STORE_CORRUPT", "Invalid current lease"));
            }
        } else if matches!(lifecycle, Lifecycle::Leased | Lifecycle::Running) {
            return Err(Error::new("STORE_CORRUPT", "Missing current lease"));
        }
        for lease in authority
            .previous_executors
            .iter()
            .chain(authority.current_executor.iter())
        {
            let mut issued = lease.clone();
            issued.pid = None;
            issued.process_start_ticks = None;
            if lease_grants.get(&lease.epoch) != Some(&json!(hash(&serde_json::to_vec(&issued)?))) {
                return Err(Error::new(
                    "STORE_CORRUPT",
                    "Lease differs from its grant record",
                ));
            }
            if let Some(pid) = lease.pid {
                let expected = json!({"pid":pid,"process_start_ticks":lease.process_start_ticks});
                if started_processes.get(&lease.epoch) != Some(&expected) {
                    return Err(Error::new(
                        "STORE_CORRUPT",
                        "Process identity differs from its start record",
                    ));
                }
            } else if authority
                .current_executor
                .as_ref()
                .is_some_and(|current| current.epoch == lease.epoch)
                && lifecycle == Lifecycle::Running
            {
                return Err(Error::new(
                    "STORE_CORRUPT",
                    "Running executor has no process identity",
                ));
            }
        }
        for (sequence, text, digest, epoch) in rows {
            let outcome: CommitOutcome = serde_json::from_str(&text)?;
            if committed.get(&sequence) != Some(&(json!(outcome.effect_id), json!(digest), epoch)) {
                return Err(Error::new(
                    "STORE_CORRUPT",
                    "Effect does not match its journal event",
                ));
            }
            let end =
                (checkpoint.next_input_position + authority.contract.chunk_size).min(values.len());
            let mut sum = checkpoint.accumulated_result;
            for value in &values[checkpoint.next_input_position..end] {
                sum = sum
                    .checked_add(*value)
                    .ok_or_else(|| Error::new("CHECKPOINT_CORRUPT", "Stored result overflows"))?;
            }
            let expected = ContinuationState {
                schema_version: 1,
                next_input_position: end,
                accumulated_result: sum,
                last_committed_chunk: sequence,
            };
            let progress = Progress {
                sequence,
                input_position: checkpoint.next_input_position,
                next_input_position: end,
                accumulated_result: sum,
                idempotency_key: format!("chunk-{sequence}"),
            };
            if digest != hash(&serde_json::to_vec(&progress)?) {
                return Err(Error::new(
                    "STORE_CORRUPT",
                    "Effect semantic digest mismatch",
                ));
            }
            if sequence != checkpoint.last_committed_chunk + 1
                || outcome.sequence != sequence
                || outcome.checkpoint != expected
            {
                return Err(Error::new(
                    "CHECKPOINT_CORRUPT",
                    "Effects do not form a valid continuation",
                ));
            }
            checkpoint = expected;
        }
        if checkpoint != authority.continuation
            || (authority.lifecycle == Lifecycle::Completed
                && checkpoint.next_input_position != values.len())
        {
            return Err(Error::new(
                "CHECKPOINT_CORRUPT",
                "Authority checkpoint differs from committed effects",
            ));
        }
        Ok(
            json!({"valid":true,"authority_id":id,"events":count,"effects":effects,"head_hash":previous,"checkpoint":checkpoint,"journal_mode":"wal","synchronous":"FULL","signed":false}),
        )
    }
}

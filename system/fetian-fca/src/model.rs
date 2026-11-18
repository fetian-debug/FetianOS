use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

pub const MAX_INPUT_BYTES: usize = 32768;
pub const MAX_INPUT_ITEMS: usize = 4096;
pub const LEASE_TTL: Duration = Duration::from_secs(30);
pub const CAPABILITIES: [&str; 4] = [
    "input.read",
    "checkpoint.commit",
    "result.commit",
    "authority.inspect",
];

pub fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
pub fn timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
        .try_into()
        .unwrap_or(u64::MAX)
}
pub fn new_id(prefix: &str) -> Result<String> {
    let mut bytes = [0_u8; 16];
    getrandom::fill(&mut bytes).map_err(|_| {
        Error::new(
            "RANDOM_UNAVAILABLE",
            "Cannot issue an unpredictable identity",
        )
    })?;
    Ok(format!(
        "{prefix}_{}",
        bytes
            .iter()
            .map(|value| format!("{value:02x}"))
            .collect::<String>()
    ))
}
pub fn valid_id(value: &str, prefix: &str) -> bool {
    value.strip_prefix(&format!("{prefix}_")).is_some_and(|id| {
        id.len() == 32
            && id
                .bytes()
                .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
    })
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct AuthorityId(String);
impl AuthorityId {
    pub fn generate() -> Result<Self> {
        Ok(Self(new_id("ca")?))
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
impl TryFrom<String> for AuthorityId {
    type Error = Error;
    fn try_from(value: String) -> Result<Self> {
        if !valid_id(&value, "ca") {
            return Err(Error::new(
                "INVALID_AUTHORITY_ID",
                "Expected ca_ followed by 32 lowercase hexadecimal digits",
            ));
        }
        Ok(Self(value))
    }
}
impl From<AuthorityId> for String {
    fn from(value: AuthorityId) -> Self {
        value.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutorId {
    #[serde(rename = "rust-reference-v1")]
    Rust,
    #[serde(rename = "python-reference-v1")]
    Python,
}
impl ExecutorId {
    pub fn name(self) -> &'static str {
        match self {
            Self::Rust => "rust-reference-v1",
            Self::Python => "python-reference-v1",
        }
    }
    pub fn parse(value: &str) -> Result<Self> {
        match value {
            "rust-reference-v1" | "rust" => Ok(Self::Rust),
            "python-reference-v1" | "python" => Ok(Self::Python),
            _ => Err(Error::new(
                "EXECUTOR_NOT_ALLOWED",
                "Unknown bundled executor",
            )),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Lifecycle {
    Created,
    Validated,
    Ready,
    Leased,
    Running,
    Checkpointing,
    Suspending,
    Suspended,
    Revoking,
    Recovering,
    Completed,
    Failed,
    Cancelled,
    Orphaned,
}
impl Lifecycle {
    pub fn terminal(self) -> bool {
        matches!(self, Self::Completed | Self::Failed | Self::Cancelled)
    }
    pub fn permits(self, next: Self) -> bool {
        use Lifecycle::*;
        matches!(
            (self, next),
            (Created, Validated | Failed | Cancelled)
                | (Validated, Ready | Failed | Cancelled)
                | (
                    Ready,
                    Leased | Suspended | Cancelled | Checkpointing | Recovering
                )
                | (Leased, Running | Revoking | Failed | Orphaned)
                | (
                    Running,
                    Checkpointing | Revoking | Suspending | Completed | Failed
                )
                | (Checkpointing, Running | Ready | Revoking | Failed)
                | (Suspending, Revoking | Suspended | Orphaned)
                | (
                    Revoking,
                    Ready | Suspended | Recovering | Cancelled | Failed | Orphaned
                )
                | (Recovering, Ready | Suspended | Orphaned | Failed)
                | (Suspended, Ready | Cancelled | Recovering)
                | (Orphaned, Recovering)
        )
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Workload {
    pub id: String,
    pub semantic_version: u32,
    pub protocol_version: u32,
    pub checkpoint_schema: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InputReference {
    pub kind: String,
    pub id: String,
    pub digest_algorithm: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResourceBudget {
    pub cpu_quota: u32,
    pub memory_bytes: u64,
    pub pids_max: u32,
    pub strict: bool,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RecoveryPolicy {
    pub automatic_resume: bool,
    pub failure_behavior: String,
    pub require_executor_compatibility: bool,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExecutionContract {
    pub schema_version: u32,
    pub workload: Workload,
    pub input: InputReference,
    pub outputs: Vec<String>,
    pub capabilities: Vec<String>,
    pub resource_budget: ResourceBudget,
    pub recovery: RecoveryPolicy,
    pub permitted_executors: Vec<ExecutorId>,
    pub chunk_size: usize,
    pub completion_condition: String,
}
impl ExecutionContract {
    pub fn reference(input: String) -> Self {
        Self {
            schema_version: 1,
            workload: Workload {
                id: "fetian.sum-i64".into(),
                semantic_version: 1,
                protocol_version: 1,
                checkpoint_schema: "sum-i64-state-v1".into(),
            },
            input: InputReference {
                kind: "managed_immutable_file".into(),
                id: input,
                digest_algorithm: "sha256".into(),
            },
            outputs: vec!["sum-i64".into()],
            capabilities: CAPABILITIES.iter().map(|v| (*v).into()).collect(),
            resource_budget: ResourceBudget {
                cpu_quota: 1,
                memory_bytes: 128 * 1024 * 1024,
                pids_max: 8,
                strict: false,
            },
            recovery: RecoveryPolicy {
                automatic_resume: false,
                failure_behavior: "recover".into(),
                require_executor_compatibility: true,
            },
            permitted_executors: vec![ExecutorId::Rust, ExecutorId::Python],
            chunk_size: 64,
            completion_condition: "all_input_committed".into(),
        }
    }
    pub fn validate(&self) -> Result<()> {
        let invalid = |message| Error::new("INVALID_CONTRACT", message);
        if self.schema_version != 1
            || self.workload.id != "fetian.sum-i64"
            || self.workload.semantic_version != 1
            || self.workload.protocol_version != 1
            || self.workload.checkpoint_schema != "sum-i64-state-v1"
        {
            return Err(invalid(
                "Unsupported contract/workload/protocol/checkpoint version",
            ));
        }
        let digest = self.input.id.strip_prefix("sha256:").unwrap_or("");
        if self.input.kind != "managed_immutable_file"
            || self.input.digest_algorithm != "sha256"
            || digest.len() != 64
            || !digest
                .bytes()
                .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
        {
            return Err(invalid(
                "Input must be an imported SHA-256 managed reference",
            ));
        }
        let caps: BTreeSet<_> = self.capabilities.iter().map(String::as_str).collect();
        if caps.len() != self.capabilities.len()
            || caps.iter().any(|cap| !CAPABILITIES.contains(cap))
            || CAPABILITIES[..3].iter().any(|cap| !caps.contains(cap))
        {
            return Err(invalid(
                "Unknown/duplicate capabilities or missing workload capability",
            ));
        }
        let budget = &self.resource_budget;
        if !(1..=64).contains(&budget.cpu_quota)
            || !(16 * 1024 * 1024..=8 * 1024 * 1024 * 1024).contains(&budget.memory_bytes)
            || !(1..=32).contains(&budget.pids_max)
        {
            return Err(invalid("Resource budget is outside prototype bounds"));
        }
        if !(16..=128).contains(&self.chunk_size)
            || self.outputs != ["sum-i64"]
            || self.completion_condition != "all_input_committed"
            || self.recovery.automatic_resume
            || !self.recovery.require_executor_compatibility
            || !matches!(self.recovery.failure_behavior.as_str(), "recover" | "fail")
        {
            return Err(invalid("Unsupported execution/completion/recovery policy"));
        }
        if self.permitted_executors.is_empty()
            || self.permitted_executors.len() > 2
            || (self.permitted_executors.len() == 2
                && self.permitted_executors[0] == self.permitted_executors[1])
        {
            return Err(invalid("Invalid executor allowlist"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContinuationState {
    pub schema_version: u32,
    pub next_input_position: usize,
    pub accumulated_result: i64,
    pub last_committed_chunk: u64,
}
impl ContinuationState {
    pub fn initial() -> Self {
        Self {
            schema_version: 1,
            ..Self::default()
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeaseRecord {
    pub executor_id: ExecutorId,
    pub lease_id: String,
    pub epoch: u64,
    pub issued_at: u64,
    pub pid: Option<u32>,
    pub process_start_ticks: Option<u64>,
}
pub struct RuntimeLease {
    pub record: LeaseRecord,
    deadline: Instant,
}
impl RuntimeLease {
    pub fn new(record: LeaseRecord) -> Self {
        Self {
            record,
            deadline: Instant::now() + LEASE_TTL,
        }
    }
    pub fn validate(&self, submitted_epoch: u64, lease_id: &str, now: Instant) -> Result<()> {
        if submitted_epoch != self.record.epoch {
            return Err(Error::new(
                "STALE_EPOCH",
                "Executor generation has been fenced",
            ));
        }
        if lease_id != self.record.lease_id {
            return Err(Error::new("LEASE_REVOKED", "Lease is not current"));
        }
        if now >= self.deadline {
            return Err(Error::new(
                "LEASE_EXPIRED",
                "Monotonic lease deadline passed",
            ));
        }
        Ok(())
    }
    pub fn renew(&mut self) {
        self.deadline = Instant::now() + LEASE_TTL;
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContinuationAuthority {
    pub(crate) id: AuthorityId,
    pub(crate) contract: ExecutionContract,
    pub(crate) lifecycle: Lifecycle,
    pub(crate) epoch: u64,
    pub(crate) continuation: ContinuationState,
    pub(crate) current_executor: Option<LeaseRecord>,
    pub(crate) previous_executors: Vec<LeaseRecord>,
}
impl ContinuationAuthority {
    pub fn id(&self) -> &AuthorityId {
        &self.id
    }
    pub fn lifecycle(&self) -> Lifecycle {
        self.lifecycle
    }
    pub fn epoch(&self) -> u64 {
        self.epoch
    }
    pub fn continuation(&self) -> &ContinuationState {
        &self.continuation
    }
    pub(crate) fn transition(&mut self, next: Lifecycle) -> Result<()> {
        if !self.lifecycle.permits(next) {
            return Err(Error::new(
                "INVALID_STATE",
                format!("Illegal transition {:?} -> {next:?}", self.lifecycle),
            ));
        }
        self.lifecycle = next;
        Ok(())
    }
    pub(crate) fn advance_epoch(&mut self) -> Result<()> {
        self.epoch = self
            .epoch
            .checked_add(1)
            .filter(|value| *value <= i64::MAX as u64)
            .ok_or_else(|| {
                Error::new("EPOCH_EXHAUSTED", "Cannot safely issue another generation")
            })?;
        Ok(())
    }
}

pub fn parse_input(bytes: &[u8]) -> Result<Vec<i64>> {
    if bytes.is_empty() || bytes.len() > MAX_INPUT_BYTES {
        return Err(Error::new(
            "INPUT_LIMIT",
            "Input must contain 1–32768 bytes",
        ));
    }
    let text = std::str::from_utf8(bytes)
        .map_err(|_| Error::new("INVALID_INPUT", "Input must be UTF-8 decimal integers"))?;
    if text.contains('\r') {
        return Err(Error::new(
            "INVALID_INPUT",
            "Use LF-separated canonical decimal lines",
        ));
    }
    let values: Vec<i64> = text
        .lines()
        .map(|line| {
            let value = line.parse::<i64>().map_err(|_| {
                Error::new(
                    "INVALID_INPUT",
                    "Expected canonical signed 64-bit decimal lines",
                )
            })?;
            if value.to_string() != line {
                return Err(Error::new("INVALID_INPUT", "Noncanonical integer encoding"));
            }
            Ok(value)
        })
        .collect::<Result<_>>()?;
    if values.is_empty() || values.len() > MAX_INPUT_ITEMS {
        return Err(Error::new("INPUT_LIMIT", "Input item limit exceeded"));
    }
    Ok(values)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn identities_are_distinct_and_validated() {
        let a = AuthorityId::generate().unwrap();
        let b = AuthorityId::generate().unwrap();
        assert_ne!(a, b);
        assert!(AuthorityId::try_from("../bad".to_owned()).is_err());
        assert_eq!(AuthorityId::try_from(a.as_str().to_owned()).unwrap(), a);
    }
    #[test]
    fn contracts_are_explicit_and_bounded() {
        let mut contract = ExecutionContract::reference(format!("sha256:{}", "a".repeat(64)));
        contract.validate().unwrap();
        contract.workload.semantic_version = 2;
        assert!(contract.validate().is_err());
        contract.workload.semantic_version = 1;
        contract.capabilities.push("host.write".into());
        assert!(contract.validate().is_err());
        contract.capabilities.pop();
        contract.resource_budget.memory_bytes = 0;
        assert!(contract.validate().is_err());
        assert!(
            serde_json::from_str::<ExecutionContract>(r#"{"shell":"touch /tmp/unsafe"}"#).is_err()
        );
    }
    #[test]
    fn terminal_states_never_resume() {
        let states = [
            Lifecycle::Created,
            Lifecycle::Validated,
            Lifecycle::Ready,
            Lifecycle::Leased,
            Lifecycle::Running,
            Lifecycle::Checkpointing,
            Lifecycle::Suspending,
            Lifecycle::Suspended,
            Lifecycle::Revoking,
            Lifecycle::Recovering,
            Lifecycle::Completed,
            Lifecycle::Failed,
            Lifecycle::Cancelled,
            Lifecycle::Orphaned,
        ];
        for terminal in [
            Lifecycle::Completed,
            Lifecycle::Failed,
            Lifecycle::Cancelled,
        ] {
            for next in states {
                assert!(!terminal.permits(next));
            }
        }
        assert!(Lifecycle::Running.permits(Lifecycle::Revoking));
        assert!(Lifecycle::Orphaned.permits(Lifecycle::Recovering));
        assert!(!Lifecycle::Orphaned.permits(Lifecycle::Running));
        assert!(!Lifecycle::Created.permits(Lifecycle::Running));
    }
    #[test]
    fn leases_use_monotonic_time_and_fencing() {
        let lease = RuntimeLease::new(LeaseRecord {
            executor_id: ExecutorId::Rust,
            lease_id: "private".into(),
            epoch: 2,
            issued_at: u64::MAX,
            pid: None,
            process_start_ticks: None,
        });
        assert_eq!(
            lease
                .validate(1, "private", Instant::now())
                .unwrap_err()
                .code,
            "STALE_EPOCH"
        );
        assert_eq!(
            lease.validate(2, "wrong", Instant::now()).unwrap_err().code,
            "LEASE_REVOKED"
        );
        assert_eq!(
            lease
                .validate(2, "private", Instant::now() + LEASE_TTL * 2)
                .unwrap_err()
                .code,
            "LEASE_EXPIRED"
        );
        lease.validate(2, "private", Instant::now()).unwrap();
    }
    #[test]
    fn input_representation_is_language_independent() {
        assert_eq!(
            parse_input(b"-9223372036854775808\n0\n9223372036854775807\n").unwrap(),
            [i64::MIN, 0, i64::MAX]
        );
        for bad in [
            b"01\n".as_slice(),
            b"+1\n",
            b" 1\n",
            b"\n",
            b"9223372036854775808\n",
        ] {
            assert!(parse_input(bad).is_err());
        }
    }
}

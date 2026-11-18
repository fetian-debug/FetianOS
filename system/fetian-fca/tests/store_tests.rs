use fetian_fca::{
    model::*,
    store::{Credential, Progress, Store},
};
use std::{fs, os::unix::fs::DirBuilderExt, path::PathBuf};
struct Fixture {
    dir: PathBuf,
    store: Option<Store>,
    id: String,
    credential: Credential,
}
impl Fixture {
    fn new() -> Self {
        let dir = std::env::temp_dir().join(new_id("fca-store-test").unwrap());
        fs::DirBuilder::new().mode(0o700).create(&dir).unwrap();
        let mut store = Store::open(&dir.join("authorities.sqlite3")).unwrap();
        let input = store
            .import(
                &(1..=128)
                    .map(|n| format!("{n}\n"))
                    .collect::<String>()
                    .into_bytes(),
            )
            .unwrap();
        let authority = store
            .create(
                AuthorityId::generate().unwrap(),
                ExecutionContract::reference(input),
            )
            .unwrap();
        let id = authority.id().as_str().to_owned();
        let lease = store.issue_lease(&id, ExecutorId::Rust).unwrap();
        store.started(&id, 123, 456).unwrap();
        Self {
            dir,
            store: Some(store),
            id,
            credential: Credential {
                executor_id: ExecutorId::Rust,
                lease_id: lease.lease_id,
                epoch: lease.epoch,
            },
        }
    }
    fn store(&mut self) -> &mut Store {
        self.store.as_mut().unwrap()
    }
    fn progress() -> Progress {
        Progress {
            sequence: 1,
            input_position: 0,
            next_input_position: 64,
            accumulated_result: 2080,
            idempotency_key: "chunk-1".into(),
        }
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        self.store.take();
        let _ = fs::remove_dir_all(&self.dir);
    }
}

#[test]
fn missing_capability_is_denied_at_store_boundary() {
    let mut f = Fixture::new();
    let existing_id = f.id.clone();
    let source = f.store().get(&existing_id).unwrap();
    let mut contract: ExecutionContract =
        serde_json::from_value(serde_json::to_value(source).unwrap()["contract"].clone()).unwrap();
    contract
        .capabilities
        .retain(|cap| cap != "authority.inspect");
    let authority = f
        .store()
        .create(AuthorityId::generate().unwrap(), contract)
        .unwrap();
    let id = authority.id().as_str().to_owned();
    let lease = f.store().issue_lease(&id, ExecutorId::Rust).unwrap();
    f.store().started(&id, 123, 456).unwrap();
    let credential = Credential {
        executor_id: ExecutorId::Rust,
        lease_id: lease.lease_id,
        epoch: lease.epoch,
    };
    assert_eq!(
        f.store()
            .inspect_executor(&id, &credential)
            .unwrap_err()
            .code,
        "CAPABILITY_DENIED"
    );
    assert!(f.store().read_chunk(&id, &credential, 0).is_ok());
}

#[test]
fn orphaned_authority_cannot_issue_replacement_lease() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    f.store().recover(&id, true).unwrap();
    assert_eq!(f.store().get(&id).unwrap().lifecycle(), Lifecycle::Orphaned);
    assert_eq!(
        f.store()
            .issue_lease(&id, ExecutorId::Python)
            .unwrap_err()
            .code,
        "INVALID_STATE"
    );
    f.store().recover(&id, false).unwrap();
    assert!(f.store().issue_lease(&id, ExecutorId::Python).is_ok());
}

#[test]
fn input_and_event_corruption_are_detected_after_restart() {
    for table in ["inputs", "events"] {
        let mut f = Fixture::new();
        f.store.take();
        let db = rusqlite::Connection::open(f.dir.join("authorities.sqlite3")).unwrap();
        if table == "inputs" {
            db.execute_batch("DROP TRIGGER inputs_no_update; UPDATE inputs SET content=X'310A';")
                .unwrap();
        } else {
            db.execute_batch(
                "DROP TRIGGER events_no_update; UPDATE events SET hash='broken' WHERE sequence=1;",
            )
            .unwrap();
        }
        drop(db);
        assert!(Store::open(&f.dir.join("authorities.sqlite3")).is_err());
    }
}

#[test]
fn symlink_store_and_runtime_directory_are_rejected() {
    let f = Fixture::new();
    let link = f.dir.join("linked.sqlite3");
    std::os::unix::fs::symlink(f.dir.join("authorities.sqlite3"), &link).unwrap();
    assert!(Store::open(&link).is_err());
    let directory = f.dir.join("linked-dir");
    std::os::unix::fs::symlink(&f.dir, &directory).unwrap();
    assert!(fetian_fca::paths::private_dir(&directory.join("child")).is_err());
    assert!(!f.dir.join("child").exists());
}
#[test]
fn identical_retries_ack_same_effect_conflicting_retries_fail() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    let credential = f.credential.clone();
    let progress = Fixture::progress();
    let first = f
        .store()
        .commit(&id, &credential, &progress, false)
        .unwrap();
    let again = f
        .store()
        .commit(&id, &credential, &progress, false)
        .unwrap();
    assert_eq!(first.effect_id, again.effect_id);
    let mut conflict = progress;
    conflict.accumulated_result += 1;
    assert_eq!(
        f.store()
            .commit(&id, &credential, &conflict, false)
            .unwrap_err()
            .code,
        "IDEMPOTENCY_CONFLICT"
    );
    assert_eq!(f.store().verify(&id).unwrap()["effects"], 1);
}
#[test]
fn transaction_failure_has_no_partial_effect_checkpoint_or_event() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    let credential = f.credential.clone();
    let before = f.store().verify(&id).unwrap();
    assert_eq!(
        f.store()
            .commit(&id, &credential, &Fixture::progress(), true)
            .unwrap_err()
            .code,
        "INJECTED_FAILURE"
    );
    assert_eq!(before, f.store().verify(&id).unwrap());
    f.store()
        .commit(&id, &credential, &Fixture::progress(), false)
        .unwrap();
    assert_eq!(f.store().verify(&id).unwrap()["effects"], 1);
}
#[test]
fn fencing_precedes_duplicate_ack_and_survives_reopen() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    let old = f.credential.clone();
    f.store()
        .commit(&id, &old, &Fixture::progress(), false)
        .unwrap();
    f.store().begin_revoke(&id, "test-handoff").unwrap();
    assert_eq!(
        f.store()
            .commit(&id, &old, &Fixture::progress(), false)
            .unwrap_err()
            .code,
        "STALE_EPOCH"
    );
    f.store.take();
    f.store = Some(Store::open(&f.dir.join("authorities.sqlite3")).unwrap());
    f.store().recover(&id, false).unwrap();
    let lease = f.store().issue_lease(&id, ExecutorId::Python).unwrap();
    assert!(lease.epoch > old.epoch);
    f.store().started(&id, 124, 457).unwrap();
    let current = Credential {
        executor_id: ExecutorId::Python,
        lease_id: lease.lease_id,
        epoch: lease.epoch,
    };
    let retry = f
        .store()
        .commit(&id, &current, &Fixture::progress(), false)
        .unwrap();
    assert_eq!(retry.sequence, 1);
    let progress = Progress {
        sequence: 2,
        input_position: 64,
        next_input_position: 128,
        accumulated_result: 8256,
        idempotency_key: "chunk-2".into(),
    };
    f.store().commit(&id, &current, &progress, false).unwrap();
    assert_eq!(f.store().complete(&id, &current).unwrap(), 8256);
    assert_eq!(
        f.store()
            .commit(&id, &old, &Fixture::progress(), false)
            .unwrap_err()
            .code,
        "STALE_EPOCH"
    );
    assert_eq!(f.store().verify(&id).unwrap()["effects"], 2);
}
#[test]
fn invalid_cursor_result_and_lease_never_commit() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    let mut credential = f.credential.clone();
    credential.lease_id = "wrong".into();
    assert_eq!(
        f.store().read_chunk(&id, &credential, 0).unwrap_err().code,
        "LEASE_REVOKED"
    );
    credential = f.credential.clone();
    let mut progress = Fixture::progress();
    progress.input_position = 1;
    assert_eq!(
        f.store()
            .commit(&id, &credential, &progress, false)
            .unwrap_err()
            .code,
        "INVALID_SEQUENCE"
    );
    progress = Fixture::progress();
    progress.accumulated_result = 0;
    assert_eq!(
        f.store()
            .commit(&id, &credential, &progress, false)
            .unwrap_err()
            .code,
        "INVALID_RESULT"
    );
    assert_eq!(f.store().verify(&id).unwrap()["effects"], 0);
}
#[test]
fn snapshot_corruption_is_rejected_on_open() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    f.store.take();
    let db = rusqlite::Connection::open(f.dir.join("authorities.sqlite3")).unwrap();
    let text: String = db
        .query_row(
            "SELECT document FROM authorities WHERE id=?1",
            [&id],
            |row| row.get(0),
        )
        .unwrap();
    let mut value: serde_json::Value = serde_json::from_str(&text).unwrap();
    value["lifecycle"] = serde_json::json!("Completed");
    db.execute(
        "UPDATE authorities SET document=?1 WHERE id=?2",
        rusqlite::params![value.to_string(), id],
    )
    .unwrap();
    drop(db);
    assert!(Store::open(&f.dir.join("authorities.sqlite3")).is_err());
}
#[test]
fn append_only_guards_and_schema_versions_are_checked() {
    let mut f = Fixture::new();
    let id = f.id.clone();
    f.store.take();
    let db = rusqlite::Connection::open(f.dir.join("authorities.sqlite3")).unwrap();
    assert!(db
        .execute("DELETE FROM events WHERE authority_id=?1", [id])
        .is_err());
    db.pragma_update(None, "user_version", 999).unwrap();
    drop(db);
    assert!(Store::open(&f.dir.join("authorities.sqlite3")).is_err());
}

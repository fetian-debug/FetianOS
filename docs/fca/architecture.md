# FCA architecture

The invariant is that the authority, rather than the PID, owns the contract,
resource budget, continuation and managed effects. Executor replacement changes
the lease and epoch while preserving the authority ID and committed state.

```text
operator CLI -- UID-authenticated Unix socket --> single Rust coordinator
                                                   | SQLite WAL/FULL
                                                   | delegated cgroup adapter
                                                   | private inherited socketpair
                                            gated trusted launcher
                                                   |
                                         Rust OR Python executor
```

One coordinator thread owns `Store`, all lifecycle decisions, and owned `Child`
handles. Bounded worker reader threads deliver requests through a 128-message
channel. Workers have no direct database API. Operator connections are serial,
bounded to 64 KiB and two-second read timeouts; workers are capped at eight.
The daemon has both runtime and state-directory single-writer locks. SQLite
transactions serialize durable admission, effects and checkpoints.

## Source map and APIs

All source paths below are relative to `system/fetian-fca`.

| File | Responsibility |
| --- | --- |
| `src/model.rs` | Validated `AuthorityId`, `ExecutorId`, `ExecutionContract`, `ContinuationState`, `Lifecycle`, monotonic `RuntimeLease` |
| `src/store.rs` | `Store::create/get/list`, lease issue/start, bounded input reads, atomic `commit`, revoke/recover, verification/events |
| `src/broker.rs` | Operator/executor admission, owned-child lifetime, restart reconciliation, epoch-first handoff |
| `src/wire.rs` | Versioned length-delimited envelopes and bounds |
| `src/resources.rs` | Delegated Linux cgroup adapter and truthful unavailable status |
| `src/paths.rs` | Private XDG state/runtime directory validation |
| `src/client.rs`, `src/cli.rs` | Operator client, CLI commands, export and isolated deterministic demo |
| `src/worker.rs`, `executors/fetian-executor-python.py` | Independent Rust/Python implementations of the same sum ABI |
| `src/bin/*` | Daemon, CLI, Rust worker and trusted gated launcher entry points |
| `tests/store_tests.rs`, `tests/process_tests.py` | Persistent-store invariants and actual Linux process/crash tests |
| `packaging/*` | Manual user unit and installed CLI wrapper |

The resource adapter isolates Linux-specific enforcement. Executor selection
accepts only two bundled identities and creates concrete commands internally.
Capability admission is performed at the store transaction boundary; there is
no policy string that expands into a host shell command.

## Database schema version 1

`inputs(id, content)` stores bounded immutable bytes addressed by SHA-256.
`authorities(id, document)` stores the validated contract and current snapshot.
`events(authority_id, sequence, kind, payload, previous_hash, hash)` is a logical
append-only audit chain. `effects(authority_id, sequence, effect_id, epoch,
operation_key, request_digest, outcome, committed_at)` is the unique effect ledger.
Foreign keys and unique authority/sequence and authority/idempotency-key pairs
constrain writes. UPDATE/DELETE triggers guard immutable tables. Snapshot, effect
and event writes share one immediate transaction per state change.

WAL and synchronous FULL are verified at open, SQLite integrity is checked,
and every existing authority is verified before accepting requests. Unknown
schema versions fail closed; there is no automatic lossy migration.

## Dependencies

The isolated Cargo lock pins serde/serde_json for typed messages, sha2 for input
and journal digests, getrandom for identities, nix for safe Linux wrappers and
rusqlite with bundled SQLite for transactions. Rust source forbids unsafe code;
these dependencies and the C SQLite implementation remain part of the trusted
computing base. Python uses only its standard library. The root telemetry
workspace retains its independent dependency-free build.

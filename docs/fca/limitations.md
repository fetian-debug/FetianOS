# Known limitations and absent features

Version 1 supports one local sum workload, trusted bundled Rust/Python programs,
bounded immutable input, and effects entirely within one SQLite transaction.
This is the smallest complete process-independent authority experiment, not a
general-purpose OS execution replacement.

- No arbitrary program migration, heap/stack checkpoint, POSIX emulation,
  kernel scheduler, new kernel primitive, device isolation or host installation.
- No hostile same-UID worker sandbox, Landlock/seccomp policy, namespaces,
  separate worker UID, filesystem encryption, signed audit or rollback resistance.
- No network effect provider, credentials, remote authority service, distributed
  consensus, cross-machine handoff, GPU control or cumulative CPU budget.
- No automatic worker launch after recovery; contracts requesting it are rejected.
- No production retention/compaction or schema migration; explicit bounds apply.
- Serial operator requests can delay progress for their bounded read timeout.
  Local trusted deployment is assumed; multi-tenant admission is future work.
- Normal broker stop is an explicit CLI command. Supervisor termination relies
  on parent-death/group cleanup and startup reconciliation rather than a custom
  asynchronous signal handler inside SQLite code.
- cgroup code requires real writable user delegation. Local WSL validation
  observed unavailable controls; actual CPU/memory/pids exhaustion testing and
  resource-overhead measurements remain unverified on a delegated host.
- No desktop application is an executor. No FCA service is enabled by default.
  Existing metrics, apps, boot/login and recovery retain their prior behavior.

The journal protects against accidental inconsistency, not an owner who rewrites
all state. Durable guarantees depend on SQLite/filesystem/fsync behavior. The
external crash tests validate process failure, not power-cut or faulty-storage
behavior. No FCA-enabled ISO, hardware boot or installation has been tested.

## Phase 2 evidence

See [research validation](research-validation.md) for actual 1,000-case Linux CI
results, failures and exact-seed replays, and [security review](security-review.md)
for observed same-UID access and duplicate external writes. The new resource
pressure harness is implemented but actual kernel exhaustion remains unverified
where delegation is unavailable. WSL showed intermittent timeout failures during
one full run; their configurations passed isolated replay, and Linux CI passed
all 1,000. Their underlying timing cause is not established. No production
readiness or general exactly-once external effects are implied by a green CI.

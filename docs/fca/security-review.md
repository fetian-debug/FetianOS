# FCA Phase 2 security review

Scope: trusted local reference executors and the broker-managed protocol, not a
hostile-code sandbox. Private IPC, UID authentication, leases and managed
capability checks are useful boundaries, but a process with the broker's Unix
identity can bypass that protocol. The security experiment actually reads its
private SQLite store from a separate same-UID process. This is a demonstrated
high-severity limitation for any proposed untrusted-executor deployment.

| Threat | Current defense/evidence | Remaining limitation |
|---|---|---|
| Retired/foreign credentials | Epoch, lease and executor validation; actual private-socket probes | Same-UID code can access owner-writable state outside IPC |
| Forged sum/cursor or unsupported operation | Bounded strict frames, field/capability checks, broker recomputation | No arbitrary workload verifier exists |
| Conflicting retries | Unique keys/digests and atomic managed transaction | External services/files are outside that transaction |
| Process survives revoke | Epoch first, owned process-group kill/wait, PDEATHSIG; restart verifies PID/start ticks | Descendant escape and hostile same-UID behavior are not sandboxed |
| Store corruption | SQLite integrity, immutable input digest, hash chain and recomputation | Hashes are unsigned; owner rollback/rewrite is not prevented |
| Resource abuse | Eight active workers, 64 authorities, bounded input/frame/request/event counts | Broker CPU/memory and socket admission remain shared |
| CPU/memory/pids | Only delegated kernel cgroup controls; strict admission rejects if unavailable | No cumulative CPU, GPU or device isolation; see measured report |
| Test hooks exposed by default | Normal-mode fault-arm/release denials actually tested | A trusted operator can explicitly opt in to destructive test hooks |

`security.py` also exercises a bounded external-effect counterexample: a producer
appends and fsyncs a temporary file, is killed, and is retried. Two external
writes exist while the FCA managed-effect ledger has zero entries. This is an
explicit standalone example outside any FCA provider adapter, not a claim that
FCA currently brokers external filesystem operations. It disproves extending the
managed transaction's deduplication guarantee to arbitrary external effects.

`security.py --delegated` can launch a transient **user** unit with controller
delegation. After strict admission it attaches an owned, gated helper to that
authority's cgroup, applies bounded pressure and records actual `nr_throttled`,
`oom_kill` and `pids.events:max` counter changes. Merely writing a limit is not
reported as enforcement. No delegation means `unavailable`, not a pass for kernel
enforcement. No root units, package changes or permanent services are installed.
Controller semantics follow the [kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html).

Before hostile executors: separate worker identities or a reviewed namespace/
seccomp/filesystem policy, inaccessible broker storage, authenticated provider
adapters with fencing/idempotency, signed/rollback-resistant state if required,
and independent admission/retention controls are necessary. None is represented
as implemented by these Phase 2 tests.

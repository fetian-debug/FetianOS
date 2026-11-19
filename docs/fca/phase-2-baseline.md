# FCA Phase 2 baseline

Inspected at source commit `2355a987221b3b7eec52e646d97936dd0c4f23d4` before
Phase 2 implementation. This records code behavior, not inferred capabilities.

The four binaries are the Rust coordinator/daemon, operator CLI, trusted gated
launcher, and Rust sum executor. The Python reference executor implements the
same `fetian.sum-i64/v1` contract and `sum-i64-state-v1` checkpoint. The core is
an independent Rust package; default metrics have a separate Cargo workspace.
The inspected source includes every FCA module and entry point, both workers,
the four-table SQLite schema, store/process tests, benchmark, packaging, protocol,
architecture, validation report, source checks and ISO/Pages/FCA workflows.

SQLite WAL/FULL immediate transactions join the managed result fragment,
checkpoint, lifecycle transitions and journal events. Unique authority/sequence
and authority/idempotency keys prevent duplicate managed effects. Epoch checking
precedes duplicate lookup. Identical authorized retries return the old outcome;
conflicting retries fail. Computation may repeat. No external effect participates
in this transaction. Operator import/export are filesystem operations, not
transactional external-provider effects.

Revocation advances the durable epoch before signalling an owned child process
group. Restart verifies SQLite, input digest, lifecycle/event hash chain, lease
identity and recomputed effect/checkpoint state. A possibly live stored process
identity produces Orphaned; stored PIDs alone are never signalled. Runtime lease
expiry uses monotonic time. Runtime/state single-writer locks prevent competing
brokers. Operators use UID-authenticated sockets; workers use inherited private
socketpairs and per-lease credentials. Both are bounded length-prefixed JSON.

Existing evidence is 16 Rust tests, 19 process tests, one Rust→Python demo and
small descriptive benchmarks. Broker transaction faults exit before commit or
after commit before ACK; test barriers and explicit SIGKILL are available only
with `--allow-test-faults`. There is no seeded thousand-run harness, replay
manifest, distribution benchmark or symmetric standalone research report yet.

Limits: 32 KiB/4,096 input integers, 64 authorities, eight active workers,
100,000 journal events/authority, 4,096 requests/lease, 30-second leases. Only
two trusted bundled workers are allowed. Same-UID hostile code is not sandboxed;
owner-writable state and unsigned hashes are not tamperproof. Resource limits
apply only if a user-owned cpu/memory/pids cgroup delegation is available;
strict mode rejects before a worker starts otherwise. Earlier WSL evidence had
no delegation. Full kernel enforcement and power-cut behavior remain unproven.

The published `preview-7-1` ISO booted separately, excludes FCA, and is immutable
evidence for that configuration only. Phase 2 will use an isolated branch and
dedicated validation workflow, preserve the ISO workflow and published release,
and leave FCA opt-in. No desktop, installer, boot, metrics or init redesign.

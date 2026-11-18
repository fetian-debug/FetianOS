# FCA implementation stages

Baseline: existing dependency-free Rust telemetry, Python/GTK applications,
Sway recovery, opt-in Hyprland and Thunar defaults remain unchanged. The local
baseline is 114 Python tests plus 6 Rust tests, with GTK/staged checks passing.
Hosted source checks and Pages deployment passed. The first actual ISO was
constructed but rejected for missing boot artifacts. Later images passed static
validation and the third boot reached an interactive firstboot prompt. A live-only
firstboot fix is under hosted verification. No graphical login or installation
success is inferred from those runs.

FCA lives in `system/fetian-fca`, an independent experimental Rust package. Its
small serialization/hash/SQLite/Unix-adapter dependencies are locked separately;
the default telemetry workspace remains dependency-free and offline-buildable.
There is no new GUI, privileged helper or boot-critical dependency.

Working increments:

1. Encapsulated identities, execution contract, continuation ABI and lifecycle.
2. SQLite WAL/FULL store, atomic effects/checkpoints, idempotency and hash chain.
3. Unprivileged broker, authenticated bounded CLI IPC and executor-private channels.
4. Separate Rust/Python workers and deterministic crash/handoff proof.
5. Epoch-first revocation, owned-child termination, restart reconciliation.
6. Delegated cgroup adapter and explicit advisory/unavailable reporting.
7. Opt-in packaging/service, full integration tests, measurements and prior art.

The reference executors are bundled cooperative programs. Managed capabilities
are broker-enforced; the prototype must not claim that Unix same-user processes
are an arbitrary hostile-code sandbox. Unsupported strict resource contracts
must fail before a worker runs. Every claimed handoff/recovery result needs real
process and durable-store evidence, not placeholders or success messages.

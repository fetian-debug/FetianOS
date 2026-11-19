# FCA stability scope

The stabilization base includes the existing Phase 2 forbidden-handoff fix and
its evidence. This branch changes no FCA implementation, contract, packaging,
dependencies, authority checks or protocol. FCA remains excluded from default
image staging unless explicitly requested and has no normal boot Install target.

The local baseline executes 16 Rust tests, 19 real-process tests, six harness
oracle tests, 23 deterministic fault scenarios and 15 protocol/security probes.
They cover broker/worker death, checkpoint transactions, reopen/corruption
rejection, interrupted commits, stale epochs, duplicate/conflicting requests,
cross-language and forbidden handoff, and incomplete transitions. Corruption is
safely rejected in designated cases; it is not described as automatic repair.

The final reproduction also requests all 1,000 seed-2090 randomized cases. Use
the machine-readable result and raw evidence, not the requested count, as the
authority for actual completion. The final report records the observed totals.
The additional security boundary suite checks admission limits and the existing
same-UID-store and external-effect counterexamples. It does not convert those
known limitations into security successes.

Delegated cgroup enforcement is unavailable in this WSL setup. Strict admission
must reject unavailable enforcement; successful rejection is not CPU/memory/pid
pressure enforcement. SQLite full-device behavior, hostile-worker sandboxing,
arbitrary external exactly-once effects and physical power-loss consistency
remain outside demonstrated guarantees. See [existing limitations](../fca/limitations.md).

Tests create private temporary stores and owned processes. They do not corrupt
the host filesystem, user data or any production FCA authority. The optional
broker's absence/failure is not turned into a normal OS startup dependency.

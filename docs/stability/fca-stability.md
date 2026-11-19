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

All 1,000 seed-2090 cases completed locally: the original run met 995 expectations
and timed out in five; the byte-identical Linux-executable control met 997 and
timed out in three different cases. A daemon thread was observed in journal
commit wait. Executable relocation did not remove the timing problem. The local
deterministic run also has one timeout; its control passed all 23. Initial
classifications remain unchanged rather than relabeled as successful recovery.

[Hosted run 44505308690](https://github.com/fetian-debug/FetianOS/actions/runs/44505308690)
at source 4b41eff completed all five jobs successfully and all 1,000 cases met
expectations: 408 recoveries, 514 rejections and 78 safely detected unrecoverable
cases. Source-identified plans, all raw records and security/performance evidence
are retained under evidence/hosted-fca. Different timing outcomes suggest an
environment-sensitive limitation; they do not establish why every timeout occurred
or prove an absence of latent defects. No deadline or durability setting changed.
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

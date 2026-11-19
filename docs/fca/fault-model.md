# FCA Phase 2 fault model

These experiments exercise the bounded `fetian.sum-i64/v1` workload on real Linux
processes, inherited private sockets and temporary SQLite WAL stores. They are
not power-cut tests, model checking, or evidence for arbitrary applications.
`validation/lab.py` stores its complete plan before executing any experiment.

| Boundary | Actual injected action | Required observation |
|---|---|---|
| Executor before next commit | SIGKILL while paused, or coordinator kills its owned producer before store commit | Previous checkpoint only; epoch fenced; replacement finishes |
| Executor after commit, before ACK | Kill owned producer after the transaction returns | Next checkpoint survives; exactly one managed effect |
| Broker before SQL commit | Exit 86 from inside the transaction | Uncommitted changes roll back |
| Broker after effect INSERT | Exit 88 before checkpoint/event commit | No isolated effect survives the atomic transaction |
| Broker after commit, before ACK | Exit 87 after commit returns | Next checkpoint and its effect survive together |
| Broker active/pending, WAL reopen | SIGKILL, then open the same private store | Identity/contract preserved; pending state verified; no automatic resume |
| Stale/competing producer | Actual competing acquisition or retired credential commit | One active grant; stale generation rejected |
| Duplicate/conflicting effect | Repeat the same progress or change its digest | Same authorized outcome, or conflict rejection; no second managed effect |
| Corrupt/incomplete checkpoint or journal | Modify only the stopped private fixture | Startup refuses; reported as unrecoverable, never successful recovery |
| Rust/Python handoff, both directions | Fence/kill/wait, then launch the other implementation | Same authority and semantic checkpoint, independent final sum |
| Forbidden handoff | Request an executor absent from the contract | Reject before changing epoch, current PID, lease or continuation |
| Expiry | Actually wait for the 30-second monotonic lease | Fenced/recoverable authority; old credential cannot commit |

Private protocol experiments are sent by actual Rust/Python worker processes,
not by the operator test API. They cover forged credentials, executor identity,
foreign authority credentials, old epochs, version, request ordering, unknown
fields/operations, forged results, cursor/capability violations and oversized,
truncated or invalid JSON frames. The coordinator records the observed response
code separately from a subsequent socket EOF. Foreign checkpoints must remain
unchanged. Transport parse failures are checked against transport audit events.

Every successful recovery checks identity, immutable contract, epoch advancement,
checkpoint schema/cursor/independent sum, unique effects, completion and the
broker's full journal/lifecycle verifier. Computation can repeat; the managed
transaction must not create duplicate effects. Each experiment uses a fresh
private store and bounded inputs (16–64 items/chunk, 2–8 chunks), changes fault
boundary, worker language and 0–2 ms scheduling jitter using a recorded seed.

Outcomes are distinct: `expected_recovery`, `expected_rejection`,
`safely_detected_unrecoverable`, `unexpected_correctness_failure`. A malformed
message refusal or corrupt-store refusal is not counted as recovered work.
Unexpected errors and cleanup failures make the command fail. No automatic retry
converts a failed experiment into a pass. A replay repeats the configuration and
logical barrier, not OS scheduling, random authority IDs or exact timings.

All hooks require explicit `--allow-test-faults`. Normal-mode denial is tested.
The harness adopts/reaps only its own orphan descendants using Linux subreaper
support. It never signals an arbitrary stored PID or the user's real FCA state.

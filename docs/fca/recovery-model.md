# Recovery and transactional effects

The sole current workload commits its result fragment and semantic checkpoint
in one SQLite WAL/FULL immediate transaction. The transaction also inserts the
effect event, checkpoint event and lifecycle history. The ACK is sent only
after successful commit. Effects are unique per authority/chunk and semantic
idempotency key; requests are independently recomputed from immutable input.

| Failure window | Durable outcome |
| --- | --- |
| Before transaction commit | No effect, checkpoint or partial audit event survives |
| After commit, before ACK | Effect/checkpoint survive; retry returns original outcome |
| Worker dies after ACK | Continue from committed cursor; no previous chunk is added twice |
| Broker dies while worker runs | Parent-death kills the trusted worker; restart verifies state and advances epoch |
| Prior context may remain live | Orphaned; replacement is blocked until cessation is established |
| Corrupt input/history/snapshot | Broker startup fails; no silent recreation or guessed checkpoint |

This provides at-least-once computation with effectively-once committed managed
effects. It is not a universal exactly-once execution guarantee. Version 1 has
no adapter for effects outside this SQLite transaction. Any future external
provider needs its own idempotency/fencing protocol and explicit ambiguous
outcome handling; an audit entry cannot undo a sent request.

Restart checks SQLite integrity and the complete logical ledger before accepting
commands. It then records RecoveryStarted, fences the old generation and
reconciles lifecycle/process identity. Suspended authorities stay Suspended;
recoverable available authorities become Ready. Completed/Failed/Cancelled
remain terminal. No authority automatically executes after daemon restart.
There is no process-image checkpoint, arbitrary stack recovery or restoration
of host file descriptors and network sessions.

The process suite forces a real broker exit before the transaction commits and
after commit before its ACK. It also sends SIGKILL to the broker while a Rust
worker waits at a committed barrier, verifies parent-death behavior, restarts
the daemon and completes with Python. These tests use disposable state and
real SQLite, not a mocked persistence adapter.

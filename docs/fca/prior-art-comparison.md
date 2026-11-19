# FCA and prior art: scoped comparison

This is a documentation comparison, not a benchmark of other products. FCA's
rows describe inspected code and the bounded reference workload; other rows
summarize primary documentation. Application-specific means a workload or
adapter must supply the semantics, not that the platform cannot support them.

| Capability | FCA prototype | Temporal | CRIU | systemd/service supervisor | Celery job queue exemplar |
|---|---|---|---|---|---|
| Identity outlives worker PID | Durable authority | Durable workflow/activity identities | Process image/tree identity | Stable unit identity and new executions | Task identity and retries |
| Continuation after failure | Committed semantic sum checkpoint | History replay; activity retry | Restore memory/registers/resources | Restart process; application checkpoint needed | Retry/redelivery; application checkpoint needed |
| Stale work fencing | Epoch+lease at managed boundary | Activity task token becomes invalid after retry; external fencing is adapter-specific | Application-specific after restore | Process lifecycle/cgroup control; result epoch is application-specific | Application-specific result/effect fencing |
| Deduplicate effects | One local SQLite managed transaction | Activities must handle external idempotency | External effect policy application-specific | Application-specific | Idempotent task design and ACK/retry configuration |
| Change implementation language | Rust/Python sum ABI only, both directions tested | SDK/service contracts; changing workflow code requires deterministic compatibility | Restores saved execution state, not a different implementation | Can launch another executable; semantic checkpoint is application-specific | Named task protocol; equivalent cross-runtime state is application-specific |
| Resource control | Delegated cpu/memory/pids only; otherwise strict refusal | Deployment/worker infrastructure | Host/container configuration | Native resource-control settings/delegation | Worker/deployment limits |
| Lifecycle audit | Local unsigned hash chain + checked snapshots | Durable event history | Checkpoint images/tools | Unit state, journal and execution results | Events/result backend depending on configuration |

Temporal already makes execution durable through history/replay. It is not fair
to describe FCA's durable logical identity as a new capability missing there.
FCA's experiment concentrates a small semantic checkpoint, explicit epoch and
managed result fragment in one local transaction. There is no evidence here of
better reliability, throughput, deployment scale or generality than Temporal.
[Workflow execution and replay](https://docs.temporal.io/workflow-execution),
[activity execution and task tokens](https://docs.temporal.io/activity-execution)
explain the relevant distinction. Token validity protects activity completion;
this must not be confused with undoing arbitrary external side effects.

CRIU collects a process tree, memory maps, registers and resources, then restores
that saved execution. FCA instead starts a fresh compatible implementation from
application-defined state. That is a different contract with much narrower
coverage, not a replacement for transparent process checkpointing.
[CRIU design](https://criu.org/Checkpoint/Restore).

systemd already owns service lifecycle/restart behavior and cgroup resource
control. FCA's broker remains an ordinary user service; it does not replace init
or the scheduler. Durable domain-specific progress and atomic effect semantics
still require an application protocol with either approach. The supervisor
column uses systemd as a concrete exemplar rather than claiming every
supervisor behaves alike. [Service lifecycle](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html),
[resource control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html).

Celery documents ACK timing, idempotent task design, retries and optional
redelivery after worker loss. Those settings materially affect recovery. Calling
all queues at-most-once or claiming they never retain identity would be wrong.
The comparison is to these documented task semantics, not every queue or result
backend. [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html).

No universal exactly-once external computation/effect guarantee is claimed for
FCA. Repeated computation, deduplicated managed commits and external effects
are three separate questions. No proof of architectural novelty is established.

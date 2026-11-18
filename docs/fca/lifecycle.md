# Lifecycle state machine

All transitions are explicit, checked and recorded in the same transaction as
the snapshot change. No terminal state resumes. The complete allowed edge list
is in `Lifecycle::permits` in `src/model.rs`.

| State | Meaning and usual next state |
| --- | --- |
| Created | Identity and contract recorded; Validated or terminal failure/cancel |
| Validated | Contract accepted; Ready |
| Ready | No active executor; Leased, Suspended, Recovering or Cancelled |
| Leased | New generation admitted; Running or Revoking |
| Running | Current lease may request managed operations; Checkpointing, Revoking, Completed or Failed |
| Checkpointing | Transactional effect/checkpoint update; Running, Ready or Revoking |
| Suspending | Reserved checked intermediate state; Revoking or Suspended |
| Suspended | Explicitly paused, no active executor; Ready on resume |
| Revoking | Old lease removed and epoch advanced durably; stopped executor required before Ready/replacement |
| Recovering | Restart reconciliation in progress; Ready, Suspended, Orphaned or Failed |
| Orphaned | Prior process identity may still be live; no new lease until cessation is established |
| Completed | Entire immutable input committed; terminal |
| Failed | Explicit failure policy or launch failure; terminal |
| Cancelled | Operator cancellation; terminal |

Created/Validated are events within the atomic create transaction. Checkpointing
is inside the atomic effect transaction: a crash cannot expose a half-written
checkpoint. Suspend currently takes the direct checked Running → Revoking →
Suspended route. The reserved Suspending state does not imply extra behavior.

Lease issuance changes Ready to Leased. The trusted launcher must establish its
lifetime before the broker commits process identity and Running, attaches the
resource group and opens the execution gate. The worker must then complete its
ABI hello before sending work requests. Running denotes an admitted context;
it does not certify arbitrary application startup success.

Cancellation and suspension durably revoke before stopping the owned child.
Stopping the broker normally suspends its running authorities. A daemon restart
preserves previously Suspended authorities. Ready authorities recover to Ready
with a newer epoch and await explicit execution.

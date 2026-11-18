# Continuation authority specification, version 1

`ca_` plus 32 lowercase random hexadecimal digits identifies the logical work.
The 128-bit random component is generated from the operating system random
source. IDs are validated before lookups and are not filesystem paths.
Duplicate IDs fail; PID reuse cannot create or rename an authority.

An authority contains its immutable validated execution contract, lifecycle,
monotonically increasing epoch, semantic continuation, optional current lease,
and bounded history of previous executor leases. Fields are changed only by
checked store operations. A lease records executor identity, an independent
random lease ID, epoch, audit issue time, PID and `/proc` start ticks.
Runtime expiry uses a 30-second `Instant` deadline and is not reconstructed
from wall time. Accepted executor requests renew the deadline.

The continuation schema contains `schema_version: 1`, `next_input_position`,
`accumulated_result` and `last_committed_chunk`. Initial values are zero.
This structure is sufficient to continue the sole supported sum workload in
another language. It does not serialize a language VM or OS process image.

Each committed chunk creates exactly one ledger row and advances the cursor
by exactly the contract chunk size, except the final shorter chunk. The broker
independently checks each signed 64-bit addition. The final state is Completed
only when the cursor equals input length; completion revokes the old epoch.

The prototype caps input at 32 KiB and 4,096 integers, authorities at 64,
active executors at eight, event history at 100,000 records per authority and
retained executor history at 64 records. Historical audit events remain intact
after older entries leave the snapshot's bounded executor history.

`verify` checks input digest, event chain and sequence, contract digest,
monotonic epochs, legal lifecycle history, current lease consistency, effects
against corresponding audit records and recomputed semantic progress, and
final checkpoint. It reports its head hash and unsigned status.

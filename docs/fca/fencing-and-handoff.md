# Fencing and handoff

Epochs are durable authority generations, checked at the managed write boundary.
Leases additionally bind a random lease ID and one allowlisted executor identity.
Wall-clock timestamps provide audit context only; expiry uses monotonic time.

The handoff order is enforced in code:

1. Commit HandoffStarted, lifecycle Revoking, removal of the current lease,
   LeaseRevoked, and an incremented epoch using SQLite FULL durability.
2. Signal only the process group belonging to the broker's owned Child handle.
   SIGKILL is used so the deterministic demo proves actual process loss.
3. Wait for the owned child and check `/proc` for surviving non-zombie group
   members. Close its private channel. If cessation is unproven, mark Orphaned.
4. Commit Ready and ExecutorExited. Check compatibility and resource budget for
   the replacement, then grant a new lease at the advanced epoch.
5. Attach the gated replacement to the authority's resource group and supply
   the same committed semantic checkpoint under its new credential.

This ordering also handles requests already in the reader queue: queue messages
carry the old epoch and cannot be dispatched to the replacement's channel.
Store admission independently rejects an old epoch before checking terminal
state or an existing idempotency key. An identical retry from the currently
authorized generation returns the original effect ID. Different semantic
content under that key returns `IDEMPOTENCY_CONFLICT`. A revoked generation
always gets `STALE_EPOCH`, including after completion.

A broker restart never sends signals using a PID loaded from storage. It
compares PID plus kernel start ticks and process state to identify whether a
previous execution context might still exist. A live matching identity makes
the authority Orphaned. Only explicit resume after that context is absent may
make it Ready. The trusted launcher installs parent-death SIGKILL and checks
that its parent did not disappear during bootstrap.

The local SQLite transaction is the fencing authority. This prototype has no
distributed consensus, remote lease service or fencing for external databases.

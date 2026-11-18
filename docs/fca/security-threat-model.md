# Security threat model

Trusted: the owner UID, operator CLI, broker binary, bundled workers/launcher,
Linux kernel, SQLite and linked dependencies. The prototype protects managed
state from malformed requests, accidental corruption, stale leases, duplicate
delivery, executor crashes, broker crashes and competing broker starts.

State/runtime directories must be absolute, non-symlink paths, owned by the
current UID and mode 0700. Database/WAL/shared-memory files must be private
regular files; database opening uses NOFOLLOW. The operator socket is 0600 and
SO_PEERCRED verifies its peer UID. Inputs and exports use bounded regular files
and no-follow opens; export refuses existing files. No runtime state is placed
in the checkout by the tests or demo. Worker environment is cleared and launch
commands are constructed from two bundled executor identities.

Protocol bounds limit allocations, per-lease requests and active contexts.
Unknown operations and fields fail. Same-UID clients can still monopolize
serial operator admission until the two-second read timeout; this is not a
multi-tenant service or comprehensive denial-of-service boundary.

The hash chain detects accidental edits, reordered records, missing records and
inconsistent snapshots/effects. It is unsigned, not externally anchored and
not tamperproof. The owner can modify SQLite, remove triggers and recompute the
entire chain, or roll back the complete store to an older coherent copy. Root
or a malicious owner can replace executables, inspect private IPC and bypass
all user-space policy. No filesystem rollback resistance is claimed.

The bundled programs do not use arbitrary host access, but ordinary same-UID OS
access is not sandboxed. Managed capabilities therefore do not constrain an
untrusted replacement binary. Landlock, seccomp, namespaces, separate worker
UIDs, encrypted state, signed exports and remote attestation are future work.
No external irreversible effect is exposed: there is no network dispatch,
credential provider, email, payment, installer action or device write API.

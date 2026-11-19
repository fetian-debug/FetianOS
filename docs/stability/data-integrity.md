# Data and configuration safety

STAB-001 changes preference reads to nonblocking/no-follow open, fstat of the
opened descriptor, regular-file validation and a bounded read. A FIFO no longer
hangs the startup thread; files growing past the budget cannot force an unbounded
read. This does not impose a hard deadline on a stalled regular/network filesystem.
Symlinks and oversized state still receive safe defaults. Loading never repairs
or overwrites the original file.

STAB-002 validates bookmark/tab field types separately and discards an invalid
URI individually. One malformed URI previously erased all valid loaded values
by falling through to complete defaults. Valid theme/bookmarks now survive the
malformed field. Credential/query/fragment filtering and list limits remain.
There is no schema migration or format change.

Preference saves already stage private files, flush/fsync and atomically rename.
An injected ENOSPC during replace leaves the old bytes unchanged and cleans the
temporary. STAB-005 extends the live-state cleanup finally block to include
write/flush/fsync failures. The old marker remains and the failure propagates.
No automatic account/store/config deletion or destructive repair is introduced.

Rust telemetry already uses create_new, data fsync, rename and directory fsync;
its existing atomic-output test remains passing. FCA uses its existing SQLite
transaction/checkpoint/event model and corruption detection. File/archive staging,
no-overwrite rename, path validation and explicit permanent-delete confirmation
are retained. None of these checks proves arbitrary interrupted cross-device
moves or arbitrary storage hardware failure safe.

There are no risky migrations in this branch and no user files are upgraded.
Existing effects and battery state writers were inspected but not represented
as universally power-loss durable. Preference/daily-helper directory fsync,
backup/version recovery policy and installed-upgrade rollback still need a
separate, tested design before a daily-use data-integrity acceptance claim.

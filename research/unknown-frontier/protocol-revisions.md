# Protocol bookkeeping revision P0a (before any experiment)

[OBSERVED] Windows/Git newline normalization changes raw CSV bytes across
checkouts. The original raw SHA-256 remains in catalogue-freeze.json. Added a
canonical SHA-256 that normalizes CRLF to LF for cross-platform verification.
No hypothesis statement, experiment condition or outcome rule changed. The
runner checks the canonical hash. All individual run source/binary hashes still
identify the exact bytes used in that environment. The pre-experiment Git commit
retains the original raw freeze record; this revision does not hide an experiment.

## P0b — post-experiment formatting only

[OBSERVED] Removed an extra trailing blank line from two Python sources for
Git whitespace checks. No hypothesis, mathematical condition or experiment
changed. The exact original P0 source bytes are frozen in the snapshot and
continue to match both original run plans. The retention helper validates and
preserves that snapshot rather than overwriting it with later source versions.
The canonical text manifest identifies the final checked-in sources separately.

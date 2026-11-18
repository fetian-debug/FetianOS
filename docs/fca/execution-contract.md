# Execution contract, schema version 1

Generate an exact JSON template with `fetian-authority contract-template INPUT_ID`.
Unknown fields and unsupported versions are rejected rather than ignored.

| Field | Accepted meaning |
| --- | --- |
| `schema_version` | 1 |
| `workload` | `fetian.sum-i64`, semantic/protocol version 1, `sum-i64-state-v1` |
| `input` | Imported `managed_immutable_file`, `sha256:` reference, SHA-256 digest |
| `outputs` | Sole managed `sum-i64` result |
| `capabilities` | Input read, checkpoint commit, result commit; optional authority inspect |
| `resource_budget` | CPU quota 1–64 cores, memory 16 MiB–8 GiB, pids 1–32, strict flag |
| `recovery` | Explicit resume, failure behavior `recover` or `fail`, compatibility required |
| `permitted_executors` | Nonempty distinct subset of bundled Rust and Python identities |
| `chunk_size` | 16–128 integers |
| `completion_condition` | `all_input_committed` |

Input is UTF-8 canonical signed decimal i64 values separated by LF, optionally
ending with LF. Empty input, CR, blank lines, spaces, leading plus or zeros,
invalid UTF-8 and out-of-range values fail. Import reads a bounded regular
non-symlink operator file; workers receive only bounded arrays of integers.
The broker copies imported bytes into its immutable managed store and verifies
the SHA-256 reference on use. No live host input pathname reaches a worker.

All intermediate additions must fit i64, including in Python. This makes the
workload deterministic across the two runtimes. A mathematically bounded final
sum is insufficient if an intermediate addition overflows.

Automatic execution after recovery is intentionally unsupported in schema 1:
`automatic_resume: true` is rejected. Recovery reconstructs durable state and
leaves the authority Ready or Suspended for an explicit operator choice.
`failure_behavior: fail` makes unexpected worker loss terminal; `recover`
preserves progress in Ready after fencing and confirmed termination.

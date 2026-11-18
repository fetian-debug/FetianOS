# Managed capability model

Capabilities are explicit contract grants enforced by the broker/store, not
ambient permission inferred from knowing an authority ID.

| Grant | Broker-mediated operation |
| --- | --- |
| `input.read` | Read exactly the bounded chunk at the committed input cursor |
| `checkpoint.commit` | Admit the next semantic checkpoint with its effect |
| `result.commit` | Admit the corresponding managed result and final completion |
| `authority.inspect` | Read the authority's current semantic continuation |

The sum workload requires the first three. Unknown or duplicate grants are
rejected. Every managed request must carry the current lease ID, executor ID
and epoch. The store validates the authority state and operation grant inside
the transaction that would mutate state. Commit requires both result and
checkpoint grants; there is no state-only advance that can skip an effect.

An input grant exposes imported immutable bytes through typed integer arrays.
A result grant writes to the managed SQLite effect ledger only. Executors
receive neither SQL nor an authority store pathname, and the protocol exposes
no arbitrary shell, file path, network request, process launch or host service
operation. Operator management has a separate same-UID socket and admission path.

These are logical managed-API capabilities. Both reference executors are trusted
bundled programs running with the operator's Unix UID. This is not kernel-enforced
isolation from other same-UID files or sockets. A modified malicious worker could
use ordinary OS APIs outside the protocol. Supporting hostile workers requires
an additional analyzed OS boundary, such as separate UIDs/namespaces and a
carefully tested Landlock/seccomp policy. None is claimed active in version 1.

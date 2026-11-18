# Executor protocol version 1

Each message is a four-byte unsigned big-endian byte length followed by that
many bytes of UTF-8 JSON. The length must be 1–65,536. Truncation, oversize,
invalid JSON and unknown envelope or typed argument fields fail closed.

Request envelope:

```json
{"version":1,"request_id":1,"operation":"hello","arguments":{}}
```

Response envelope always contains `version`, `request_id`, `result` and `error`.
Exactly one of result/error is non-null. An error has stable `code` and `message`.
Clients validate response version and matching request ID.

The operator endpoint is a mode-0600 Unix socket in a user-owned mode-0700 XDG
runtime directory. Linux `SO_PEERCRED` must identify the daemon's UID. One
request, with ID 1, is accepted per operator connection. Operators may manage
their own authorities but cannot pass arbitrary executable paths or raw SQL.

Executors use separate inherited Unix socketpairs mapped to standard input and
output. The trusted launcher first establishes a new session/process group and
parent-death SIGKILL. It reports readiness, waits for the broker to attach the
resource group and record the process identity, then receives the resource gate
and execs the allowlisted worker. No workload instruction runs before that gate.

The broker sends a versioned start descriptor with workload identifier,
credential, committed checkpoint and optional explicit test barrier. The worker
must start with exactly one ABI-compatible hello, then numbered requests in
strict order, limited to 4,096 per lease. Its credential contains executor ID,
lease ID and epoch. Supported operations are `hello`, `read`, `commit`, `inspect`
and `complete`. `read` starts exactly at the committed cursor. `commit` carries
semantic progress and `chunk-N` idempotency key; its acknowledgement includes
the committed effect ID and checkpoint. No shell, network, arbitrary path or
process-spawn primitive is exposed.

Test mode additionally admits a deterministic `barrier` whose response is held
until the worker is stopped. Operator `fault-kill`, `stale-probe` and
`fault-arm` are accepted only by a daemon explicitly started with
`--allow-test-faults`. Transaction fault phases terminate that test daemon
immediately before commit or after commit before acknowledgment. They are
absent from normal admission and are never enabled by the supplied user unit.

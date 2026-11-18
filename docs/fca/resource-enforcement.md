# Resource enforcement and availability

The resource budget belongs to the authority contract and persists across
executor changes. The Linux adapter attempts kernel enforcement only inside
the daemon's own user-owned delegated cgroup v2 subtree. It refuses UID 0,
the machine root, a shared group, or missing cpu/memory/pids delegation.

For a suitable delegation, it moves the sole broker process into a manager
child, enables the three controllers, and creates one stable child named with
the validated authority ID. It writes and reads back `cpu.max`, `memory.max`
and `pids.max` before attaching the waiting trusted launcher. The launcher has
not executed workload code at that point. Replacement executors use the same
authority cgroup, preserving its accounting identity and configured limits.
CPU quota is a bandwidth rate, not a lifetime CPU-seconds allowance.
The limits cover executor processes. Broker validation, SQLite work and their
CPU/memory costs remain in the manager group and are not charged to a particular
authority. Full attribution of these service costs is not implemented.

If delegation is unavailable, default contracts explicitly report
`mode: advisory`, `kernel_enforced: false`, and unavailable CPU/memory/pids
controls. Bounded input/chunks remain broker admission limits; they are not
advertised as memory or CPU enforcement. A strict contract fails with
`STRICT_RESOURCE_UNAVAILABLE` before a lease or worker is created.
Partial controller setup or failed limit readback fails execution admission.
There is no privileged fallback, root request or write to arbitrary cgroup paths.

The optional manual systemd user unit requests `Delegate=cpu memory pids`.
The core only consumes the Linux delegation and can be supervised otherwise.
Controllers still depend on the host's parent delegation. GPU budgets, priority
scheduling, cumulative CPU limits and distributed resource accounting are absent.

Local WSL validation observed `DELEGATION_UNAVAILABLE`; strict rejection and
truthful advisory reporting passed. Actual throttling, memory OOM, pids exhaustion
and cgroup accounting continuity require a suitably delegated Linux test host.
The existence of adapter code is not evidence that these limits were enforced
in the recorded environment.

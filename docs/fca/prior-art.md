# Prior art and research position

Primary sources checked 18 November 2026. This prototype combines established
mechanisms. It does not claim a new kernel primitive, first invention, patent
novelty or superiority over mature distributed workflow systems.

| Work | Relevant existing idea | FCA relationship |
| --- | --- | --- |
| [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html) | Hierarchical resource domains and delegation | Reuses its controllers; durable semantic state lives outside the kernel |
| [systemd cgroup delegation](https://systemd.io/CGROUP_DELEGATION/) | Supervisor grants a subtree to a manager | Optional deployment adapter, not replaced init or authority database |
| [Fuchsia jobs](https://fuchsia.dev/fuchsia-src/reference/kernel_objects/job) | Jobs group processes, policy and resource control | FCA is a userspace logical work record, not a Zircon kernel job |
| [Fuchsia handles](https://fuchsia.googlesource.com/fuchsia/+/master/docs/concepts/kernel/concepts.md) | Typed handles carry rights | FCA uses broker-managed grants; it does not reproduce kernel handle isolation |
| [CRIU](https://github.com/checkpoint-restore/criu) | Checkpoint/restore of running Linux applications | FCA transfers explicit workload state across languages, not a process memory image |
| [Resource Containers, Banga/Druschel/Mogul, OSDI 1999](https://www.usenix.org/conference/osdi-99/resource-containers-new-facility-resource-management-server-systems) | Resource principal can be separated from a protection domain | Direct precedent for resource ownership independent of individual processes |
| [Kubernetes Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) | Controllers replace ephemeral execution contexts | FCA keeps a local authority ID and semantic checkpoint across its bundled executors; no cluster scheduling |
| [Temporal Workflow Execution](https://docs.temporal.io/workflow-execution) | Durable logical execution, event history and replay | Strong precedent for work outliving workers; FCA is a much smaller local semantic ABI experiment |
| [Zap, OSDI 2002](https://www.cs.cmu.edu/~sosman/publications/osdi2002/osdi2002_zap.pdf) | Pods and transparent application migration | FCA does not migrate arbitrary legacy processes or virtualize their complete OS namespace |
| [NixOS manual](https://nixos.org/manual/nixos/stable/) | Declarative system configuration and generations | A contract describes one workload; no functional system deployment or rollback is implemented |
| [Agent libOS, Zhang, arXiv 2606.03895v3](https://arxiv.org/abs/2606.03895v3) | Persistent agents, typed authority, budgets, provider effects and durable evidence | Substantial conceptual overlap; FCA has no model, tool synthesis, information-flow system or external effect providers |
| [CapROS/EROS sources](https://www.capros.org/overview.html) | Capability systems and persistence | Prior authority/persistence foundations; FCA's trusted same-UID workers provide a weaker OS boundary |
| [Kleppmann, fencing tokens](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html) | Reject stale writers at the resource using increasing generations | Reused directly at FCA's transactional effect boundary |

The demonstrated integration is one persistent local authority with a fixed
contract, managed effect ledger and increasing epoch, replacing a terminated
Rust executor with an independent Python executor implementing the same explicit
continuation ABI. This is a concrete engineering result, not evidence of broad
architectural novelty. A useful next experiment is a second stateful workload
and a formally stated external-effect protocol under deterministic fault tests.

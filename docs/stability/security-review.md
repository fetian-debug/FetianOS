# Security and reliability review

No new root helper, network listener, capability, setuid permission or broad IPC
exception is introduced. Session entry still rejects root, requires a managed
runtime directory and prevents concurrent sessions. Descriptor ownership is
tightened. Tests use only disposable fixtures; root-run test wrappers drop the
fixture compositor to uid/gid 65534, not the real desktop user/session.

The session flock is cooperative ownership by the wrapper, not an authorization
boundary against the same user. Regression fixtures also verify a second wrapper
is rejected while the first compositor runs and that normal termination releases
the lock. SIGKILL of the wrapper cannot execute its cleanup; logind/SDDM cleanup
of that case still requires guest validation. No guarantee about surviving a
SIGKILL with an independently surviving compositor is inferred.

The source audit follows service sandboxing, private FCA directories/socket/store,
peer identity, bounded frames, contract capabilities, fencing and recovery checks.
Same-UID hostile code is still outside FCA's isolation boundary. Unsigned hashes
do not defeat owner rollback. Optional resource enforcement does not become
available merely because a rejection test passed.

Preference reads reject special files and final-component symlinks on Linux and
bound bytes. Schema filtering still excludes persisted URI credentials. Archive
and file operations retain descriptor-relative traversal and no-overwrite policy.
No secret or credential was added to test output intentionally; fixture live
credentials are the existing public live-media account, not installed credentials.

`cargo metadata --locked --offline` verifies resolvable lockfiles, not security
advisories. The first baseline lacked cargo-audit. Its failure is preserved.
Any later audit must identify its tool and advisory database revision and retain
warnings as well as vulnerability results. A lockfile scan does not audit all
distribution packages, Python/GI libraries, firmware, boot chain or the kernel.
[RustSec tool documentation](https://github.com/rustsec/rustsec/blob/main/cargo-audit/README.md).

The supplemental official cargo-audit 0.23.0 scan completed on both lockfiles:
zero listed vulnerabilities and no informational warnings at advisory revision
`7133866a6b44d6d3e1994ae6a48a296553c3c3da` (1,550 advisories).
The asset digest was checked before execution. Exact commands, lock hashes and
JSON results are retained in evidence/dependency-audit; the original missing-tool
results remain unchanged. This is a dated scan, not future vulnerability immunity.

Secure Boot, actual service sandbox runtime, exposed listening ports, installed
system permissions, log confidentiality, real lock readiness and hostile-user
penetration testing remain unverified. No comprehensive security certification
or absence of all P0/P1 defects is claimed.

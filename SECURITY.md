# Security

FetianOS is a developer preview. Do not treat the included image profile as a
validated production installation or security boundary.

The Rust system collector forbids unsafe code, has no third-party crates and
performs no subprocess or network operations. Its service uses a dynamic user,
an empty capability set, filesystem protections and a dedicated state directory.
Atomic replacement avoids partial snapshots; stale snapshots must be detected
using their timestamps. Health reports contain local hardware identity and
metrics and are not uploaded automatically.

Package operations must retain repository signature verification and Linux
authorization. Never run an AI provider or desktop shell with unrestricted root
access. Destructive storage actions require an explicit target review and user
confirmation. Credentials must stay outside source, generated images and logs.

There is no verified Secure Boot, encrypted installation, rollback or supported
security update lifecycle yet. Before release, validate the installer and sandbox
on the target distribution, pin image inputs, publish image checksums, and
establish a private vulnerability reporting channel. Do not publish secrets in
public bug reports.

Live-media account provisioning is a separate root oneshot, guarded by the
Archiso command line, overlay root and boot-media mount. The public disposable
guest credential is `fetian`/`fetian`; root is locked and sudo still authenticates.
The helper never resets an unrecognized existing account/home or provisions an
installed system. Calamares must remove/convert live credentials and the live
sudo rule before installation can be enabled. See [boot/login policy](docs/boot-login.md).

# FetianOS documentation

FetianOS is a developer-preview Manjaro-compatible Wayland desktop. Rust system
services, existing applications and recovery paths are retained while the
desktop is improved. Installation remains disabled pending acceptance.

## Start here

- [Published preview downloads](../website/downloads.md)
- [Build the ISO](iso-build.md)
- [CI/CD, releases and website publishing](ci-cd.md)
- [Disposable UEFI VM tests](vm-testing.md)
- [Live boot and login](boot-login.md)
- [Daily usability](daily-usability.md)
- [Recovery procedures](recovery.md)

## Applications and architecture

- [One primary application per task](application-strategy.md)
- [FetianFiles features and limitations](fetian-files.md)
- [Architecture and Rust system foundation](architecture.md)
- [Experimental Continuation Authority architecture (FCA)](fca/README.md)
- [Hyprland candidate integration](hyprland-integration.md)
- [Development workflow](development.md)
- [Security boundaries](security.md)

## Validation and installation status

- [System stabilization audit and acceptance limits](stability/final-stability-report.md)
- [Latest recorded local verification](verification-2026-11-18.md)
- [Actual UEFI/live-account boot and greeter evidence](verification-2026-11-18-uefi.md)
- [Test commands and earlier milestones](testing.md)
- [Release acceptance gates](release-acceptance.md)
- [Disabled installer architecture](installer-architecture.md)
- [Known limitations](known-issues.md)
- [Roadmap](roadmap.md)

Each published ISO includes its own build metadata and VM evidence. Those
records describe that specific image; older milestone reports do not substitute
for its test results.

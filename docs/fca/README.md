# Continuation Authority Architecture (FCA)

FCA is an opt-in, unprivileged Rust research prototype in the existing FETIANOS
repository. A durable logical authority survives its executor process. The
working workload is a signed 64-bit sum over imported immutable integers:
Rust can be killed and Python can continue the same authority from its last
committed semantic checkpoint. This is an application-level execution model.

The default desktop, systemd boot, Sway recovery, optional Hyprland, existing
applications, dependency-free Rust metrics and disabled installer are unaffected.
FCA is excluded from the default Cargo workspace and default ISO staging.

## Reproduce on Linux

Requires Rust 1.89 or newer, a C compiler for bundled SQLite, Python 3, and Linux
Unix sockets and `/proc`. Run as a normal user. The first build fetches the
separately locked dependencies; subsequent builds can use `--offline`.

```sh
bash scripts/build-fca.sh --release
cargo test --manifest-path system/fetian-fca/Cargo.toml --locked
FCA_BIN_DIR="$PWD/system/fetian-fca/target/release" python3 system/fetian-fca/tests/process_tests.py
system/fetian-fca/target/release/fetian-authority --json demo-handoff
```

The demo creates a private temporary broker and input, stops Rust at a recorded
three-chunk barrier, durably fences its epoch, kills and waits for its owned
process group, and runs Python. It checks the independent sum, unchanged
checkpoint across the kill, distinct PIDs, increasing epoch, 64 unique effects,
and rejection of an old Rust commit. Temporary demo state is removed afterward.
The emitted JSON is the evidence; redirect it to a report to retain it.

## Use a persistent authority

Use your session's existing `XDG_RUNTIME_DIR`. For an isolated experiment,
create a mode-0700 temporary directory and export its path as `XDG_RUNTIME_DIR`.
State is under `${XDG_STATE_HOME:-$HOME/.local/state}/fetian-fca`.

```sh
FCA="$PWD/system/fetian-fca/target/release/fetian-authority"
"$FCA" daemon start
printf '1\n2\n3\n' > /tmp/fca-input.txt
"$FCA" input import /tmp/fca-input.txt
# Copy the returned sha256:... input_id into the next command.
"$FCA" contract-template sha256:YOUR_INPUT_DIGEST > /tmp/fca-contract.json
"$FCA" create --contract /tmp/fca-contract.json
# Copy the returned ca_... identity into the commands below.
"$FCA" run ca_YOUR_ID --executor rust
"$FCA" inspect ca_YOUR_ID
"$FCA" verify ca_YOUR_ID
"$FCA" export ca_YOUR_ID --output /tmp/fca-report.json
"$FCA" daemon stop
```

Other commands: `list`, `checkpoint ID`, `suspend ID`, `resume ID`, `cancel ID`,
`handoff ID --executor python`, `events ID --after N`, `daemon status`.
`--json` emits compact JSON; default output is indented structured JSON.
Errors contain a stable code and exit nonzero. Export refuses overwriting files.
`checkpoint` is a durable barrier for the last accepted managed state, not a
snapshot of arbitrary executor memory. `resume` makes a suspended authority
Ready; explicitly `run` it with a compatible executor afterward.

## Integrate only when requested

After building FCA release binaries, `scripts/stage-profile.py DEST --with-fca`
copies its four Rust programs, trusted Python worker, CLI wrapper and manual
user unit into a fresh profile. It does not enable the unit or change desktop
startup. The supplied user unit can be started manually after deliberate
installation with `systemctl --user start fetian-authorityd`. There is no
default target or privileged helper. An OpenRC or other supervisor may launch
the same foreground daemon; the core has no systemd API dependency.

## Read the specification

- [Architecture and source map](architecture.md)
- [Authority specification](continuation-authority-spec.md)
- [Execution contract](execution-contract.md)
- [Executor protocol](executor-protocol.md)
- [Lifecycle](lifecycle.md)
- [Fencing and handoff](fencing-and-handoff.md)
- [Capabilities](capability-model.md)
- [Resource enforcement](resource-enforcement.md)
- [Security threat model](security-threat-model.md)
- [Recovery model](recovery-model.md)
- [Prior art](prior-art.md)
- [Limitations](limitations.md)
- [Validation and measurements](validation-report.md)

## Phase 2 research

- [Research validation, all 1,000 randomized cases and retained evidence](research-validation.md)
- [Fault windows and outcome definitions](fault-model.md)
- [Measured performance distributions](performance.md)
- [Security review and demonstrated boundaries](security-review.md)
- [Evidence-based prior-art comparison](prior-art-comparison.md)
- [Inspected Phase 1 baseline](phase-2-baseline.md)

The dedicated FCA workflow runs fast/fault/security checks on changes. All
1,000 randomized experiments and the performance matrix run on explicit manual
or scheduled validation. This workflow creates research artifacts; it never
builds or publishes an ISO. Choose fresh report directories for each run.

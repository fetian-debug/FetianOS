# Reproduce round 2

[OBSERVED] Tested with Rust 1.89.0, Python 3.10.12, a native linker and
unprivileged x86_64 Linux under WSL2. No third-party Python packages, Cargo
dependencies, external solver, root permission or hardware access is required.
All models and the Rust executable are standalone; no FCA process is used.

```sh
python3 research/unknown-frontier/round-2/reproduce.py --output .build-tools/frontier-round2-reproduction
python3 research/unknown-frontier/round-2/verify.py
```

The wrapper compiles the Rust program in a temporary directory and runs the
two finite-channel seeds, original-80 witness suite, other-field controls and
P3 linear family. Choose a fresh output path; retained data are never overwritten.
Never regenerate or edit the original hypothesis catalogues for replication.
Use `--rustc /path/to/rustc` to select an installed compiler explicitly.

Expected each P2 seed: 1,184 exhaustive physical-event/input cases, 1,000 random
propagation cases, ten exposed controls and eight invalid inputs. These are
simulated word faults, not hardware injections. Expected P3: sixteen conditions,
4,072 error syndromes and 1,600 random cases. The strong generic baseline and
the Rust decoder both require four metadata bits for five word bits and three
for six. The expected novelty conclusion is **no new capability established**.

[OBSERVED] The original-80 evidence comprises thirty groups, not 80 independent
runtime implementations. Several statements have only a located theorem,
written argument or unresolved empirical status. The suite references earlier
complete optional-stopping evidence rather than claiming to execute it anew.
The 4,096-strategy nonlocal-game enumeration is entirely classical; it does not
implement a quantum resource or beat the classical bound.

[OBSERVED] Exact experiment source bytes are retained in binary archives for
source-hash checking. Text manifests normalize CRLF to LF so Git/Windows
checkout conversion does not falsely break verification. Compiler/environment
changes can change binary hashes; no bit-for-bit binary reproducibility claim
is made. The verifier checks finite records and lower-bound certificates, not
asymptotic novelty, physical premises or external peer review.

[OBSERVED] A temporary LF-only copy of this research tree also passed both the
round-2 verifier and the parent evidence verifier. This checks checkout
portability and preservation of earlier evidence, not external replication.

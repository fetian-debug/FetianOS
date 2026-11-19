# Reproducibility

[OBSERVED] Actual executions used unprivileged x86_64 Linux under WSL2, Python
3.10.12 and Rust 1.89.0. Exact kernel/source/compiler details are retained in
raw-results. No third-party Python packages, Cargo dependencies, SMT solver,
external service, root privilege, device access or installed OS module is needed.
No physics or biological hardware experiment was performed.

On Linux with Python 3.10+, Rust 1.89+ and a working native linker available:

```sh
python3 research/unknown-frontier/reproduce.py --output .build-tools/frontier-replay-2090 --seed 2090 --follow-on
python3 research/unknown-frontier/reproduce.py --output .build-tools/frontier-replay-2091 --seed 2091
python3 research/unknown-frontier/verify_evidence.py
```

[OBSERVED] The wrapper compiles both independent Rust programs in a temporary
directory and removes only that temporary build afterward. Every output path
must be fresh. Existing evidence is never overwritten. Outputs include every
input and oracle/prototype/baseline result, transformations, mutants,
counterexamples and protocol/source hashes. The hypotheses CSV is frozen;
never run create_catalogue.py as part of replication. Its source is retained
only to explain catalogue construction, not to revise original statements.

[OBSERVED] Git/Windows can normalize line endings. catalogue-freeze.json keeps
the original raw CSV hash and a canonical CRLF-to-LF hash; the runner checks the
latter. Raw source snapshots retain the exact experiment bytes for checking
recorded source hashes. A fresh checkout can have different raw byte hashes
without changing the statement or computation. Binary hashes also depend on
compiler/toolchain/linker/environment; exact binary reproducibility is not
claimed. Results must agree, not PIDs, runtime durations or binary hashes.

Expected per seed: 10,733 base evaluations, 2,000 metamorphic evaluations, 729
grid-oracle checks, eight exposed mutants, seven invalid lines rejected by each
binary, seven belief cases and six schedule permutations. Expected conclusion:
functional agreement but **no new capability established**. The follow-on model
has exactly 65,536 equally likely paths, not 65,536 sampled physical coin tosses.

[UNVERIFIED] The experiment has not received external peer review. Reproduce it
in a fresh container/VM and inspect the proofs rather than trusting the printed
summary. No production solver throughput or cross-platform timing claim is made.


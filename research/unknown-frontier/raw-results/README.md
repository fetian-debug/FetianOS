# Retained evidence guide

[OBSERVED] All entries are local experimental records, not signed attestations.
The seed directories contain every right-hand side and transformed input, exact
geometry result, Rust prototype/baseline result, mutants and counterexamples.
The two seeds repeat the same 729-case exhaustive grid; do not count those as
different input domains. Random samples are not guaranteed unique.

| Artifact | Meaning |
|---|---|
| catalogue-freeze.json | Original raw and newline-canonical hashes of the 100 hypotheses |
| search-ledger.json | 65 web-index queries/primary opens; no exhaustive-search claim |
| prior-art-screen.json | Twenty scoped reviews, ordinal scores and unresolved cells |
| seed-2090, seed-2091 | 10,733 base + 2,000 metamorphic evaluations each, plans and controls |
| certificate-change-supplement.json | Separate H003 false-rejection example, supplementing P0's false-acceptance example |
| follow-on/coin-paths.jsonl.gz | All 65,536 fair-coin bit strings and stopping outcomes |
| follow-on/summary.json | Exact event counts/probabilities and complete 32-step control trajectory |
| experiment-source-snapshot.tar.gz | Exact original P0 source bytes matching recorded hashes |
| compiler.txt | Actual Rust 1.89.0 compiler/version/host record |
| evidence-manifest.json | Raw binary-archive and newline-canonical text hashes; not a signature |

[OBSERVED] The standalone verifier recomputes geometry for all retained
feasibility fixtures, validates small cases with a second oracle, counts the
complete follow-on paths, checks the source snapshot and verifies file hashes.
The reproduction wrapper was actually run on Linux using fresh output/build
directories. Verification also passed after copying the research tree and
normalizing all text to LF, emulating Git's checkout conversion. This is local
portability checking, not independent external replication.

[UNVERIFIED] The web screen does not establish patent coverage, legal priority,
absence of prior work or completeness of academic search. Some closest-code
pointers were not found; none of the external implementations was benchmarked.
The artefact's mathematical and finite-model conclusions are deliberately
narrow. Read the original protocols before interpreting a green summary.

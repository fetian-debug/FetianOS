# Review correction R1

[OBSERVED] Before constructing the original-80 test suite, adversarial review of
our own classification found that H055 does not require writer progress or
continued successful allocation. Blocking updates is a loophole in a purported
universal impossibility argument. Changed its annotation from FALSIFIED to
NEEDS FORMALIZATION; the original hypothesis itself is unchanged. The first-pass
CSV is preserved under raw-results/review-first-pass.csv. Final counts become
40 known conditional mechanisms, 32 explicit-model falsifications, six claims
needing formalization and two unverified physical claims. Finite hidden-reader
models only support the conditional safety/space/progress tradeoff described.

## R2: retained harness failure

[OBSERVED] The first original-80 witness run completed its checks but failed
while generating the summary: a Hamming-loop local variable reused the name of
the parity-case list. The raw checks, failure traceback, source hash and exact
failed source are retained in original-80-seed-2090. Renamed that local variable
and reran in a fresh directory. This is a harness correction, not a changed
hypothesis, relaxed assertion or successful result substituted for a failed one.

## R3: supplemental plan metadata

[OBSERVED] The first other-fields control run retained complete outcomes but
omitted its per-run plan file. Preserved those records and reran the same
unchanged finite conditions in other-fields-planned with a source/protocol hash
written before enumeration. Count 4,096 distinct classical strategies once;
the repeated metadata-validation run is not a larger strategy space.

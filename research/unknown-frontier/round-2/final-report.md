# Round 2 final report

[OBSERVED] All 80 original candidates left outside the first shortlist now have
individual annotations, exact-statement hashes, primary anchors, scope and
counterexample/evidence hooks. Thirteen additional hypotheses/models were
investigated (H101–H112 plus the separately registered H113 extension).
**No genuinely new, previously unavailable computing capability is established.**
The most concrete finding is a restricted exact metadata bound, not an OS feature
or a superiority result over the strongest generic baseline.

## 1. Assumption challenged

[HYPOTHESIS] Extra arbitrary borrowed data might enable computation/correction
with less retained trusted information. Also challenged: unrestricted reuse of
negative information, observation-free optimal decisions, universal prediction,
parallel local sampling and individual counterfactual identification.

## 2. Findings

[OBSERVED] The remaining-80 review yields 40 established conditional mechanisms,
32 explicit-model falsifications, six statements needing formalization, and
two unverified physical-energy claims. These are not 80 independently
implemented algorithms. [FORMALLY PROVEN — restricted written argument]
For the declared channel, five arbitrary word bits require four metadata bits,
while six require three. [EXPERIMENTALLY DEMONSTRATED] Both thresholds were
reached by Rust and an independent generic codebook baseline.

## 3. Exact new capability

[UNVERIFIED] None established. The working decoder restores arbitrary words
under an explicit two-window single-fault model. General zero-error coding
already has that capability under the same information/resource assumptions.
The word lengths differ in the 5/6 comparison, so it is not a same-resource
baseline separation. Retained metadata is not total working space.

## 4. Closest prior work

[ESTABLISHED BY PRIOR WORK] Finite zero-error side-information coding supplies
the confusability-graph model. [Located primary paper](https://ieeexplore.ieee.org/document/1228155/).
[PRIOR REPORTED, not independently reproduced here] Recent catalytic results
already claim relevant time/space advantages under precise output models;
[2026 preprint](https://arxiv.org/abs/2610.24377). Broader primary anchors and
alternative names appear in other-fields-review.md and the individual CSV.
An exhaustive priority/patent review is not claimed.

## 5. Difference from prior work

[OBSERVED] We provide small exact prototypes, adversarial witnesses and a
written linear-code family derivation. [UNVERIFIED] The exact formulation's
publication priority is unresolved. Different packaging, a compiler wrapper or
an application to borrowed memory does not establish a new computing capability.

## 6. Evidence for or against separation

[EXPERIMENTALLY DEMONSTRATED] Each seed 2090/2091 includes all 1,184 finite
word/window/fault combinations, 1,000 random reversible-circuit propagation
checks, ten exposed mutation/assumption controls and eight malformed-input
rejections. Generic graph colouring reaches the same four/three metadata-bit
bounds. [OBSERVED] This defeats the capability-gap suggestion rather than
establishing it. The repeated exhaustive cases are replications, not different
state spaces. Random propagation checks claim no universal correction ability.

## 7. Written mathematical results

[FORMALLY PROVEN — written, not proof-assistant checked] Clique lower bounds
apply to ANY encoder at n=5 and n=6. For every m>=3, LINEAR retained metadata
requires m+1 bits at n=2^m-3 and m bits at n=2^m-2. The latter is a classical
parity-check-style derivation; exact priority is UNVERIFIED. No larger-n
nonlinear bound, verified machine code or new complexity-class separation is
proved. See mathematical-findings.md for the complete argument and exclusions.

## 8. Experimental findings only

[EXPERIMENTALLY DEMONSTRATED] P3 validates sixteen constructions (m=3..10),
4,072 allowed error syndromes and 1,600 seeded random restoration cases.
The original-80 suite has thirty evidence groups, including 729 exact geometry
fixtures, 500 additive updates, 502 partial-parity transcripts and 128 Hamming
code/fault fixtures; some IDs are covered by prior theory or written reasoning,
not direct empirical implementations. Other-field controls enumerate all
4,096 classical magic-square strategies, two SCM truth tables, and 128 primitive
two-spin update trajectories. None is a physical/quantum experiment.

## 9. Failures

[FALSIFIED] H104's error-count-only metadata formula; H108's universal
individual-response identification from marginals; H111's arbitrary synchronous
Gibbs correctness; and the specifically scoped original-80 countermodels.
[OBSERVED] One harness summary failed from a reused Python variable name;
its traceback, exact failed source and raw checks are preserved. The corrected
run used a fresh directory. H055 was downgraded from a first-pass false claim
of impossibility to NEEDS FORMALIZATION because writer progress was absent.
These corrections did not change the frozen original statements.

## 10. Remaining counterexamples/open questions

[OBSERVED] Out-of-model faults, corrupt metadata and inadequate checks have
retained witnesses. [UNVERIFIED] Exact nonlinear metadata optima for larger
lengths such as n=13 remain unresolved in this investigation. So do exact
priority of H113, six underspecified original statements and two physical
energy claims. The linear theorem does not resolve those nonlinear questions.

## 11. Limits and assumptions

[OBSERVED] Trusted metadata/encoder/decoder, protected gates except two declared
fault windows, arbitrary binary words, exact finite arithmetic and a fixed
channel description. Static code tables and control scratch are disclosed and
not counted as retained protected metadata. No arbitrary machine faults,
malicious code, quantum hardware, actual catalytic asymptotic algorithm,
energy saving, production service or OS fault-tolerance guarantee is established.

## 12. Independent reproduction

[OBSERVED] reproducibility.md provides Linux/Rust/Python commands and expected
counts. Raw records, original/follow-on protocols, source snapshots, compiler
metadata and an independent evidence verifier are retained. [UNVERIFIED]
External peer review and independent researchers' replications have not occurred.
Checksums are provenance checks, not signed attestations.

## 13. What defeats novelty

[OBSERVED] An equal-assumption conventional decoder already matches the proposed
capability and metadata budget. A prior equivalent theorem/construction would
also defeat a future exact-priority claim. Missing an exact search phrase proves
nothing. A future claim must add a genuine, explicit resource/information gap
and survive a stronger baseline, not rename the current known coding problem.

## 14. Publication judgment

[HYPOTHESIS / judgment] Useful as an auditable negative research artifact and
restricted mathematical note after further priority review. It does not yet
justify publication as a new computing capability or breakthrough. A next
positive direction would need a sharply specified nontrivial separation and
independent scrutiny before any integration.

## Platform preservation

[OBSERVED] Every mission change is under research/unknown-frontier/round-2.
Earlier research, the original hypotheses, FCA, default workspace, apps,
boot/login, Sway recovery, services and ISO workflow are unchanged. No merge
to main, ISO build, release upload or service enablement occurred. Release
metadata was read only to verify the existing preview assets remained intact.

# Unknown Frontier: final research report

[OBSERVED] This completed, bounded discovery round establishes **no new computing
capability**. It produces 100 frozen candidates, a 20-candidate prior-art screen,
three detailed destruction reports, reproducible Linux artifacts and retained
negative results. It does not prove that all 100 ideas are false or that future
research in these fields cannot succeed. Eighty candidates have not received
individual prior-art review; unresolved shortlist cells remain explicit.

## 1. What assumption did we challenge?

[HYPOTHESIS] Rejected computation, unobserved state and alternative execution
orders might provide useful information without redoing original work or taking
every observation. Discovery also examined representation, precision, memory,
privacy, coding, compression, compiler equivalence, physical reversibility,
biological feedback, statistics, human intent and hardware-error evidence.

## 2. What did we discover?

[ESTABLISHED BY PRIOR WORK] Much of the promising space already has mathematical
and implementation counterparts. [OBSERVED] The strongest artifact reproduces
negative-certificate reuse, but an equivalent ordinary projection achieves the
same capability. [FALSIFIED] Several stronger generalizations fail on small
explicit examples. These are useful exclusions, not a claimed breakthrough.

## 3. What is the exact new capability?

[UNVERIFIED] **None established.** [EXPERIMENTALLY DEMONSTRATED] A standalone
Rust certificate classifier answers the fixed six-constraint, two-real-variable
feasibility problem without per-request LP solving. The strong conventional
baseline does the same; the capability itself is not new.

## 4. What was the closest existing work?

[ESTABLISHED BY PRIOR WORK] For H005: Farkas certificates, Benders feasibility
cuts and variable elimination; [SCIP implementation](https://scipopt.org/doc-9.2.4/html/benderscut__feas_8h_source.php)
and [BendersLib's cut contract](https://benders.dev/latest/api/cuts.html).
For H007: [partial-observation shielding](https://arxiv.org/abs/2204.00755) and
[belief-state planning](https://people.csail.mit.edu/lpk/papers/aij98-pomdp.pdf).
For H014: [context-sensitive DPOR](https://researchmgt.monash.edu/ws/portalfiles/portal/257767040/71313718_oa.pdf)
and [GenMC](https://plv.mpi-sws.org/genmc/). These are closest located anchors,
not a proven exhaustive nearest-work ranking. See prior-art-review.md for 20
scoped reviews, alternative names and technical disclosures.

## 5. Why is our result different?

[OBSERVED] It is a small independently inspectable reproduction and adversarial
artifact inside the repository. [UNVERIFIED] That packaging, language choice or
new application setting is not evidence of a scientific capability difference.
No algorithmic novelty, scale advantage or superiority to those projects is
claimed. No external solver or model checker was benchmarked here.

## 6. What evidence establishes the difference?

[FALSIFIED] The novelty requirement of a capability gap fails: both classifiers
have zero online LP solves and equivalent feasible regions under the same
assumptions. [EXPERIMENTALLY DEMONSTRATED] Each of two seeds checks 10,733 base
and 2,000 transformed inputs with zero mismatches. The evidence supports
functional agreement, not a novel difference. Complete JSON-line records,
plans, independent oracle checks and eight mutation controls are retained.

## 7. What have we formally proven?

[FORMALLY PROVEN — restricted written mathematics] The five inequalities are
necessary and sufficient for this fixed matrix; they are equivalent to interval
projection. A complete-belief shared action is one-step safe. The two-state
cost and three-action context examples refute the stated stronger extensions.
The bounded-actuator fixture cannot maintain its setpoint. Alpha-spending has
its stated error bound under the specified null. These are elementary known-
mechanism derivations, **not new theorems**, proof-assistant checks or verified
machine-code correctness. See mathematical-model.md and proof-or-falsification.md.

## 8. What have we only experimentally demonstrated?

[EXPERIMENTALLY DEMONSTRATED] Rust classifier/baseline agreement on bounded
fixtures, exact geometry/grid-oracle agreement on 729 small fixtures per seed,
malformed-input rejection, seven finite belief cases and six finite schedules.
The statistical continuation exhaustively enumerates 65,536 length-16 fair-coin
paths. Optional fixed-time testing rejects 5,368 paths (~8.19%); final-time-only
testing rejects 1,394 (~2.13%); conservative alpha-spending rejects 16 (~0.0244%).
This is an exact finite model, not a physical coin experiment or a free-power
improvement. A separate 32-step control simulation shows unavoidable drift
under a saturated actuator; it is not a biological/hardware experiment.

## 9. What failed?

[FALSIFIED] The new-capability separation for H005; H003's arbitrary-matrix
rejection reuse; H010's universal full-information optimality without observing;
H013/H015's extrapolation of one sampled commutation to all contexts; H085's
universal perfect adaptation with insufficient actuation. [OBSERVED] The eight
intentional mutation defects were exposed. No functional classifier mismatch
occurred in the retained bounded experiments. A matrix-mutant interpretation
was distinguished explicitly: false acceptance is not the same as unsound
rejection, so a separate false-rejection witness is retained.

## 10. What counterexamples remain?

[OBSERVED] All counterexamples remain in raw-results rather than being patched
away or hidden by weaker wording. Changed coefficient matrices require fresh
certificate validation; incomplete beliefs can permit unsafe actions; an
initial commutation can fail after another action. [UNVERIFIED] Larger models,
weak memory, arbitrary matrices, physical sensors and the remaining candidate
space have not been eliminated by these examples.

## 11. What assumptions limit the result?

[OBSERVED] Fixed matrix, exact bounded integer inputs but real feasibility,
trusted local CLI programs, explicit finite observation/state models, and
independent fair coins for the statistical null. Preprocessing is not free;
zero online solves do not mean zero work or metadata. [UNVERIFIED] No result
here establishes fault tolerance, security isolation, energy savings, real-time
scheduling, statistical validity under arbitrary distribution shift, or an
arbitrary-program OS facility.

## 12. Can another researcher reproduce it?

[OBSERVED] Yes: reproducibility.md gives dependency-free Python/Rust Linux
commands, seeds, expected counts, exact-byte source snapshots, canonical CSV
hash, raw records and an evidence verifier. [UNVERIFIED] Independent external
replication has not occurred. Local hashes identify artifacts but are not
signed attestations or external review. Output directories must be fresh.

## 13. What would disprove our novelty claim?

[OBSERVED] No positive novelty claim survives. The equal-assumption projection
construction and located prior art already defeat the proposed gap. For any
future revision, an earlier equivalent method or same-information baseline
with the same capability would defeat novelty again; a functional counterexample
would separately defeat correctness. Failure to find a paper would prove neither.

## 14. Is this worth publishing?

[HYPOTHESIS / publication judgment] Worth sharing as a transparent negative
research/reproducibility artifact or teaching note, with the limitations intact.
It currently does not justify a paper claiming a new computing capability,
architectural breakthrough, patentability or first-ever result. A publishable
positive claim would require a new sharply stated gap, stronger prior-art
review, independent scrutiny and evidence beyond repackaging established work.

## Preserved platform

[OBSERVED] All mission changes stay under research/unknown-frontier. No FCA,
boot/login, application, Sway recovery, ISO build configuration or production
service is changed or enabled. No ISO was built, replaced or published. The
research branch is separate from main; no integration is justified by this
negative novelty result. The follow-on statistics/control exploration extends
the search into other fields without changing the original claims.

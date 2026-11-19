# Destruction reports: strongest three bounded candidates

## H005 — useful information from infeasible requests

[ESTABLISHED BY PRIOR WORK] The strongest attack is equivalence, not a timing
counterexample. Farkas certificates already separate impossible right-hand
sides; Benders feasibility cuts already reuse this negative information.
A conventional fixed-matrix projection can precompute the same region.
[FORMALLY PROVEN] For the experiment matrix the five certificate tests and the
interval-intersection baseline are algebraically equivalent. Both require zero
online LP solves. The functional property is true; the proposed baseline gap
is false. This is an important distinction from falsifying the mathematics.

[EXPERIMENTALLY DEMONSTRATED] Seeds 2090 and 2091 each checked 10,733 original
fixtures and 2,000 transformed fixtures against two Rust implementations and an
independent exact-rational geometry oracle, with zero disagreements. The 729
small exhaustive fixtures also match a separate integer-grid oracle. The
controls expose all eight intentionally defective variants, including omission
of each individual cut. These counts are evaluations, not a claim that random
sampling produced that many unique right-hand sides.

[FALSIFIED] Reusing these cuts after changing A is unsound: with
b=(2,2,2,2,-1,2), replace the x+y row by the zero row. The old cache accepts,
but the new constraint 0<=-1 is impossible. A matrix identity or a fresh
nullspace validation is necessary. This counterexample does not refute H005,
whose fixed-A assumption is explicit. This witness shows false acceptance.
The separate certificate-change-supplement.json shows a false rejection for
H003: changing the final row for b=(0,2,0,2,2,-1) makes the old rejected
problem feasible. Both unsafe directions are retained.

[OBSERVED] Disposition: no new computing capability established. Retain the
small artifact as an independently checkable reproduction/negative result.
No production admission service or other runtime module is integrated.

## H007 — skip sensing while remaining safe

[ESTABLISHED BY PRIOR WORK] Belief-state reasoning, robust feasible controls,
partial-observation shielding and active sensing already occupy this space.
A common action set is a direct set intersection, not a new source of
information. The fully observed controller has information the blind controller
lacks; a comparison that hides the sensing bill is unfair.

[EXPERIMENTALLY DEMONSTRATED] All seven nonempty beliefs over {-1,0,1} match
an independently enumerated state/action table for one-step safety. The
conditional safety property is preserved. No unbounded-horizon robustness,
physical robot experiment or new POMDP algorithm follows from this toy model.

[FALSIFIED] H010's universal equal-full-information-cost extension fails on the
two hidden states {-1,1}. The informed actions -x each attain zero cost; one
blind action cannot attain zero cost in both states. Under-reporting a belief
as {-1} when the true state is 1 permits action 1 and exits the safe set. These
counterexamples remain in control.json; the original H010 is not weakened.

[OBSERVED] Disposition: known one-step capability reproduced, novelty not
established. H007 is not refuted merely because its stronger sibling is false.

## H014 — certify counterfactual schedule elimination

[ESTABLISHED BY PRIOR WORK] DPOR and context-sensitive independence already
avoid redundant schedules with explicit soundness conditions. Existing GenMC
and published proof artifacts are much stronger than this finite demonstration.
The expense of proving independence must be charged; exhaustive checking of
all states is not a free optimization.

[EXPERIMENTALLY DEMONSTRATED] In the three-action fixture, a and b commute at
the initial state, but not after c. The complete six-order baseline sees two
terminal outcomes. An unsound sample-based ordering retains only one and loses
(1,1). The all-reachable-state independence check rejects that swap. A disjoint-
coordinate positive control has the same terminal result in all six orders.

[FALSIFIED] H015/H013 cannot extrapolate an observed initial commutation to
all contexts. A conditional local rewrite does not become a global program
equivalence certificate. The finite model says nothing about real Linux weak
memory unless a separate memory-model proof is supplied.

[OBSERVED] Disposition: standard proof obligation confirmed; no novel reduction
algorithm, complexity improvement or unavailable baseline capability established.

## Continued search outside these fields

[EXPERIMENTALLY DEMONSTRATED] The separate P1 continuation exhaustively checks
65,536 fair-coin paths and records a bounded-control saturation trajectory.
These explore statistics and biological/control-inspired allocation after the
first three directions fail the novelty gate. They are retained known-result
replications/counterexamples, not renamed discoveries. See proof-or-falsification.md.


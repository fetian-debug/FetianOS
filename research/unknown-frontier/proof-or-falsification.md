# Proof, evidence and falsification ledger

[FORMALLY PROVEN] A written constructive derivation establishes equivalence of
the five certificate inequalities and real feasibility for the one fixed matrix.
It also establishes equality of the proposed and conventional projected
capabilities. The result is a rederivation of existing linear-feasibility ideas,
not a new theorem, not an arbitrary-matrix result, and not a proof of the
compiled Rust implementation. No Lean/Coq/SMT proof artifact is supplied.

[EXPERIMENTALLY DEMONSTRATED] Two real Linux executions, seeds 2090 and 2091,
each have 10,733 base and 2,000 metamorphic evaluations, zero classifier/oracle
mismatches, 729 separate grid-oracle checks, eight exposed mutation controls,
and seven malformed/domain-violating inputs rejected by each Rust program.
All raw inputs/results remain in the seed directories. These are bounded tests,
not universal empirical proof or hardware validation.

[FALSIFIED] H005's proposed capability separation fails: the strongest relevant
conventional baseline also uses zero online feasibility solves and exactly
classifies the same admissible domain. Beating a repeated general-purpose
solver would not rescue novelty. The functional part of H005 is not false.

[FALSIFIED] H003's arbitrary-matrix cached-rejection extension has a retained
false-rejection counterexample in certificate-change-supplement.json. The
original P0 mutation separately shows false acceptance when a previously
learned classifier is used after a matrix change. The distinction matters:
false acceptance alone would not disprove soundness of a rejection certificate.
Neither is a counterexample within H005's fixed-matrix assumptions.

[FORMALLY PROVEN] Universal instantiation proves the one-step H007 safety rule
under a complete belief set and accurate model. The two-state indistinguishability
argument refutes H010's full-information optimality extension. The explicit
three-action calculation refutes H013/H015's context extrapolation. These are
restricted written arguments; finite tables independently exercise the fixtures.

[OBSERVED] The P1 follow-on crosses into statistics and control after the first
three candidates failed the novelty gate. No original hypothesis or P0 outcome
rule was changed to obtain a success. See follow-on-protocol.md.

[EXPERIMENTALLY DEMONSTRATED] Exhaustive enumeration of every length-16 fair-
coin path gives 5,368/65,536=671/8,192 (about 8.19%) false rejections when
repeatedly using a fixed-time level-5% exact binomial test. At the final time
alone the rate is 1,394/65,536 (about 2.13%), at most 5%. The elementary
alpha-spending baseline rejects 16/65,536=1/4,096 (about 0.0244%). It is much
more conservative; this is not free power or a new statistical method. The
all-ones alternative is detected at time 13 as a positive control.

[FORMALLY PROVEN] For each fixed time, the exact p-value test has rejection
probability at most its allocated alpha_t under the independent fair-coin null.
A union bound and sum_t 1/[t(t+1)]<=1 give overall false-alarm probability <=5%
for the alpha-spending policy. Optional stopping of fixed-time tests lacks that
same justification. This reproduces known sequential-testing logic; it is not
a proof under arbitrary dependent or adversarial nonstationary data.

[FALSIFIED] H085's universal perfect-adaptation claim fails when disturbance
is 2 and the actuator magnitude is at most 1: x_next=x+2-u>=x+1. The complete
32-step trajectory is retained. This physical-model constraint defeats every
controller in that fixture, not only the chosen finite integrator. It does not
refute narrower H084 or a biological antithetic network theorem.

[UNVERIFIED] Most of the 100 candidate claims have not undergone independent
formal review. Several located-implementation cells and one located-patent cell in
the shortlist are unresolved; exact counts are generated in the review JSON.
No exhaustive patent/literature review, independent external replication,
physical control experiment, new complexity bound, or new computing capability
has been established. Read the review's explicit unresolved entries rather than
inferring that no relevant work exists.


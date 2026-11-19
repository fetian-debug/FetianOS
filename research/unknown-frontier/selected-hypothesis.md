# Selected hypothesis: no novelty survivor

[OBSERVED] No candidate currently survives the novelty gate. No new production
module is selected for integration. This file records the **one primary
candidate subjected to experimental falsification**, H005, without calling it
a surviving invention. Its original CSV statement remains unchanged:

> For A consisting of axis and diagonal bounds in R^2, five stored dependency certificates exactly classify every bounded integer b without solving again; test whether this exceeds an equivalent projected baseline.

[HYPOTHESIS] Functional claim C1: for the exact fixed matrix in
`mathematical-model.md`, both real feasibility and the cached-certificate
classifier agree for every admitted integer right-hand side. Distinct claim C2:
this constitutes a capability not available from an equivalent conventional
projected feasibility baseline. C2 is a requirement for novelty, not a fact.

Assumptions: one unchanging six-row matrix, two real variables, integer bounds
in [-1,000,000,1,000,000], exact integer arithmetic, trusted local programs,
Linux pipes and no hidden sensor/oracle information. Coefficients, input-domain
checks, certificate validation and preprocessing are included. No floating-point,
integer-program feasibility, unknown matrix, or changing-coefficient claim.

Smallest mechanism: five nonnegative row dependencies, checked once; subsequent
requests evaluate five integer dot products. No LP solve is needed per request.
The strongest equivalent conventional baseline uses interval intersection and
an algebraically precomputed projection. It also needs zero LP solves.

Proof obligation: soundness and completeness for this matrix, an independent
exact geometry oracle, and a genuine separation from that strong baseline.
Failure conditions: any admitted input disagreement refutes C1; an equal-
assumption conventional construction with the same capability refutes C2.
No wall-clock advantage against vertex enumeration establishes C2.

[ESTABLISHED BY PRIOR WORK] Farkas dual certificates, Benders feasibility cuts
and variable elimination already expose the relevant reuse mechanism. The
experiment is retained to test this negative novelty assessment independently,
not to rename that prior work. Final dispositions appear in the final report.

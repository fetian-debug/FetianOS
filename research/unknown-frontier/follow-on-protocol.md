# Follow-on protocol P1 — another-field continuation

[OBSERVED] After the primary candidates failed the novelty gate, continue with
statistics and bounded control rather than reinterpret their results as a win.
This is a separate protocol; P0 and the 100 original hypotheses stay unchanged.

1. H087: enumerate every length-16 fair-coin sequence (65,536 equally likely
   paths). At every prefix compute the exact two-sided binomial tail p-value.
   Compare stopping at the first p<=0.05 with a conventional anytime policy
   using alpha_t=0.05/[t(t+1)]. Record every path and stopping time, final-time
   rejection counts, cumulative rejection counts and exact probabilities.
   Validate each p-value independently by enumerating the complete binomial
   probability mass and verify each fixed-time test's size is <=0.05.
2. H086/H089: the anytime baseline is an elementary alpha-spending rule, not an
   implementation or benchmark of the linked confseq project. Its probability
   bound follows a union bound under the independent fair-coin null. Empty or
   very conservative acceptance regions are not presented as free statistical
   power. Include the all-ones alternative as a power positive control.
3. H085: simulate 32 steps of x'=x+d-u with integral-state saturation and
   |u|<=1, d=2, target x=0. Record every state. The physical bound x'>=x+1
   means no controller can maintain zero error in this fixture. Also use d=0,
   initial x=0 as a positive equilibrium control. Do not label this a stochastic
   antithetic molecular simulation or a falsification of H084's narrower bound.
4. Preserve raw results. These are replications/counterexamples to known
   mechanisms, not a new confidence sequence or adaptation theorem. No runtime
   integration follows. Store P1's hash before execution and never overwrite
   an output directory.

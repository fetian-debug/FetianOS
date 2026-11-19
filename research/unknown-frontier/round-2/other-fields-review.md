# Other-field prior-art and adversarial review

[OBSERVED] H101–H112 remain in their separately frozen catalogue. H113 was
registered later in family-protocol.md before its P3 experiment. Thirteen
additional hypotheses were investigated, not thirteen proven inventions or
thirteen completely unrelated fields. Search scope is bounded and documented;
no global novelty, patentability or first-ever claim follows from it.

| ID | Verdict and exact scope | Closest located primary work |
|---|---|---|
| H101 | PRIOR REPORTED. Genuine catalytic time/space advantages are already claimed under explicit output models. We did not independently reproduce those asymptotic algorithms. | [2026 catalytic algorithms preprint](https://arxiv.org/abs/2610.24377) |
| H102 | NEEDS FORMALIZATION. Expected-error models depend on what randomness/tape distribution and error rate are allowed. Recent characterizations already study this family. | [Robust catalytic computing](https://arxiv.org/abs/2605.09648) |
| H103 | FALSIFIED for a standard end-only single-bit decoder: propagation can create multi-bit logical errors. P2 retains inside-region and full-error counterexamples. | [Fault propagation and reliable circuits](https://preskill.caltech.edu/pubs/preskill-2006-threshold.pdf) |
| H104 | FALSIFIED. Seven possible effective errors at n=5 still require four metadata bits; error count alone is insufficient. | [Zero-error side-information coding](https://ieeexplore.ieee.org/document/1228155/) |
| H105 | FUNCTIONALLY DEMONSTRATED; capability gap FAILED. Optima 4 and 3 match a generic same-model baseline exactly. | [Zero-error side-information coding](https://ieeexplore.ieee.org/document/1228155/) |
| H106 | EXCLUDED in the stated stable finite-state population model by semilinearity. An unbounded simulation cannot prove this theorem; we rely on the existing result. | [Semilinear predicates theorem](https://www.cs.yale.edu/homes/aspnes/papers/semilinear-abstract.html) |
| H107 | FALSIFIED. All 4,096 deterministic parity-respecting classical strategies achieve at most 8/9. Shared randomness is a convex mixture. Quantum resources are a different model and were not implemented. | [Quantum pseudo-telepathy paper](https://crypto.cs.mcgill.ca/~crepeau/COMP647/2007/TOPIC08/BBT04.pdf) |
| H108 | FALSIFIED. Identical observed/interventional marginals admit different individual-response couplings. | [Probabilities of causation](https://ftp.cs.ucla.edu/pub/stat_ser/r271-A.pdf) |
| H109 | FALSIFIED in a finite reversible-state model: eight initial states cannot map injectively into four while preserving the catalyst and exporting no distinction. No energy measurement is claimed. | [Logical reversibility](https://www.cs.princeton.edu/courses/archive/fall04/cos576/papers/bennett73.html) |
| H110 | FALSIFIED under the stated black-box observation restriction. Constant-zero and secret-leaking programs agree on the observed secret input yet differ in noninterference. | [Hyperproperties](https://journals.sagepub.com/doi/pdf/10.3233/JCS-2009-0393) |
| H111 | FALSIFIED by exact joint-stationarity calculations. Parallel scheduling needs valid conditional independence or another correction, not arbitrary simultaneous updates. | [Parallel Gibbs sampling](https://proceedings.mlr.press/v15/gonzalez11a.html) |
| H112 | KNOWN QUERY PACKING; information-cost claim UNRESOLVED as phrased. Twenty-seven integer rows fit a five-bit observation; encoding does not remove their information content. | [Kronecker substitution implementation](https://flintlib.org/doc/algorithms/polynomials/kronecker.html) |
| H113 | RESTRICTED WRITTEN LINEAR BOUND plus tested construction. Exact statement priority UNVERIFIED; no new capability over generic coding established. Larger-n nonlinear bounds remain open in this investigation. | [Related inversion-code work](https://www.vkit.ru/index.php/archive-rus/1437-034-040) and zero-error coding |

[FORMALLY PROVEN — conditional use of prior theorem] Unary semilinear sets are
ultimately periodic; prime population sizes are not. If primes were periodic
with period p beyond N, choose a prime q>N and q>p. The accepted number q+qp
would also have to be prime, but equals q(1+p). Thus H106 cannot hold under
the standard model's semilinearity characterization. Changing fairness,
agent memory or adding identifiers changes the assumptions.

[OBSERVED] Searches also found folded-cube total/incidence colouring papers.
Those concern different colourings and are not used as proofs of the precise
confusability-square bounds here. A near title is not exact anticipation.
Conversely, not locating this exact tiny example does not make its capability
new: the general coding baseline already implements it. That distinction is
why H105 does not pass the requested capability gate.

[UNVERIFIED] This screen does not settle every exact priority claim or close
all implementation/patent cells left open previously. External projects were
not benchmarked. No person was contacted, no physical system was modified,
and no result is represented as independent peer review.

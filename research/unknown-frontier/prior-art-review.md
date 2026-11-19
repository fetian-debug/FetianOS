# Adversarial prior-art review

[OBSERVED] Twenty shortlisted claims were screened across distinct fields. The search ledger records 65 web-index queries and primary-page opens. Searches included alternative names, GitHub, patents, author papers, ACM/IEEE/USENIX-indexed work, theses, arXiv and queries mentioning Google Scholar and Semantic Scholar. This does **not** mean every portal was directly accessible, every venue was exhaustively searched, or all 20 closest implementations were found. Unresolved implementation/patent cells remain UNVERIFIED. Implementation links are documentation/source pointers; external projects were not installed or benchmarked.

[UNVERIFIED] A patent hit is a located technical disclosure, not a determination of anticipation, claim coverage, validity, ownership or freedom to operate. No legal conclusions or date-priority claims are made. Negative search results confer no novelty evidence.

## Ranking and scope

Ordinal 0–5 scores use significance / novelty evidence / testability / formalizability / feasibility / measured baseline capability gap / reproducibility. After screening, novelty evidence and demonstrated gap are zero for every candidate. H005, H007 and H014 score 24/35 through testability/formal scope; other shortlisted directions score 15/35. These are purposive judgments, not calibrated estimates that a breakthrough exists. The shortlist was chosen for diverse, bounded falsification rather than because universal overclaims sound impressive.

[OBSERVED] The remaining 80 catalogue entries were not individually subjected to this depth of review and are not classified as disproven or non-novel. Even the 20-case screen does not exhaust all possible refinements. Only the specifically scoped top-three gap assessments are investigated with artifacts.

## H005 — negative feasibility information

[HYPOTHESIS] For A consisting of axis and diagonal bounds in R^2, five stored dependency certificates exactly classify every bounded integer b without solving again; test whether this exceeds an equivalent projected baseline.

Aliases searched: Farkas; Benders feasibility cut; dual ray; projection; parametric LP.

Primary theory/paper: [located work](https://benders.dev/latest/api/cuts.html).

Located implementation/source: [primary project](https://scipopt.org/doc-9.2.4/html/benderscut__feas_8h_source.php).

Located patent disclosure: [document](https://patents.google.com/patent/US20030036937A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Certificate reuse is explicit prior work. Exact interval projection has the same fixed-matrix capability with zero online LP solves. No capability gap survives.

Assumptions to preserve: fixed known rational A; changing integer b; exact arithmetic.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H007 — observation-action coupling

[HYPOTHESIS] A controller updating the complete reachable belief set preserves one-step safety without measuring on every step.

Aliases searched: belief support; information state; robust safety; active sensing; shielding.

Primary theory/paper: [located work](https://arxiv.org/abs/2204.00755).

Located implementation/source: [primary project](https://github.com/h2r/pomdp-py).

Located patent disclosure: [document](https://patents.google.com/patent/US11921506B2/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Partial-observation control already reasons from belief/support. The toy intersection is a one-step robust constraint, not a general POMDP solver or a new controller. Full-information optimality is a separate false extension.

Assumptions to preserve: finite exact belief set B; known dynamics; trusted observation.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H014 — useful counterfactual schedules

[HYPOTHESIS] Pairwise independence checking over every finite reachable state can certify reduction without application annotations.

Aliases searched: POR; DPOR; context-sensitive independence; commutativity; Mazurkiewicz trace.

Primary theory/paper: [located work](https://researchmgt.monash.edu/ws/portalfiles/portal/257767040/71313718_oa.pdf).

Located implementation/source: [primary project](https://plv.mpi-sws.org/genmc/).

Located patent disclosure: [document](https://patents.google.com/patent/US20180046523A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Checking independence to reduce schedules is existing POR. Sound context-sensitive algorithms already exist. A single observed commutation cannot justify arbitrary contexts; our finite checker is not a competing DPOR implementation.

Assumptions to preserve: finite deterministic transition system; declared observable state.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H019 — representation-changing query reuse

[HYPOTHESIS] A homomorphic representation map commutes with additive deltas when its group-homomorphism law is verified.

Aliases searched: delta query; change propagation; differential dataflow; homomorphic update.

Primary theory/paper: [located work](https://arxiv.org/abs/2203.16684).

Located implementation/source: [primary project](https://github.com/feldera/feldera).

Located patent disclosure: [document](https://patents.google.com/patent/US7680767B2).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Incrementalization and representation maps overlap existing algebraic view maintenance. A specific cheaper verified transport between new representations remains UNVERIFIED; no separation from DBSP is demonstrated.

Assumptions to preserve: explicit representation map; bag semantics; insertions/deletions.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H025 — precision as a controlled resource

[HYPOTHESIS] A runtime can select the lowest arithmetic precision meeting a per-request certified backward-error target, accounting for verification work.

Aliases searched: iterative refinement; residual certification; adaptive mixed precision; backward error.

Primary theory/paper: [located work](https://www.netlib.org/utk/people/JackDongarra/PAPERS/mixed-rs-2020.pdf).

Located implementation/source: [primary project](https://icl.utk.edu/magma/).

Located patent disclosure: [document](https://patents.google.com/patent/US9779061B2/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Low-precision work plus residual/refinement is established with conditioning assumptions. The exact lowest-precision selection and total verification-cost benefit remain UNVERIFIED; runtime placement alone is not novelty.

Assumptions to preserve: finite non-NaN inputs; explicit conditioning and rounding model.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H029 — negative membership information

[HYPOTHESIS] An absent-key certificate can be reused until an insertion invalidates the certified interval.

Aliases searched: negative caching; range filter; absence certificate; interval invalidation.

Primary theory/paper: [located work](https://www.cs.cmu.edu/~huanche1/publications/surf_paper.pdf).

Located implementation/source: [primary project](https://github.com/efficient/SuRF).

Located patent disclosure: [document](https://patents.google.com/patent/US20180302433A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Prior work already filters negative range/point lookups and caches negative answers. SuRF is approximate, so it does not establish an exact mutable-certificate claim. Exact invalidation design and separation from ordinary ordered indexes remain UNVERIFIED.

Assumptions to preserve: explicit universe; no hidden backing-store reads.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H032 — decisions before outcomes

[HYPOTHESIS] A scheduler can retain a bounded competitive ratio when prediction error is arbitrarily large by falling back to an online policy.

Aliases searched: learning augmented scheduling; consistency; robustness; untrusted advice.

Primary theory/paper: [located work](https://ijcai.org/proceedings/2022/636).

Implementation: UNVERIFIED: closest implementation not identified in this bounded screen.

Located patent disclosure: [document](https://patents.google.com/patent/US20200264928A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Consistency and robustness to bad scheduling predictions are explicit existing goals/results. A different objective or error model needs a new theorem, not a renamed scheduler. No such separation demonstrated.

Assumptions to preserve: nonclairvoyant arrivals; explicit advice bits and objective.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H039 — computation from absent observations

[HYPOTHESIS] A verified common prefix can reduce repeated parity work by its known prefix length.

Aliases searched: query complexity; exact memoization; prefix reuse; input identity.

Primary theory/paper: [located work](https://cs.uwaterloo.ca/~eblais/cs860/w25/hierarchy).

Implementation: UNVERIFIED: exact-prefix-reuse implementation not separately inspected.

Patent/disclosure: UNVERIFIED: parity/query-complexity patent query found no close exact disclosure.

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Known prefix information can eliminate repeated work; unread independent suffix bits still carry information. An implementation must charge identity validation. No new query-complexity result demonstrated.

Assumptions to preserve: arbitrary independent bits; exact deterministic answer.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H045 — coded partial work

[HYPOTHESIS] A runtime can switch decoding bases as fragments arrive without repeating completed linear work; compare against existing coded-computing schedulers.

Aliases searched: coded computation; stragglers; polynomial code; rank-aware decoding.

Primary theory/paper: [located work](https://proceedings.neurips.cc/paper_files/paper/2017/hash/e6c2dc3dee4a51dcec3a876aa2339a78-Abstract.html).

Implementation: UNVERIFIED: located paper, no closest author implementation validated.

Located patent disclosure: [document](https://patents.google.com/patent/US20180365099A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Coding and decoding collected fragments already tolerate missing workers under redundancy assumptions. A new adaptive policy or bound is UNVERIFIED; linear-algebra reconstruction is not novel.

Assumptions to preserve: linear computation; explicit redundancy and worker failure bound.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H049 — verification during computation

[HYPOTHESIS] Accumulating independent row checks can expose a corruption before computing the complete product.

Aliases searched: Freivalds; online verification; randomized projection; adaptive challenges.

Primary theory/paper: [located work](https://www.sciencedirect.com/science/article/pii/002001909390183A).

Located implementation/source: [primary project](https://github.com/williamfiset/Algorithms/blob/master/src/main/java/com/williamfiset/algorithms/linearalgebra/FreivaldsAlgorithm.java).

Located patent disclosure: [document](https://patents.google.com/patent/WO2024226627A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Randomized product verification is established. Interleaving checks is not a new soundness theorem; challenge exposure and adversary timing matter. No adaptive-public-reuse guarantee established.

Assumptions to preserve: correct verifier; fresh private randomness; adversary timing explicit.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H054 — reclamation without global observation

[HYPOTHESIS] A bounded reader lifetime permits time-based reclamation if the clock bound is trusted.

Aliases searched: RCU; hazard pointer; grace period; bounded reader lifetime.

Primary theory/paper: [located work](https://docs.kernel.org/6.18/RCU/whatisRCU.html).

Located implementation/source: [primary project](https://github.com/urcu/userspace-rcu).

Located patent disclosure: [document](https://patents.google.com/patent/US9785548B2/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Known reclamation schemes wait for or establish reader safety information. An external hard reader-lifetime bound changes assumptions. Novel timing/reclamation tradeoffs remain UNVERIFIED; no stalled-reader impossibility evaded.

Assumptions to preserve: shared memory; reader/writer execution model specified.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H059 — privacy of resource decisions

[HYPOTHESIS] Privacy loss can be tracked under adaptive composition with an explicit accountant.

Aliases searched: privacy filter; odometer; adaptive composition; privacy accountant.

Primary theory/paper: [located work](https://arxiv.org/abs/1605.08294).

Implementation: UNVERIFIED: closest fully adaptive filter implementation not inspected.

Located patent disclosure: [document](https://patents.google.com/patent/US20220327227A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Adaptive privacy budgeting is prior work, including stopping filters. A scheduler-specific accountant must prove observer/adjacency guarantees; that exact construction remains UNVERIFIED.

Assumptions to preserve: explicit observer and adjacency; budget accounting.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H064 — coordination from monotonic information

[HYPOTHESIS] An escrow allocation can preserve a global bound using preallocated local rights.

Aliases searched: escrow; bounded counter; invariant confluence; coordination avoidance.

Primary theory/paper: [located work](https://arxiv.org/abs/1503.09052).

Located implementation/source: [primary project](https://docs.rs/bcounter/latest/src/bcounter/lib.rs.html).

Located patent disclosure: [document](https://patents.google.com/patent/US11630838B1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Escrow rights and bounded-counter replicated data types explicitly preserve numeric invariants with local operations. Bounds and rights-transfer assumptions cannot be omitted. No new capability gap identified.

Assumptions to preserve: asynchronous delivery; no Byzantine participants; monotone outputs.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H069 — storage entropy and prediction

[HYPOTHESIS] An adaptive code can approach a stationary source entropy rate under its stated source model.

Aliases searched: source coding; universal coding; stationary source; adaptive entropy coding.

Primary theory/paper: [located work](https://www.cl.cam.ac.uk/teaching/2021/InfoTheory/InfoTheoryNotes2020.pdf).

Implementation: UNVERIFIED: no closest implementation for the exact source model validated.

Located patent disclosure: [document](https://patents.google.com/patent/US10128868B1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Source-model-dependent compression is established. An unrestricted every-input improvement is excluded by injectivity/counting. A new finite-size redundancy bound for a specific source remains UNVERIFIED.

Assumptions to preserve: lossless decoding; account for model and metadata.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H072 — compiler-runtime boundary

[HYPOTHESIS] A proof-producing rewrite can transport an optimization across two typed intermediate representations.

Aliases searched: egraph; equality saturation; rewrite certificate; translation validation.

Primary theory/paper: [located work](https://arxiv.org/abs/2004.03082).

Located implementation/source: [primary project](https://isa-afp.org/entries/Equality_Saturation_Checker.html).

Located patent disclosure: [document](https://patents.google.com/patent/US20120159459A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Existing equality saturation retains equivalent forms and proof-checking work checks rewrite/extraction certificates. Transport across a particular typed pair may be engineering; a new theorem or capability gap is UNVERIFIED.

Assumptions to preserve: sound rewrite rules; explicit cost model; observable semantics.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H077 — energy and information erasure

[HYPOTHESIS] Uncomputation can erase temporary logical garbage by reversing a computation with a copied output.

Aliases searched: reversible simulation; Bennett uncomputation; garbage; pebble game.

Primary theory/paper: [located work](https://www.cs.princeton.edu/courses/archive/fall04/cos576/papers/bennett73.html).

Implementation: UNVERIFIED: no closest classical reversible implementation evaluated.

Located patent disclosure: [document](https://patents.google.com/patent/EP3304363A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Retaining history and uncomputing are longstanding constructions. Logical reversibility does not alone demonstrate physical energy savings. No hardware or energy measurement performed.

Assumptions to preserve: physical device model; include I/O and garbage cleanup.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H084 — biological adaptation

[HYPOTHESIS] A finite-state approximation of an integral controller has a measurable steady-state error bound.

Aliases searched: integral control; antithetic feedback; robust adaptation; finite-state approximation.

Primary theory/paper: [located work](https://arxiv.org/abs/1410.6064).

Implementation: UNVERIFIED: no closest finite-state controller implementation inspected.

Located patent disclosure: [document](https://patents.google.com/patent/WO2024023166A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Biological feedback adaptation is established under explicit stochastic/stability conditions. A finite-state approximation needs its own error/stability bound; the catalogue does not establish one. Software transfer is not itself novelty.

Assumptions to preserve: known actuator bounds; noise model; stability region.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H089 — uncertainty with optional stopping

[HYPOTHESIS] A nonnegative test martingale can support an anytime-valid threshold decision.

Aliases searched: confidence sequence; e-process; Ville inequality; anytime valid stopping.

Primary theory/paper: [located work](https://arxiv.org/abs/1810.08240).

Located implementation/source: [primary project](https://github.com/gostevehoward/confseq).

Located patent disclosure: [document](https://patents.google.com/patent/US20240281836A1/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Anytime-valid bounds and stopping decisions are established. Applying them to resource sampling requires justified stochastic assumptions. An arbitrary-dependence guarantee is not supplied by optional stopping alone.

Assumptions to preserve: exchangeability or martingale assumptions stated explicitly.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H094 — human intent and reversible interfaces

[HYPOTHESIS] An effect type can reject commands lacking a declared compensation before execution.

Aliases searched: compensation; effect types; inverse operation; semantic undo.

Primary theory/paper: [located work](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction).

Implementation: UNVERIFIED: no exact compensation effect-type implementation located.

Located patent disclosure: [document](https://patents.google.com/patent/US20090094291).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Compensation and declared undo operations have existing disclosures. An effect annotation cannot restore information or control external observers. A sound new typed calculus is UNVERIFIED.

Assumptions to preserve: explicit environment and external-effect reversibility.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.

## H099 — fault prediction versus evidence

[HYPOTHESIS] An explicit predictive model can trade false alarms against missed failures on held-out labeled traces.

Aliases searched: ECC telemetry; predictive failure; correctable error; calibration.

Primary theory/paper: [located work](https://research.google/pubs/dram-errors-in-the-wild-a-large-scale-field-study/).

Located implementation/source: [primary project](https://docs.kernel.org/driver-api/edac.html).

Located patent disclosure: [document](https://patents.google.com/patent/US10558521B2/en).

[ESTABLISHED BY PRIOR WORK / UNVERIFIED GAP] Statistical failure prediction and error telemetry are established. No held-out device traces or physical fault experiment were collected here. Universal fault prediction without prior information remains unsupported.

Assumptions to preserve: explicit fault model; causal sensors only.

Verdict: novelty NOT ESTABLISHED. Do not infer absence of a capability from this bounded search.


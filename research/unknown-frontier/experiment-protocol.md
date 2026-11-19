# Experiment protocol — frozen before execution

Primary candidate: H005. Detailed companion candidates: H007 and H014.
Strong extensions under attack: H010 and H015. Claims are in the frozen CSV.

1. Compile two independent dependency-free Rust command-line programs with
   optimization: certificate dot products versus interval projection. Validate
   all certificate weights/nonnegative nullspace equations once at startup.
2. Compare both programs to an independent Python exact-rational vertex oracle
   on all 3^6=729 b in {-1,0,1}^6 and 10,000 seeded random b in [-8,8]^6.
   Master seed 2090. Include explicit domain-edge and malformed-line fixtures.
3. Independently validate the geometry oracle against exhaustive integer-grid
   existence on the 729 small cases and against a constructed witness on a
   feasible example. No floating-point feasibility tolerance is allowed.
4. Use 1,000 affine translations of constraints and positive scale transforms.
   Their truth must be invariant, and compare with the geometry oracle again.
5. Mutation controls: drop each of five cuts, reject equality by changing >= to
   >, use a negative invalid certificate, and extrapolate a certificate to a
   changed matrix. Each defect must be exposed by a retained witness. A test
   harness that fails to expose these defects does not establish correctness.
6. Enumerate all seven nonempty beliefs over {-1,0,1} and all three actions.
   Compare the shared-safe-action mechanism with an independently enumerated
   set of state/action safety pairs. Retain the full-information optimal-cost
   counterexample and an under-approximated-belief unsafe action.
7. Enumerate all six orders of three finite actions. Record complete outcomes,
   initial commutativity and context-dependent counterexample. Compare an
   unsound sample-based reduction with the complete schedule baseline.
8. Save every right-hand side, expected/actual result, source/binary/protocol
   hashes, environment, seed, oracle checks and mutants. A second seed 2091 is
   an explicit independent replication, not replacement of failed seed 2090.
9. Evaluate zero-online-solve capability against the strong projected baseline.
   Do not use a slower enumeration baseline to manufacture novelty. No timing
   or performance superiority claim is needed for this capability experiment.

Stop: any functional mismatch fails the experiment. A retained expected
counterexample refutes its tagged strong claim rather than failing the harness.
Known equivalence to the strong baseline fails the novelty gate. No runtime
integration follows a failed or unverified novelty gate. Results never rewrite
this protocol or the original claims; corrections require a separate revision.

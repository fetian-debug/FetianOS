# Round 2 protocol — original claims stay frozen

[OBSERVED] Parent source: 4c8541d658e31068856bfc46ee88917b5c9beddb.
Do not edit the original 100 hypotheses, earlier evidence, FCA, runtime services,
ISO configuration or published releases. All follow-on work stays in round-2.

## Required gates

[HYPOTHESIS] A discovery needs an exact observable capability and an equal-
assumption separation from the strongest relevant conventional baseline. A new
name, application domain, restricted weak comparator, extra hidden memory,
precision, trusted information or physical resource does not establish it.
A baseline is permitted the same input, preprocessing and static code tables.
No benchmark speedup alone establishes previously unavailable computation.

[OBSERVED] Review each of the 80 original IDs excluded from the earlier
shortlist. Preserve its exact text/hash. Mark individually: known conditional
mechanism, falsified in an explicit model, needs formalization, or unverified
physical/empirical claim. Do not treat an ambiguous claim as disproven. Record
primary sources, assumptions, strongest comparator and an evidence hook.
A bounded literature review is not an exhaustive priority/patent assessment.

## Other-field hypotheses H101–H112

Create a separate frozen catalogue. Focus detailed tests on H104/H105 (protected
metadata for reversible-memory faults), H108 (causal identification) and H111
(stochastic computing). Screen catalytic complexity, finite-state population
protocols, nonlocal games, thermodynamic catalysis, hyperproperty monitoring and
integer query packing as well. External mathematical results remain attributed.

## P2-A: exact noisy-memory channel, not an OS recovery mechanism

Word x has n arbitrary bits. Trusted metadata f(x) is computed before noise.
A protected CNOT-star forward/inverse circuit returns the word to x in the
absence of faults. Permit at most one bit flip at either of two declared windows:
before the forward star, or between forward and inverse. No faults are allowed
inside gates, in metadata, the encoder or the decoder. Derive error masks by
actual gate propagation and independently by a GF(2) matrix calculation.

The resulting error set is E_n={0, unit_1,...,unit_n, all_ones}. The decoder gets
only the final word and retained metadata, never the original x or fault site.
The experiment harness may retain x as an external correctness oracle. Protected
metadata bits are the resource measured; control scratch, static code/tables
and addresses are NOT claimed to fit in that budget. This is NOT catalytic
logspace, hardware fault tolerance or a clean-workspace complexity separation.

H104 predicts ceil(log2 |E_n|) protected bits always suffice; test n=5 and n=6.
H105 predicts an exact nonmonotonic bound: n=5 needs 4 bits, n=6 needs 3 bits.
Compare a Rust syndrome decoder, an independent generic confusability decoder,
a weak end-only single-bit decoder as a negative control, and raw snapshots.
Exhaust all initial words, allowed windows and fault bits, including no fault.
Derive lower bounds for ANY encoder, not just linear parity maps. Use the
full indistinguishability graph, not only the cardinality of E. Test all 2- and
3-row linear checks for minimality where tractable, but do not substitute that
for a nonlinear lower bound. Charge the static decoding table separately.

Adversarial controls: omit all-ones error; one fewer metadata bit; corrupt
metadata; allow two errors; inject a fault inside a nominally protected gate
region. Retain counterexamples; do not expand a failed model's guarantee.
Run randomized circuits/input words under a second explicitly declared model
only to test propagation/oracle consistency, never to claim universal correction.

## P2-B: causal counterfactual identification

Two SCMs use independent fair X,U. Model A: Y=U. Model B: Y=X xor U.
Enumerate all assignments and interventions. Compare observable and
interventional distributions and the response event Y(0)!=Y(1). No estimator
that sees only the identical distributions may read the hidden model label.
This is an identification example, not a causal-inference implementation win.

## P2-C: exact two-spin sampling

Compare simultaneous independent conditional updates with a sequential Gibbs
sweep. Matching a neighbor has probability 3/4. Use rational transition
matrices, all four states, exact stationarity residuals, and an independent
trajectory enumerator. The target law is (3/8,1/8,1/8,3/8). Test the claim that
arbitrary synchronous updates preserve that law, without mixing-time or
hardware-speed assertions.

## P2-D: original-80 adversarial checks

Exercise information collisions, a residual/forward-error counterexample,
nonclairvoyant two-job policies, public-projection forgery, memory-reader
indistinguishability, exact-output privacy, asynchronous absence, replicated
uniqueness, compression counting, finite IEEE reassociation, inverse maps,
actuator saturation, conformal distribution shift, external observation/undo,
parity and Hamming distance-three coding. Mathematical impossibility claims
need written arguments; tests cover finite witnesses, not arbitrary programs.

## Evidence rules

Save plan/source/compiler hashes before each experiment, every tested case and
mutation/counterexample, and independent oracle outputs. Original statements
and this protocol are never weakened after results. Unexpected discrepancies
fail the command and remain in a separate failure record. A successful
functional result is not a passed novelty gate. Only integrate after genuine
capability separation and independent review; no integration occurs by default.

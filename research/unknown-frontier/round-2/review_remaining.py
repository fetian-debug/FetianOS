"""Individual annotations for all previously unreviewed original IDs; no edits to claims."""
import csv,hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# K: established conditional mechanism; F: explicit countermodel; Q: underspecified; U: unverified physical claim.
DATA={
1:('K','An infeasible request yields a reusable halfspace when the matrix is unchanged; this is the feasibility-cut mechanism.','dual'),
2:('K','The nonnegative nullspace identity proves rejection by adding inequalities; arithmetic/domain assumptions remain necessary.','dual'),
3:('F','A changed row makes a previously rejected b feasible; the old multiplier no longer annihilates the matrix.','matrix-change'),
4:('K','For a fixed finite matrix, complete extreme rays of the nonnegative dual cone describe feasible right-hand sides; enumeration can be expensive.','dual'),
6:('K','A shared safe action permits omitting a one-step observation if the true state is inside the complete belief set.','belief'),
8:('F','For hidden states -1 and 1, the informed zero-cost actions differ; a blind shared safe action cannot match both.','blind-cost'),
9:('Q','A nonempty intersection suffices for blind one-step safety. Cardinality zero does not say whether sensing can rescue feasibility; necessary/predicts needs a definition.','belief-empty'),
10:('F','The same two-state indistinguishability defeats a universal full-information optimality guarantee with fewer observations.','blind-cost'),
11:('K','For enabled universally commuting transitions, adjacent swaps preserve terminal state; intermediate observations require separate treatment.','commute'),
12:('K','A finite acyclic three-action reduction with checked independence and enabling preservation is standard partial-order reasoning.','commute'),
13:('F','Actions commuting initially need not commute after a third action changes the context.','context'),
15:('F','Ordering a before b from the initial sample loses a terminal outcome in the retained three-action model.','context'),
16:('K','An additive aggregate consumes explicit signed updates across a lossless row/column map; unchanged input need not be fully rescanned.','delta'),
17:('K','Bag multiplicities support exact grouped-count deletions when the update identifies the group and deleted amount.','delta'),
18:('F','Two inputs colliding in a lossy summary differ on a singleton selection query; identical summary cannot answer both exactly.','information'),
20:('K','Incremental relational implementations already support joins and deletions; this does not imply every update costs only its delta size.','delta'),
21:('K','Mixed-precision refinement reaches a backward-error target only under its solver, rounding and conditioning requirements.','residual'),
22:('K','A verified residual can stop a solved diagonal fixture immediately instead of performing a predetermined extra iteration.','residual'),
23:('F','For diag(epsilon,1), residual epsilon coexists with unit forward error; a condition-number bound is missing.','residual'),
24:('K','Condition/error bounds can reject a precision choice. Computing trustworthy bounds and overflow checks is part of the work.','residual'),
26:('K','A standard Bloom filter rejects some absent keys without false negatives for inserted keys, under its hash/update model.','bloom'),
27:('K','Learned-plus-backup filters have modeled false-positive formulas; target guarantees require the stated query distribution and calibration, not arbitrary shift.','bloom'),
28:('F','There are 2^U subsets but only 2^m summaries; U>m forces two distinct sets to share a summary.','information'),
30:('F','Exact dynamic membership must distinguish all represented sets. Changing the word adaptive does not remove the encoding lower bound.','information'),
31:('Q','The objective is not stated. SRPT is a known optimum for appropriate preemptive single-machine completion-time objectives, not every scheduling objective.','schedule'),
33:('F','Two same-arrival jobs of lengths (1,2) or (2,1) share the initial observation; any first unit of service is wrong on one instance.','schedule'),
34:('K','An advice bit distinguishing the two traces can select the short job. This charges an extra bit of future information.','schedule'),
35:('F','Identical bid histories cannot distinguish the two hidden-length instances; the rejected bids need not reveal the missing fact.','schedule'),
36:('K','In the exact classical bit-query model, flipping an unread bit changes parity while preserving the entire observation transcript.','parity'),
37:('K','The promise {00,11} fixes even parity without reading either bit; the promise supplies extra information.','parity'),
38:('F','Without an input identity observation, old parity cannot distinguish 0 from an unseen replacement 1.','parity'),
40:('F','For parity, two completions of a partial input with an unread unconstrained bit have different results.','parity'),
41:('K','A redundant linear fragment equal to a+b lets either missing summand be reconstructed from the other and the fragment.','coding'),
42:('K','Distinct independent field evaluations give an invertible Vandermonde system. Duplicate points or singular evaluation maps do not.','coding'),
43:('F','With one unseen input bit, AND at observed input 1 has two possible answers; no redundant information can reconstruct both.','information'),
44:('K','Rank of collected linear measurements decides whether the desired linear output is in their span; rank computation is charged.','coding'),
46:('K','Freivalds verification supplies a one-sided bounded-error matrix-product check under its fresh-randomness arithmetic model.','freivalds'),
47:('K','Independent challenges multiply the worst-case failure probabilities; independence and producer timing are essential.','freivalds'),
48:('F','A nonzero error matrix with the public vector in its kernel always passes that projection.','public-projection'),
50:('F','Reusing an exposed insufficient set of projections lets an adaptive producer choose an error in their common kernel. Full-rank checks change cost.','public-projection'),
51:('K','Hazard publication plus validation protects dereferences under the required memory-ordering/reclamation protocol.','reclamation'),
52:('K','RCU reclamation after the applicable grace period is an existing mechanism; no new reader-observation capability follows.','reclamation'),
53:('Q','Unreachable is ambiguous: globally unreachable from every reader differs from retired from a shared data structure. A hidden-reader witness addresses only the latter.','reclamation'),
55:('Q','No writer-progress or successful-allocation obligation is stated. Invisible readers cause a safety/space tradeoff if retirements must continue, but blocking updates avoids that counterexample.','reclamation'),
56:('K','Laplace noise for a sensitivity-one count has a finite differential-privacy bound; observer and neighboring datasets must be defined.','privacy'),
57:('K','A proved privacy filter can stop adaptive querying before exceeding its budget; this is existing adaptive composition.','privacy'),
58:('F','For exact counts 0 versus 1, event output=0 has probability 1 versus 0; no finite epsilon with delta=0 satisfies DP.','privacy'),
60:('F','Exact distinguishable secret-dependent outputs violate pure DP on the neighboring pair; an uninformative constant action is a different capability.','privacy'),
61:('K','Grow-only set union is associative, commutative and idempotent; eventual dissemination gives convergence.','crdt'),
62:('K','Monotone positive consequences need no evidence that no more messages exist; this is the CALM setting.','crdt'),
63:('F','An absent-message prefix is identical to one with a sufficiently delayed message; exact terminating absence needs an extra completeness condition.','absence'),
65:('F','Two replicas can both allocate the same sole resource locally, then merge to an invalid double allocation; a semilattice alone does not prevent it.','crdt'),
66:('K','A dictionary can reduce a specified repetitive corpus after charging the dictionary. It need not reduce arbitrary corpora.','compression'),
67:('K','An exact residual transform can be inverted when prediction state is reproduced; predictor quality affects size, not invertibility.','compression'),
68:('F','At most 2^n-1 binary strings have length below n, fewer than the 2^n possible n-bit inputs.','information'),
70:('F','A fixed lossless map cannot strictly shorten every input; omitted dictionary, precision or compute costs cannot supply an every-workload improvement.','information'),
71:('K','E-graphs already retain multiple rewrite-equivalent forms before extraction under a declared cost model.','equality'),
73:('F','Finite IEEE inputs can give a*b+a*c=2 while a*(b+c)=2.2 due to rounding. Real arithmetic distributivity is not bitwise equality.','float'),
74:('Q','Finite syntax alone does not make semantic equivalence decidable over unbounded programs/inputs. A bounded total semantics makes enumeration possible.','equivalence'),
75:('F','For arbitrary programs a globally cheapest equivalent-program procedure can encode an undecidable halting/equivalence test. Restricted grammars are separate claims.','equivalence'),
76:('K','Reversible simulation retains the distinctions erased by a many-to-one step; the history storage is part of the mechanism.','inverse'),
78:('F','A many-to-one map gives the same output for distinct inputs; an inverse without any retained distinction cannot choose both originals.','inverse'),
79:('U','Logical reversibility supplies no device-independent energy upper bound. No physical device or energy experiment is available here.','energy'),
80:('U','Software reversibility alone does not establish lower total physical energy on every device including I/O and cleanup; hardware data are absent.','energy'),
81:('K','If a stable integral-control loop reaches a bounded steady state, a constant nonzero error would keep changing the integral; plant/actuation assumptions matter.','control'),
82:('K','Antithetic feedback adaptation has specified stochastic-network theorems; no biological experiment or unrestricted workload guarantee is inferred.','control'),
83:('F','Insufficient actuation under constant disturbance makes the state diverge even with zero extra delay, defeating an every-saturation stability claim.','control'),
85:('F','With disturbance 2 and |u|<=1, x_next>=x+1, so bounded-state perfect adaptation cannot hold for every workload.','control'),
86:('K','Time-uniform confidence sequences retain their coverage at admissible stopping times under their stochastic assumptions.','statistics'),
87:('K','Optional reuse of a fixed-time confidence test can exceed nominal rejection probability; exact finite records already exhibit this effect.','statistics'),
88:('F','Calibration scores all zero and a shifted test score one yield zero coverage for the finite split-conformal interval; exchangeability was removed.','conformal'),
90:('Q','No target parameter, nonvacuity requirement, stopping guarantee or dependence model is defined. Always-wide intervals are not a useful new capability.','statistics'),
91:('K','A local edit with deleted bytes and position retained admits an inverse; concurrent edits and external observers require different semantics.','undo'),
92:('K','Operational transformation supplies intention/convergence results for specified operation models and transformation laws, not arbitrary actions.','undo'),
93:('F','Deleting a published bit cannot erase an uncontrolled observer copy; a compensating action need not restore the entire previous world state.','undo'),
95:('F','A bounded log cannot distinguish arbitrarily many erased world states, so it cannot universally reconstruct all of them.','information'),
96:('K','One bit flip changes parity; even numbers of flips may not. The single-error detection claim is established.','coding'),
97:('K','Minimum distance three separates the radius-one decoding balls; a Hamming (7,4) fixture checks every codeword and one-bit flip.','coding'),
98:('F','Healthy history can be followed by either a fault or no fault; a causal predictor produces the same prediction before those futures diverge.','prediction'),
100:('F','Without advance evidence or redundancy, indistinguishable histories cannot guarantee correction before every unheralded fault.','prediction')}
STATUS={'K':'ESTABLISHED BY PRIOR WORK (conditional)','F':'FALSIFIED IN EXPLICIT MODEL','Q':'NEEDS FORMALIZATION','U':'UNVERIFIED PHYSICAL CLAIM'}
all_rows=list(csv.DictReader((ROOT.parent/'hypotheses.csv').open()))
remaining=[r for r in all_rows if r['shortlist']=='False']
assert len(remaining)==80 and {int(r['id'][1:]) for r in remaining}==set(DATA)
anchors=json.loads((ROOT.parent/'raw-results/prior-art-screen.json').read_text())
rows=[]
for original in remaining:
    index=int(original['id'][1:]); status,assessment,hook=DATA[index]
    anchor=anchors[(index-1)//5]
    url=anchor['theory']
    if index==27:url='https://arxiv.org/abs/1802.00884'
    if index==31:url='https://doi.org/10.1287/opre.16.3.687'
    if index==51:url='https://doi.org/10.1109/TPDS.2004.8'
    if index==73:url='https://docs.python.org/3/tutorial/floatingpoint.html'
    if index==75:url='https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf'
    rows.append(dict(id=original['id'],original_statement=original['precise_statement'],
        statement_sha256=hashlib.sha256(original['precise_statement'].encode()).hexdigest(),status=STATUS[status],
        assessment=assessment,primary_source=url,located_family_implementation=anchor['implementation'],
        prior_art_scope='Located primary theory/implementation anchor and claim-specific reasoning; not exhaustive literature/patent review.',
        assumptions=original['required_assumptions'],evidence_hook=hook,
        strong_baseline=original['closest_prior_art'].split('; family anchor')[0],
        novelty='NOT ESTABLISHED; unresolved statements are not declared impossible'))
with (ROOT/'remaining-80-review.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=rows[0],lineterminator='\n');writer.writeheader();writer.writerows(rows)
(ROOT/'raw-results/remaining-80-index.json').write_text(json.dumps(dict(total=80,counts=dict(Counter(r['status'] for r in rows)),
    ids=[r['id'] for r in rows],note='H003/H010/H013/H015/H085/H087 had earlier experimental witnesses; this completes their individual follow-on review, not 80 newly invented experiments.'),indent=2)+'\n')
print(json.dumps(dict(Counter(r['status'] for r in rows))))

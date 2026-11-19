"""Author-maintained discovery catalogue. Run before experiments, never revise frozen claims."""
import csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# family, fields, model, assumptions, baseline, mechanism, counterexample, five distinct claims
FAMILIES=[
('negative feasibility information','optimization; OS admission; convex geometry','A*x<=b; y>=0, y^T*A=0 implies y^T*b>=0','fixed known rational A; changing integer b; exact arithmetic','Farkas certificates / Benders cuts / parametric projection','store verified nonnegative dependencies of matrix rows','an unseen dual ray or a changed matrix invalidates cache completeness',[
'An infeasible two-variable admission request can yield a halfspace rejecting at least two distinct later requests without another feasibility solve.',
'Checking y>=0 and y^T*A=0 once permits sound rejection for every later right-hand side with y^T*b<0.',
'A cached rejection certificate remains sound under arbitrary coefficient-matrix changes without revalidation.',
'A complete set of extreme dual rays classifies all right-hand sides for a fixed matrix with zero per-request LP solves.',
'For A consisting of axis and diagonal bounds in R^2, five stored dependency certificates exactly classify every bounded integer b without solving again; test whether this exceeds an equivalent projected baseline.']),
('observation-action coupling','robotics; control; information theory','U_safe(B)=intersection over x in B of {u:x+u in S}','finite exact belief set B; known dynamics; trusted observation','belief-state POMDP / robust control / event-triggered sensing','act from a shared-safe-action intersection; sense only if needed','two hidden states need different optimal actions',[
'A finite controller can omit one exact sensor read whenever every state in its belief set admits the same safe action.',
'A controller updating the complete reachable belief set preserves one-step safety without measuring on every step.',
'An observation can be skipped whenever one safe action exists while retaining the fully observed optimal action cost for every hidden state.',
'The cardinality of the common safe-action set predicts whether a sensor reading is necessary for one-step robust feasibility.',
'An intersection-based sensor gate can match full-state optimal cost on every trajectory while using strictly fewer observations than a fully observed controller.']),
('useful counterfactual schedules','concurrency; programming languages; model checking','a(b(s))=b(a(s)); quantify over reachable s','finite deterministic transition system; declared observable state','DPOR / context-sensitive independence / concolic execution','cache commutativity evidence and explore a representative schedule','actions commute at initial state but not after a third action',[
'Two universally commuting enabled actions need only one ordering to preserve their final-state outcomes.',
'A checked independence relation plus enabling preservation can reduce a three-action model without losing reachable terminal states.',
'One successful commutativity test at the initial state licenses the same swap at every reachable state.',
'Pairwise independence checking over every finite reachable state can certify reduction without application annotations.',
'A reduction learned only from observed pairwise commutativity can preserve all terminal outcomes of every three-action program without exploring the alternative orders.']),
('representation-changing query reuse','databases; algebra; compiler design','Q(R+delta)=Q(R)+D_Q(R,delta)','explicit representation map; bag semantics; insertions/deletions','DBSP / differential dataflow / incremental view maintenance','transport signed deltas through a verified representation map','a nonlinear aggregate or lossy encoding loses update information',[
'An exact sum can be maintained across row-to-column conversion using a signed update stream and no full rescan.',
'A grouped count can be updated after deletion by retaining multiplicities rather than individual row provenance.',
'An arbitrary lossy summary can support every exact future selection query without retaining the discarded distinctions.',
'A homomorphic representation map commutes with additive deltas when its group-homomorphism law is verified.',
'A representation-aware delta compiler can support exact joins and deletions without rescanning unchanged inputs; compare against DBSP under identical semantics.']),
('precision as a controlled resource','numerical analysis; architecture','r=b-A*x; ||r||/(||A||||x||+||b||)<=tau','finite non-NaN inputs; explicit conditioning and rounding model','mixed-precision iterative refinement / verified residual bounds','use a higher-precision residual to certify a cheaper solution','ill-conditioned matrix or overflow makes residual inconclusive',[
'A low-precision factorization with high-precision residual correction can reach a specified backward-error tolerance.',
'A residual certificate can stop refinement before a fixed iteration budget on a well-conditioned diagonal system.',
'A small residual alone certifies small forward error for every nonsingular matrix.',
'Adaptive precision selected from a certified condition bound can reject an unsafe low-precision solve.',
'A runtime can select the lowest arithmetic precision meeting a per-request certified backward-error target, accounting for verification work.']),
('negative membership information','storage; information theory; security','exact membership over universe U with m bits; collision classes','explicit universe; no hidden backing-store reads','Bloom filters / learned Bloom filters / approximate membership lower bounds','learn a negative filter while retaining an exact fallback','two key sets share the same finite filter representation',[
'A Bloom filter can avoid at least one absent-key disk lookup without false negatives.',
'A learned filter plus backup filter can enforce a stated false-positive target on a fixed distribution.',
'A fixed m-bit filter exactly represents every subset of a universe with size larger than m.',
'An absent-key certificate can be reused until an insertion invalidates the certified interval.',
'An adaptive negative cache can give zero false positives and zero false negatives for every dynamic key set using fewer bits than its information content.']),
('decisions before outcomes','online algorithms; scheduling; economics','regret=L(policy,trace)-min_policy L(policy,trace)','nonclairvoyant arrivals; explicit advice bits and objective','competitive analysis / online algorithms with predictions','use rejected bids as advice with an error budget','two indistinguishable prefixes require different decisions',[
'A scheduler with exact future processing-time advice can choose shortest remaining processing time optimally on its stated objective.',
'A scheduler can retain a bounded competitive ratio when prediction error is arbitrarily large by falling back to an online policy.',
'A deterministic nonclairvoyant scheduler has zero regret against an offline scheduler on every two-job arrival trace.',
'One bit distinguishing two future traces suffices to remove a specific adversarial scheduling ambiguity.',
'Rejected resource bids alone can remove all clairvoyance advantage without assumptions about future arrivals.']),
('computation from absent observations','logic; decision-tree complexity; information theory','parity(x_1,...,x_n); decision-tree depth n','arbitrary independent bits; exact deterministic answer','decision-tree/query complexity / communication lower bounds','share previously queried bits with an exact input identity check','flip the one unread bit',[
'The exact parity of n arbitrary bits requires observing all n bits in the worst case.',
'A promise that an input belongs to a two-element code can reduce exact parity query complexity.',
'An exact parity result for arbitrary new input can be reused without validating any input identity information.',
'A verified common prefix can reduce repeated parity work by its known prefix length.',
'An exact computation cache can answer all unseen n-bit inputs after reading fewer than n unconstrained bits and storing no equivalent advice.']),
('coded partial work','distributed numerical computing; coding theory','recover polynomial/product from k of n worker symbols','linear computation; explicit redundancy and worker failure bound','gradient coding / coded matrix multiplication / polynomial codes','encode subcomputations so completed fragments span required output','insufficient independent fragments or nonlinear workload',[
'Linear coded partial sums can reconstruct a result after one worker erasure using redundant work.',
'Any k independent evaluations of a degree k-1 polynomial suffice for exact interpolation.',
'A general nonlinear function can tolerate arbitrary missing worker outputs with no redundant computation or information.',
'Rank certificates can identify whether collected linear fragments suffice before all workers finish.',
'A runtime can switch decoding bases as fragments arrive without repeating completed linear work; compare against existing coded-computing schedulers.']),
('verification during computation','complexity; cryptography; numerical computation','Pr[false accept]<=2^-k for Freivalds checks','correct verifier; fresh private randomness; adversary timing explicit','Freivalds / interactive proofs / verifiable computation','stream independent checks interleaved with matrix operations','adaptive adversary sees every random challenge before fabricating output',[
'A randomized product verifier checks A*B=C in O(n^2) arithmetic per round with bounded false acceptance.',
'k independent Freivalds rounds reduce a stated soundness bound exponentially.',
'A single public fixed projection certifies arbitrary matrix products against an adaptive producer.',
'Accumulating independent row checks can expose a corruption before computing the complete product.',
'A continuous verifier can reuse public test vectors indefinitely with the same soundness as fresh hidden challenges against adaptive outputs.']),
('reclamation without global observation','memory; concurrency; architecture','free(p) only after every possible reader stops dereferencing p','shared memory; reader/writer execution model specified','hazard pointers / RCU / epoch-based reclamation','publish a read-side certificate or use an external quiescence guarantee','a reader paused before publishing protection',[
'Hazard-pointer publication plus validation can protect an object from concurrent reclamation.',
'A read-copy-update grace period can reclaim retired versions after prior readers quiesce.',
'A writer can safely reclaim any unreachable object while readers publish no information and may pause indefinitely.',
'A bounded reader lifetime permits time-based reclamation if the clock bound is trusted.',
'A reclaimer can simultaneously guarantee wait-free readers, bounded memory and arbitrary reader stalls without any reader announcements or external lifetime bound.']),
('privacy of resource decisions','security; differential privacy; economics','epsilon composition; neighboring workloads differ in one event','explicit observer and adjacency; budget accounting','differential privacy / privacy filters and odometers','account for adaptive admission and timing disclosures','an unbudgeted timing channel reveals the secret event',[
'Adding calibrated noise to an admission count can satisfy an explicit differential-privacy bound.',
'Adaptive resource queries can stop when a valid privacy filter exhausts the budget.',
'A deterministic exact queue-length disclosure is differentially private for neighboring empty/nonempty workloads.',
'Privacy loss can be tracked under adaptive composition with an explicit accountant.',
'A scheduler can reveal exact individual resource consequences while maintaining finite epsilon and zero delta for every neighboring workload.']),
('coordination from monotonic information','distributed systems; logic; databases','monotone Q: x subset y implies Q(x) subset Q(y)','asynchronous delivery; no Byzantine participants; monotone outputs','CALM / CRDTs / invariant confluence','restrict updates so local knowledge grows monotonically','a uniqueness or bounded-counter invariant requires coordination',[
'A grow-only set converges without global ordering under eventual message delivery.',
'A monotone query can emit irrevocable positive results without detecting global completion.',
'An exact absence query can terminate in every asynchronous run without a completeness signal.',
'An escrow allocation can preserve a global bound using preallocated local rights.',
'Every application invariant can be enforced without coordination merely by representing updates as a join-semilattice.']),
('storage entropy and prediction','compression; architecture; information theory','injective encoding; Kraft inequality; expected length >= entropy','lossless decoding; account for model and metadata','source coding / dictionary compression / minimum description length','share a model dictionary across related stored objects','incompressible strings or an omitted model-storage bill',[
'A shared dictionary reduces total bytes for a specified repetitive corpus when dictionary cost is included.',
'A predictor can guide a reversible residual codec without affecting losslessness.',
'A lossless compressor shortens every n-bit input to fewer than n bits.',
'An adaptive code can approach a stationary source entropy rate under its stated source model.',
'A cross-application predictor can reduce storage for every workload without increasing computation, metadata or any input length.']),
('compiler-runtime boundary','compilers; formal methods; algebra','egraph equivalent expressions; extraction minimizes declared cost','sound rewrite rules; explicit cost model; observable semantics','equality saturation / egg / superoptimization','retain equivalent representations until extraction time','a rewrite invalid under overflow, effects or floating-point semantics',[
'Equality saturation can retain multiple equivalent arithmetic forms before selecting by a cost model.',
'A proof-producing rewrite can transport an optimization across two typed intermediate representations.',
'Integer distributivity rewrites preserve IEEE floating-point results bit-for-bit for all finite inputs.',
'A solver can find an optimal expression within an explicitly bounded candidate grammar.',
'A runtime can choose a globally cheapest equivalent expression for arbitrary programs with an unbounded grammar and no termination restriction.']),
('energy and information erasure','physics; architecture; reversible computing','logical reversibility; erased information and thermodynamic assumptions','physical device model; include I/O and garbage cleanup','Bennett reversible computation / Landauer principle','retain reversible history and uncompute temporary data','retained garbage cost or irreversible measurement',[
'A reversible circuit can compute a Boolean function while retaining enough history to invert the mapping.',
'Uncomputation can erase temporary logical garbage by reversing a computation with a copied output.',
'A many-to-one map is invertible without storing any distinction among colliding inputs.',
'Logical reversibility alone guarantees lower measured energy on every physical device.',
'A software-only reversible interpreter lowers total physical energy for every computation including input/output and history cleanup.']),
('biological adaptation','control theory; synthetic biology; resource management','antithetic integral feedback; error integral and stability','known actuator bounds; noise model; stability region','antithetic integral feedback / integral control','coupled opposing counters integrate a resource-target error','actuator saturation, unstable plant or unbounded counter growth',[
'An integral controller removes steady-state error for a stable constant disturbance under its assumptions.',
'Antithetic coupling can provide robust setpoint adaptation in a specified stochastic reaction network.',
'Integral feedback remains stable for every delay and actuator saturation.',
'A finite-state approximation of an integral controller has a measurable steady-state error bound.',
'A biologically inspired allocator guarantees zero steady-state error, bounded state and stability for arbitrary delayed workloads without a plant model.']),
('uncertainty with optional stopping','statistics; AI; scheduling','confidence sequence: Pr[for all t, theta in C_t]>=1-alpha','exchangeability or martingale assumptions stated explicitly','confidence sequences / e-processes / conformal prediction','use an anytime-valid interval to stop costly observations','distribution shift or repeatedly reusing a fixed-time interval',[
'An anytime-valid confidence sequence retains coverage at a data-dependent stopping time.',
'A fixed-time 95 percent interval can lose 95 percent coverage under repeated optional stopping.',
'Conformal intervals maintain their nominal distribution-free coverage after arbitrary adversarial distribution shift.',
'A nonnegative test martingale can support an anytime-valid threshold decision.',
'An adaptive scheduler can stop resource sampling with nominal error guarantees under arbitrary dependent nonstationary workloads and no stochastic assumptions.']),
('human intent and reversible interfaces','HCI; programming languages; effect systems','inverse action f^-1 exists iff required distinctions retained','explicit environment and external-effect reversibility','command pattern / operational transformation / reversible interfaces','record semantic intent and an explicit compensating operation','external observer acts before an attempted undo',[
'A local text-edit command with retained deleted bytes admits an exact inverse.',
'Operational transformation can preserve specified intentions for a defined concurrent text-edit model.',
'Every external action can be exactly undone by a compensating action without controlling other observers.',
'An effect type can reject commands lacking a declared compensation before execution.',
'A universal intent log can reconstruct every previous external world state using bounded metadata independent of the lost information.']),
('fault prediction versus evidence','architecture; reliability; coding theory','parity/syndrome; indistinguishable healthy and future-fault prefixes','explicit fault model; causal sensors only','ECC / scrubbing / predictive failure analysis','combine syndrome telemetry with an explicitly calibrated risk model','a spontaneous unheralded bit flip follows identical healthy history',[
'A parity check detects every single-bit error in a protected word.',
'A distance-three code corrects one arbitrary bit error under its decoding assumptions.',
'Past error counts predict every future spontaneous fault with zero false positives and zero false negatives.',
'An explicit predictive model can trade false alarms against missed failures on held-out labeled traces.',
'A causal software observer guarantees correction before every unheralded hardware fault without redundancy or advance physical evidence.'])]
METHODS=['contradiction mining','boundary removal','cross-domain transfer','counterfactual computation','information-theoretic limits','hidden-state discovery']
SHORTLIST={5,7,14,19,25,29,32,39,45,49,54,59,64,69,72,77,84,89,94,99}
rows=[]
for family_index,(name,fields,model,assumptions,baseline,mechanism,counterexample,claims) in enumerate(FAMILIES):
 for variant,claim in enumerate(claims):
  identity=f'H{family_index*5+variant+1:03}'
  rows.append(dict(id=identity,family=name,discovery_method=METHODS[(family_index+variant)%6],precise_statement=claim,
    why_possible='Provisional mechanism: '+mechanism+'. Functional plausibility is not novelty evidence.',
    challenged_assumption=claims[0],related_fields=fields,closest_prior_art=baseline+'; family anchor only, candidate-level scope must be checked',
    possible_gap='Candidate-specific separation is UNVERIFIED; known baseline may already implement this exact capability.',
    mathematical_formulation=model+'; target property: '+claim,possible_implementation=mechanism,
    expected_benefit='Observe the claimed decision/error/work/storage property against the named baseline, including preprocessing and metadata.',
    required_assumptions=assumptions,potential_counterexample=counterexample,
    falsifying_experiment='Enumerate the smallest bounded model, compare all outputs with an independent oracle, then search adversarial inputs violating: '+claim,
    novelty_confidence='UNVERIFIED; no calibrated probability assigned',scientific_significance='4/5' if variant==4 else '2/5',
    feasibility='4/5 for bounded exploration; universal extensions may be impossible',
    shortlist=(family_index*5+variant+1 in SHORTLIST),screening_status='selected for adversarial prior-art screening' if family_index*5+variant+1 in SHORTLIST else 'not individually reviewed'))
assert len(rows)==100 and len({r['id'] for r in rows})==100
with (ROOT/'hypotheses.csv').open('w',newline='',encoding='utf-8') as f:
 writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
(ROOT/'raw-results/catalogue-freeze.json').write_text(json.dumps(dict(schema_version=1,hypotheses=100,shortlisted=[r['id'] for r in rows if r['shortlist']],
 sha256=hashlib.sha256((ROOT/'hypotheses.csv').read_bytes()).hexdigest(),
 canonical_sha256=hashlib.sha256((ROOT/'hypotheses.csv').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
 protocol='Statements frozen before experiments. Later statuses belong in review/result files, never rewrite this CSV.'),indent=2)+'\n')
print('Frozen 100 hypotheses with all required fields; 20 shortlisted.')

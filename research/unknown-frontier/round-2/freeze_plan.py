import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=[
('H101','catalytic complexity','Full arbitrary borrowed memory can improve specified time-space bounds while being exactly restored, with an equal output interface.','Known catalytic algorithms must be compared under the same output model.','https://arxiv.org/abs/2610.24377'),
('H102','robust catalytic complexity','Allowing expected rather than worst-case reset errors always adds a previously unavailable catalytic capability.','Quantifiers over initial tapes and random coins change the class; check 2026 characterizations.','https://arxiv.org/abs/2605.09648'),
('H103','reversible circuits and coding','A standard end-only single-bit checksum corrects every one-bit transient fault at every point of an arbitrary reversible use/uncompute circuit.','Single physical faults can become multi-bit output differences.','https://preskill.caltech.edu/pubs/preskill-2006-threshold.pdf'),
('H104','zero-error side-information coding','For every two-window CNOT-star channel E_n, ceil(log2 |E_n|) trusted metadata bits suffice to restore every arbitrary n-bit initial word.','Cardinality is a lower bound; pairwise confusability can require more.','https://ieeexplore.ieee.org/document/1228155/'),
('H105','zero-error coding and reversible memory','For E_n={0,unit vectors,all ones}, exact restoration needs four trusted metadata bits at n=5 but only three at n=6; this might provide a capability absent from a generic same-model decoder.','The functional threshold and the novelty/separation obligation are distinct.','https://ieeexplore.ieee.org/document/1228155/'),
('H106','population protocols','A fixed finite-state anonymous population protocol stably decides primality of the population size for every size under standard fair pairwise interactions.','Stable computability is constrained by semilinearity; a changed interaction model is not a counterexample.','SOURCE_TO_VERIFY'),
('H107','nonlocal games','A classical no-communication strategy can win every input pair of the magic-square game using only pre-shared randomness.','Entanglement and communication are extra resources; do not attribute simulated quantum power to Linux.','SOURCE_TO_VERIFY'),
('H108','causal inference','Observational and single-variable interventional distributions always identify the individual response event Y(0)!=Y(1), with no cross-world assumptions.','Equal interventional marginals can have different couplings of potential outcomes.','SOURCE_TO_VERIFY'),
('H109','thermodynamic resource theory','A reversible device can reset an arbitrary unknown bit while exactly restoring an arbitrary catalyst, without exporting entropy or any other state change.','Injectivity excludes universal erasure without an information sink.','https://www.cs.princeton.edu/courses/archive/fall04/cos576/papers/bennett73.html'),
('H110','hyperproperty monitoring','A finite black-box trace monitor can soundly and completely certify noninterference of every program without observing alternative secret inputs or inspecting the program.','Observed finite behavior does not determine an unobserved counterfactual branch.','SOURCE_TO_VERIFY'),
('H111','probabilistic computing','Parallel synchronous updates of all p-bits using their local Gibbs conditionals always preserve the joint target Gibbs distribution.','Conditional distributions alone do not license arbitrary simultaneous updates.','SOURCE_TO_VERIFY'),
('H112','algebraic query packing','A bounded-integer matrix row can be identified with one exact unbounded-width packed probe, and this reduces information cost as well as oracle-call count.','Kronecker-style substitution shifts cost into precision/bit length; charge both.','SOURCE_TO_VERIFY')]
rows=[dict(id=i,field=f,original_statement=s,challenge=c,primary_anchor=u,classification='HYPOTHESIS',novelty='UNVERIFIED') for i,f,s,c,u in DATA]
p=ROOT/'new-hypotheses.json'
assert not p.exists(),'Never overwrite frozen statements'
p.write_text(json.dumps(rows,indent=2)+'\n')
freeze=dict(parent_canonical_sha256=json.loads((ROOT.parent/'raw-results/catalogue-freeze.json').read_text())['canonical_sha256'],
            new_hypotheses_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            protocol_canonical_sha256=hashlib.sha256((ROOT/'protocol.md').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            note='New source URLs are discovery anchors; SOURCE_TO_VERIFY is resolved in a separate review, never by editing frozen statements.')
(ROOT/'raw-results/freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print('Frozen H101-H112 separately from the original 100.')

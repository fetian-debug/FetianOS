"""Additional false-rejection witness; original P0 records remain unchanged."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'baseline-implementation'))
from geometry import A,feasible
b=(0,2,0,2,2,-1)
changed=A[:5]+((1,1),)
assert not feasible(b) and feasible(b,changed)
# The old triangle certificate has y^T b=-1, but no longer y^T A=0.
y=(1,0,1,0,0,1)
residual=[sum(w*row[j] for w,row in zip(y,changed)) for j in range(2)]
assert residual==[2,2]
output=ROOT/'raw-results/certificate-change-supplement.json'
with output.open('x') as f:
 json.dump(dict(id='H003',classification='FALSIFIED',b=b,old_matrix=A,new_matrix=changed,
               old_rejection=True,new_geometry_feasible=True,certificate=y,new_nullspace_residual=residual,
               note='P0 matrix mutant showed false acceptance; this distinct witness shows false rejection and directly addresses cached-rejection soundness.'),f,indent=2);f.write('\n')
print('H003 false-rejection witness independently checked.')

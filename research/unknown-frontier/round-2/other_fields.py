"""Other-field finite controls: classical nonlocal strategies, erasure, monitorability and packing."""
import argparse,hashlib,itertools,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'plan.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),protocol_canonical_sha256=hashlib.sha256((ROOT/'protocol.md').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),scope='finite classical controls; no quantum/thermal hardware'),indent=2)+'\n')
    even=[row for row in itertools.product((0,1),repeat=3) if sum(row)%2==0]
    odd=[column for column in itertools.product((0,1),repeat=3) if sum(column)%2==1]
    scores=[]
    for alice in itertools.product(even,repeat=3):
        for bob in itertools.product(odd,repeat=3):
            wins=sum(alice[i][j]==bob[j][i] for i in range(3) for j in range(3))
            assert wins<9;scores.append(dict(alice=alice,bob=bob,wins=wins))
    assert len(scores)==4096 and max(r['wins'] for r in scores)==8
    with (a.output/'classical-magic-square.jsonl').open('w') as stream:
        for row in scores:stream.write(json.dumps(row)+'\n')
    before=[(bit,catalyst) for bit in (0,1) for catalyst in range(4)]
    after=[(0,catalyst) for bit,catalyst in before]
    assert len(set(before))==8 and len(set(after))==4
    monitor=[dict(program=name,observed_secret=0,observed_output=0,alternative_outputs=outputs,
                  noninterference=len(set(outputs))==1) for name,outputs in [('constant',[0,0]),('leak',[0,1])]]
    assert monitor[0]['noninterference'] and not monitor[1]['noninterference']
    packing=[];probe=(1,3,9)
    for coefficients in itertools.product(range(3),repeat=3):
        observed=sum(x*y for x,y in zip(coefficients,probe))
        restored=tuple((observed//(3**i))%3 for i in range(3))
        assert restored==coefficients
        packing.append(dict(coefficients=coefficients,probe=probe,observation=observed,decoded=restored))
    assert len({r['observation'] for r in packing})==27
    summary=dict(H107=dict(strategies=4096,maximum_wins=8,input_pairs=9,quantum_hardware=False),
                 H109=dict(initial_states=8,required_final_states=4,reversible_bijection_possible=False),
                 H110=dict(indistinguishable_observed_traces=monitor),
                 H112=dict(cases=packing,oracle_calls_per_row=1,maximum_probe_component=9,observation_bits=5,
                           information_lower_bits=math.ceil(math.log2(27)),new_information_capability=False),
                 novelty='known mechanisms/countermodels; not new physical resources or an original quantum strategy')
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k in ('H107','H109')}))

if __name__=='__main__':main()

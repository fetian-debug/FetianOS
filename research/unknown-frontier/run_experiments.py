#!/usr/bin/env python3
"""Reproducible negative novelty experiment; no OS runtime dependencies."""
import argparse,csv,hashlib,itertools,json,os,platform,random,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'baseline-implementation'))
from geometry import A,feasible,grid_feasible
CUTS=((1,1,0,0,0,0),(0,0,1,1,0,0),(0,0,0,0,1,1),(1,0,1,0,0,1),(0,1,0,1,1,0))

def check(value,message):
    if not value: raise AssertionError(message)

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def cache(b,cuts=CUTS,strict=False):
    terms=[sum(x*y for x,y in zip(c,b)) for c in cuts]
    return all(v>0 if strict else v>=0 for v in terms)

def invoke(binary,cases):
    text=''.join(' '.join(map(str,b))+'\n' for b in cases)
    result=subprocess.run([str(binary)],input=text,text=True,capture_output=True,check=True,timeout=60)
    lines=result.stdout.splitlines()
    check(len(lines)==len(cases),'binary lost or added input responses')
    check(all(v in ('FEASIBLE','INFEASIBLE') for v in lines),'binary rejected valid input')
    return [v=='FEASIBLE' for v in lines]

def control_cases():
    states=(-1,0,1); actions=(-1,0,1); records=[]
    for mask in range(1,8):
        belief=[x for i,x in enumerate(states) if mask&(1<<i)]
        # Prototype: set intersection. Baseline: enumerate every state/action pair.
        shared=set(actions)
        for x in belief: shared &= {u for u in actions if abs(x+u)<=1}
        truth={u for u in actions if sum(abs(x+u)<=1 for x in belief)==len(belief)}
        check(shared==truth,'belief safety mechanism differs from truth table')
        records.append(dict(belief=belief,shared_safe_actions=sorted(shared),baseline=sorted(truth)))
    costs={str(u):{str(x):abs(x+u) for x in (-1,1)} for u in actions}
    check(not any(all(costs[str(u)][str(x)]==0 for x in (-1,1)) for u in actions),'missing information counterexample disappeared')
    return dict(trials=records,H007='known one-step safety reproduced; no new baseline capability',
                H010_counterexample=dict(belief=[-1,1],costs=costs,fully_observed_costs=[0,0]),
                incomplete_belief_counterexample=dict(reported_belief=[-1],true_state=1,chosen_action=1,next_state=2,safe=False))

def concurrency_cases():
    actions={'a':lambda s:(s[1],s[1]),'b':lambda s:(0,s[1]),'c':lambda s:(s[0],1)}
    def run(order,state=(0,0)):
        for name in order: state=actions[name](state)
        return state
    records=[dict(schedule=''.join(order),state=run(order)) for order in itertools.permutations('abc')]
    initial_commutes=run('ab')==run('ba')
    reduced=[r for r in records if r['schedule'].index('a')<r['schedule'].index('b')]
    complete_outcomes={tuple(r['state']) for r in records}
    reduced_outcomes={tuple(r['state']) for r in reduced}
    check(initial_commutes and reduced_outcomes<complete_outcomes,'sample commutativity mutant was not exposed')
    reachable={(0,0)}
    for length in range(1,4):
        reachable.update(run(order) for order in itertools.permutations('abc',length))
    all_state_commutes=all(run('ab',s)==run('ba',s) for s in reachable)
    check(not all_state_commutes,'universal checker failed to reject bad swap')
    # Positive control: disjoint-coordinate increments commute at all states.
    independent=[]
    for order in itertools.permutations(range(3)):
        state=[0,0,0]
        for index in order: state[index]+=1
        independent.append(state)
    check(all(s==[1,1,1] for s in independent),'independent positive control failed')
    return dict(records=records,initial_ab_commutes=initial_commutes,reachable_states=sorted(reachable),
                all_state_ab_commutes=all_state_commutes,reduced_records=reduced,
                lost_outcomes=sorted(complete_outcomes-reduced_outcomes),
                independent_positive_control=dict(schedules=6,outcomes=independent),
                H014='universal finite-state check rejects unsafe swap; standard POR obligation',H015='FALSIFIED')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prototype',type=Path,required=True);parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seed',type=int,default=2090)
    args=parser.parse_args();args.prototype=args.prototype.resolve();args.baseline=args.baseline.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    freeze=json.loads((ROOT/'raw-results/catalogue-freeze.json').read_text())
    check(freeze['canonical_sha256']==hashlib.sha256((ROOT/'hypotheses.csv').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'frozen hypotheses changed')
    rng=random.Random(args.seed)
    exhaustive=list(itertools.product((-1,0,1),repeat=6))
    random_cases=[tuple(rng.randint(-8,8) for _ in range(6)) for _ in range(10000)]
    edges=[(0,)*6,(1000000,)*6,(-1000000,)*6,(1000000,-1000000,1000000,-1000000,1000000,-1000000)]
    cases=exhaustive+random_cases+edges
    plan=dict(schema_version=1,seed=args.seed,base_cases=len(cases),exhaustive=729,randomized=10000,domain_edges=edges,
              hypotheses_canonical_sha256=freeze['canonical_sha256'],protocol_sha256=digest(ROOT/'experiment-protocol.md'),
              source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              sources={str(p.relative_to(ROOT)):digest(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.suffix in ('.py','.rs','.md')},
              binaries={str(p):digest(p) for p in (args.prototype,args.baseline)},
              environment=dict(kernel=platform.release(),architecture=platform.machine(),python=platform.python_version(),os=platform.platform()),
              note='Uncommitted source hashes identify artifact contents; git HEAD alone is not a build attestation.')
    (args.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    start=time.perf_counter()
    try:
        proposed=invoke(args.prototype,cases);baseline=invoke(args.baseline,cases)
        with (args.output/'admission.jsonl').open('w') as raw:
            for index,(b,actual,ordinary) in enumerate(zip(cases,proposed,baseline)):
                expected=feasible(b)
                raw.write(json.dumps(dict(index=index,b=b,geometry=expected,certificate=actual,projection=ordinary))+'\n')
                check(actual==ordinary==expected,f'feasibility mismatch at {b}')
        grid_matches=0
        for b in exhaustive:
            check(grid_feasible(b)==feasible(b),'geometry oracle disagrees with independent integer-grid oracle')
            grid_matches+=1
        check(feasible((1,1,1,1,1,1)) and not feasible((0,0,0,0,-1,0)),'oracle analytic fixtures failed')
        transforms=[]
        for _ in range(1000):
            b=rng.choice(cases[:10729]);tx,ty=rng.randint(-3,3),rng.randint(-3,3)
            translated=tuple(bound+p*tx+q*ty for (p,q),bound in zip(A,b))
            scaled=tuple(2*value for value in b)
            transforms.extend([dict(original=b,transformed=translated,kind='translation'),dict(original=b,transformed=scaled,kind='scale')])
        changed=[tuple(r['transformed']) for r in transforms]
        transformed_outputs=invoke(args.prototype,changed);baseline_outputs=invoke(args.baseline,changed)
        with (args.output/'metamorphic.jsonl').open('w') as raw:
            for record,actual,ordinary in zip(transforms,transformed_outputs,baseline_outputs):
                expected=feasible(record['original'])
                check(actual==ordinary==expected==feasible(record['transformed']),'metamorphic invariant failed')
                raw.write(json.dumps(dict(record,expected=expected,certificate=actual,projection=ordinary))+'\n')
        mutants=[]
        for index in range(5):
            incomplete=CUTS[:index]+CUTS[index+1:]
            witness=next(b for b in exhaustive if cache(b,incomplete)!=feasible(b))
            mutants.append(dict(mutation='drop-cut',cut=index,b=witness,mutant=cache(witness,incomplete),oracle=feasible(witness)))
        equality=(0,)*6
        check(feasible(equality) and not cache(equality,strict=True),'strict-boundary mutant survived')
        mutants.append(dict(mutation='reject-equality',b=equality,mutant=False,oracle=True))
        bad=subprocess.run([str(args.prototype),'--invalid-certificate'],capture_output=True,text=True,timeout=5)
        check(bad.returncode==2 and bad.stdout.strip()=='INVALID_CERTIFICATE','invalid negative certificate accepted')
        mutants.append(dict(mutation='negative-weight-certificate',rejected=True,exit_code=bad.returncode))
        b=(2,2,2,2,-1,2); changed_matrix=A[:4]+((0,0),)+A[5:]
        check(cache(b) and not feasible(b,changed_matrix),'matrix-change counterexample failed')
        mutants.append(dict(mutation='reuse-after-matrix-change',b=b,changed_matrix=changed_matrix,old_cache=True,oracle=False))
        invalid=['1 2','0 0 0 0 0 1000001','0 0 0 0 0 -1000001','0 0 0 0 0 NaN','0 '*200,'','9999999999999999999999999999999999999999999 0 0 0 0 0']
        for binary in (args.prototype,args.baseline):
            outcome=subprocess.run([str(binary)],input='\n'.join(invalid)+'\n',text=True,capture_output=True,check=True,timeout=5)
            check(outcome.stdout.splitlines()==['INVALID_INPUT']*len(invalid),'malformed input accepted or lost')
        controls=control_cases();concurrency=concurrency_cases()
        for name,value in [('mutations',mutants),('control',controls),('concurrency',concurrency)]:
            (args.output/f'{name}.json').write_text(json.dumps(value,indent=2)+'\n')
        summary=dict(schema_version=1,seed=args.seed,classification='EXPERIMENTALLY DEMONSTRATED',base_cases=len(cases),
                     functional_mismatches=0,metamorphic_cases=len(transforms),grid_oracle_cases=grid_matches,
                     mutants_exposed=len(mutants),invalid_input_cases_per_binary=len(invalid),belief_cases=7,schedules=6,
                     prototype_online_LP_solves=0,strong_baseline_online_LP_solves=0,
                     new_capability_established=False,novelty_gate='FAILED: equal-assumption conventional baseline already has the capability',
                     H010='FALSIFIED',H015='FALSIFIED',elapsed_seconds=time.perf_counter()-start,
                     proof_scope='written restricted derivations; finite oracle checks, no proof-assistant artifact')
        (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,message=str(error)),indent=2)+'\n')
        raise
    return 0

if __name__=='__main__': raise SystemExit(main())

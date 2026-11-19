#!/usr/bin/env python3
"""P2 finite-channel, causal and sampler experiments. No OS runtime integration."""
import argparse,hashlib,itertools,json,math,platform,random,subprocess,tarfile,traceback
from fractions import Fraction as F
from pathlib import Path
from channel import star,propagate,matrix_error,error_set,graph,colour,generic_decode,check_all_smaller_linear
ROOT=Path(__file__).resolve().parent

def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def digest(path,canonical=False):
    data=Path(path).read_bytes()
    return hashlib.sha256(data.replace(b'\r\n',b'\n') if canonical else data).hexdigest()

def call(binary,lines):
    response=subprocess.run([str(binary)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=30)
    result=response.stdout.splitlines();assert len(result)==len(lines)
    return result

def syndrome(word,n):
    # Independent row/parity expression; the Rust implementation folds columns.
    masks=(0b00101,0b00110,0b01000,0b10000) if n==5 else (0b010101,0b100110,0b111000)
    return sum(((word&mask).bit_count()%2)<<i for i,mask in enumerate(masks))

def decoder(word,saved,n,omit_full=False,truncate=False):
    columns=(1,2,3,4,8) if n==5 else (1,2,3,4,5,6)
    bits=4 if n==5 else 3
    h=lambda w:syndrome(w,n)&((1<<(bits-1))-1 if truncate else (1<<bits)-1)
    saved=saved&((1<<(bits-1))-1) if truncate else saved
    candidates=[word^error for error in error_set(n) if not(omit_full and error==(1<<n)-1) and h(word^error)==saved]
    return candidates[0] if len(candidates)==1 else None

def channel_cases(binary,out,seed):
    all_records=[];proofs=[];mutants=[]
    for n in (5,6):
        gates=star(n);errors=error_set(n);q=16 if n==5 else 8
        colours,nodes=colour(n,q)
        adjacency=graph(n)
        clique=[x for x in range(1<<n) if x.bit_count()%2==0] if n==5 else sorted(errors)
        assert len(clique)==q and all(y in adjacency[x] for x,y in itertools.combinations(clique,2))
        linear=check_all_smaller_linear(n,3 if n==5 else 2);assert linear['valid']==0
        observed_errors={0}
        cases=[]
        # Encode and decode occur in separate processes; D never receives x.
        encoded=call(binary,[f'E {n} {word}' for word in range(1<<n)])
        assert all(int(value)==syndrome(word,n) for word,value in enumerate(encoded))
        for word in range(1<<n):
            events=[(None,None)]+[(window,bit) for window in (0,n-1) for bit in range(n)]
            for window,bit in events:
                observed=word if window is None else propagate(word,gates,window,bit)
                effective=0 if window is None else matrix_error(n,gates,window,bit)
                assert observed==word^effective
                observed_errors.add(effective)
                saved=syndrome(word,n)
                conventional=generic_decode(observed,colours[word],colours,errors)
                assert conventional==word
                cases.append(dict(n=n,word=word,window=window,bit=bit,observed=observed,effective_error=effective,
                                  saved=saved,generic_saved=colours[word],generic_result=conventional))
        assert observed_errors==errors
        result=call(binary,[f'D {n} {r["observed"]} {r["saved"]}' for r in cases])
        for record,value in zip(cases,result):
            assert int(value)==record['word'];record['rust_result']=int(value);all_records.append(record)
        proofs.append(dict(n=n,error_set=sorted(errors),cardinality_lower_bits=math.ceil(math.log2(len(errors))),
                           clique=clique,clique_colours_required=q,minimum_protected_metadata_bits=int(math.log2(q)),
                           generic_colouring=colours,generic_search_nodes=nodes,smaller_linear_checks=linear,
                           static_generic_codebook_bits=(1<<n)*int(math.log2(q)),
                           claim='protected retained metadata only; not total workspace'))
        for name,kwargs in [('omit-full-error',dict(omit_full=True)),('one-less-metadata-bit',dict(truncate=True))]:
            witness=next(r for r in cases if decoder(r['observed'],r['saved'],n,**kwargs)!=r['word'])
            mutants.append(dict(name=name,n=n,witness=witness,mutant_result=decoder(witness['observed'],witness['saved'],n,**kwargs)))
        outside=[('corrupt-metadata',0,1),('two-bit-errors',3,0),
                 ('inside-protected-region',propagate(0,gates,1,0),0)]
        outputs=call(binary,[f'D {n} {observed} {saved}' for _,observed,saved in outside])
        for (name,observed,saved),value in zip(outside,outputs):
            assert value!='0';mutants.append(dict(name=name,n=n,observed=observed,saved=saved,expected_original=0,output=value,
                                                 scope='outside declared trusted/fault assumptions'))
    with (out/'channel-cases.jsonl').open('w') as stream:
        for r in all_records:stream.write(json.dumps(r)+'\n')
    write(out/'channel-proofs.json',proofs);write(out/'channel-mutants.json',mutants)
    rng=random.Random(seed);trials=[]
    for index in range(1000):
        n=rng.randrange(2,9);forward=[tuple(rng.sample(range(n),2)) for _ in range(rng.randrange(1,21))]
        gates=forward+list(reversed(forward));word=rng.randrange(1<<n)
        window=rng.randrange(len(gates)+1);bit=rng.randrange(n)
        observed=propagate(word,gates,window,bit);effective=matrix_error(n,gates,window,bit)
        assert observed==word^effective
        trials.append(dict(index=index,n=n,word=word,gates=gates,window=window,bit=bit,observed=observed,matrix_error=effective,
                           correction_claim=False))
    with (out/'propagation-random.jsonl').open('w') as stream:
        for r in trials:stream.write(json.dumps(r)+'\n')
    invalid=['D 4 0 0','D 5 32 0','D 6 0 8','E 5 -1','E 6 0 extra','D 5 0 NaN','D 5 0',' ']
    assert call(binary,invalid)==['INVALID_INPUT']*len(invalid)
    return dict(exhaustive_physical_cases=len(all_records),random_propagation_cases=len(trials),mutants_exposed=len(mutants),
                invalid_cases=len(invalid),H104='FALSIFIED at n=5',H105_functional='exact bounds 4 and 3 verified',
                generic_baseline_minimum_bits=[4,3],prototype_minimum_bits=[4,3],new_capability_separation=False)

def causal(out):
    models={};records=[]
    for name in ('A','B'):
        observation={};intervention={};response=0
        for x,u in itertools.product((0,1),repeat=2):
            y=u if name=='A' else x^u
            observation[x,y]=observation.get((x,y),0)+F(1,4)
            records.append(dict(model=name,x=x,u=u,y=y))
        for do in (0,1):
            for u in (0,1):
                y=u if name=='A' else do^u
                intervention[do,y]=intervention.get((do,y),0)+F(1,2)
        for u in (0,1):
            y0=u;y1=u if name=='A' else 1^u
            response+=F(y0!=y1,2)
        models[name]=dict(observation=observation,intervention=intervention,response=response)
    assert models['A']['observation']==models['B']['observation']
    assert models['A']['intervention']==models['B']['intervention']
    assert models['A']['response']==0 and models['B']['response']==1
    write(out/'causal.json',dict(records=records,models={name:{k:({str(key):str(v) for key,v in value.items()} if isinstance(value,dict) else str(value)) for k,value in model.items()} for name,model in models.items()},
                                  H108='FALSIFIED',novelty='known nonidentification mechanism, independently instantiated'))
    return dict(assignments=len(records),response_A='0',response_B='1',observables_equal=True,interventions_equal=True)

def sampling(out):
    states=list(itertools.product((0,1),repeat=2));pi=[F(3,8),F(1,8),F(1,8),F(3,8)]
    sync=[];sequential=[]
    for a,b in states:
        ps=[];pq=[]
        for c,d in states:
            ps.append((F(3,4) if c==b else F(1,4))*(F(3,4) if d==a else F(1,4)))
            pq.append((F(3,4) if c==b else F(1,4))*(F(3,4) if d==c else F(1,4)))
        sync.append(ps);sequential.append(pq)
    assert all(sum(row)==1 for row in sync+sequential)
    distribution=lambda matrix:[sum(pi[i]*matrix[i][j] for i in range(4)) for j in range(4)]
    assert distribution(sync)!=pi and distribution(sequential)==pi
    # Independent primitive-noise enumerator: four equally likely choices per
    # local update; three copy the chosen neighbour and one inverts it.
    for mode,matrix in [('sync',sync),('sequential',sequential)]:
        for i,(a,b) in enumerate(states):
            counts=[0]*4
            for first,second in itertools.product(range(4),repeat=2):
                c=b if first<3 else 1-b
                source=a if mode=='sync' else c
                d=source if second<3 else 1-source
                counts[states.index((c,d))]+=1
            assert [F(v,16) for v in counts]==matrix[i]
    write(out/'sampling.json',dict(states=states,target=list(map(str,pi)),synchronous=[[str(v) for v in r] for r in sync],
                                    sequential=[[str(v) for v in r] for r in sequential],after_sync=list(map(str,distribution(sync))),
                                    after_sequential=list(map(str,distribution(sequential))),H111='FALSIFIED',
                                    primitive_trajectories=128,hardware=False))
    return dict(states=4,primitive_trajectories=128,synchronous_stationary=False,sequential_stationary=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=2090);args=parser.parse_args();args.binary=args.binary.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    freeze=json.loads((ROOT/'raw-results/freeze.json').read_text())
    assert digest(ROOT/'new-hypotheses.json',True)==freeze['new_hypotheses_sha256']
    assert digest(ROOT/'protocol.md',True)==freeze['protocol_canonical_sha256']
    sources={str(p.relative_to(ROOT)):digest(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.suffix in ('.py','.rs','.md')}
    write(args.output/'plan.json',dict(seed=args.seed,protocol=freeze,sources=sources,binary_sha256=digest(args.binary),
                                      environment=dict(kernel=platform.release(),python=platform.python_version(),architecture=platform.machine()),
                                      scope='finite exact models, simulated faults; no physical hardware or catalytic complexity claim'))
    with tarfile.open(args.output/'source-snapshot.tar.gz','w:gz') as snapshot:
        for source in sources:snapshot.add(ROOT/source,arcname=source)
        snapshot.add(ROOT/'new-hypotheses.json',arcname='new-hypotheses.json')
    try:
        summary=dict(seed=args.seed,channel=channel_cases(args.binary,args.output,args.seed),causal=causal(args.output),sampling=sampling(args.output),
                     classification='EXPERIMENTALLY DEMONSTRATED within explicit finite models',novel_capability_established=False)
        write(args.output/'summary.json',summary);print(json.dumps(summary),flush=True)
    except Exception as error:
        write(args.output/'failure.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()));raise

if __name__=='__main__':main()

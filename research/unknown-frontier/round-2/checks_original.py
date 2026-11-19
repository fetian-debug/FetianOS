#!/usr/bin/env python3
"""Finite adversarial witnesses for the original-80 review, not 80 new inventions."""
import argparse,csv,hashlib,itertools,json,math,random,sys,traceback,zlib
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'baseline-implementation'))
from geometry import A,feasible

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=2090)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rng=random.Random(a.seed);records=[]
    def record(hook,ids,scope,**payload):
        records.append(dict(hook=hook,ids=ids,scope=scope,**payload))
    (a.output/'plan.json').write_text(json.dumps(dict(seed=a.seed,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_canonical_sha256=hashlib.sha256((ROOT.parent/'hypotheses.csv').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        rule='Finite witnesses and written reasoning do not empirically prove universal claims.'),indent=2)+'\n')
    try:
        cuts=((0,1),(2,3),(4,5),(0,2,5),(1,3,4));dual_cases=[]
        for b in itertools.product((-1,0,1),repeat=6):
            proposed=all(sum(b[i] for i in cut)>=0 for cut in cuts);truth=feasible(b)
            assert proposed==truth;dual_cases.append(dict(b=b,cuts=proposed,geometry=truth))
        record('dual',[1,2,4],'fixed two-variable matrix only; general theorem is prior work',cases=dual_cases)
        b=(0,2,0,2,2,-1);changed=A[:5]+((1,1),)
        assert not feasible(b) and feasible(b,changed)
        record('matrix-change',[3],'one explicit false rejection',b=b,old_feasible=False,new_feasible=True,changed_matrix=changed)
        beliefs=[]
        for mask in range(1,8):
            belief=[x for i,x in enumerate((-1,0,1)) if mask&(1<<i)]
            sets=[{u for u in (-1,0,1) if abs(x+u)<=1} for x in belief]
            shared=set.intersection(*sets)
            assert shared=={u for u in (-1,0,1) if all(abs(x+u)<=1 for x in belief)}
            beliefs.append(dict(belief=belief,safe=sorted(shared)))
        record('belief',[6],'complete-belief one-step model',cases=beliefs)
        costs={str(u):[abs(-1+u),abs(1+u)] for u in (-1,0,1)}
        assert not any(values==[0,0] for values in costs.values())
        record('blind-cost',[8,10],'indistinguishable hidden states',costs=costs,informed=[0,0])
        empties=[]
        for belief in ((-2,2),(-3,3)):
            sets=[{u for u in (-1,0,1) if abs(x+u)<=1} for x in belief]
            assert not set.intersection(*sets)
            empties.append(dict(belief=belief,common_count=0,each_state_has_action=all(sets)))
        assert empties[0]['each_state_has_action'] and not empties[1]['each_state_has_action']
        record('belief-empty',[9],'ambiguity witness, not a falsification of an undefined predicate',cases=empties)
        actions={'a':lambda s:(s[1],s[1]),'b':lambda s:(0,s[1]),'c':lambda s:(s[0],1)}
        def run(order,state=(0,0)):
            for op in order:state=actions[op](state)
            return state
        schedules=[dict(order=''.join(order),result=run(order)) for order in itertools.permutations('abc')]
        reduced=[r for r in schedules if r['order'].index('a')<r['order'].index('b')]
        assert run('ab')==run('ba') and run('cab')!=run('cba')
        assert {r['result'] for r in reduced}<{r['result'] for r in schedules}
        record('context',[13,15],'terminal states of three finite actions',all_orders=schedules,reduced=reduced)
        positive=[]
        for order in itertools.permutations(range(3)):
            state=[0]*3
            for op in order:state[op]+=1
            assert state==[1,1,1];positive.append(dict(order=order,result=state))
        record('commute',[11,12],'total enabled independent increments',cases=positive)
        rows=[(rng.randrange(4),rng.randrange(-3,4)) for _ in range(12)];counts=Counter(k for k,_ in rows);total=sum(v for _,v in rows)
        changes=[]
        for _ in range(500):
            if rows and (len(rows)>=24 or rng.randrange(2)):
                row=rows.pop(rng.randrange(len(rows)));delta=-1
            else:row=(rng.randrange(4),rng.randrange(-3,4));rows.append(row);delta=1
            counts[row[0]]+=delta;total+=delta*row[1]
            assert total==sum(v for _,v in rows)
            assert +counts==Counter(k for k,_ in rows)
            changes.append(dict(row=row,delta=delta,total=total,group_counts=dict(+counts)))
        record('delta',[16,17,20],'500 exact additive/bag updates; no production compiler claim',changes=changes)
        eps=F(1,10**12);residual=eps;forward=F(1)
        assert residual<F(1,10**6) and forward==1
        record('residual',[21,22,23,24],'exact diagonal witness, not a mixed-precision library benchmark',matrix=['1/1000000000000','1'],exact_solution=[1,1],candidate=[0,1],residual=str(residual),forward_error=str(forward))
        bits=set();keys={2,5}
        hashes=lambda k:{k%16,(3*k+1)%16}
        for key in keys:bits|=hashes(key)
        assert all(hashes(k)<=bits for k in keys)
        absent=next(k for k in range(100) if k not in keys and not hashes(k)<=bits)
        record('bloom',[26,27],'toy no-false-negative/absent-key check; distributional guarantee remains prior theorem',inserted=sorted(keys),rejected_absent=absent)
        def completion(order,lengths):
            done=[0,0];times=[None,None]
            for t,job in enumerate(order,1):
                done[job]+=1
                if done[job]==lengths[job]:times[job]=t
            assert done==list(lengths)
            return sum(times)
        policies=[]
        for first in (0,1):
            instances=[]
            for lengths in ((1,2),(2,1)):
                orders=set(itertools.permutations([0]*lengths[0]+[1]*lengths[1]))
                optimum=min(completion(order,lengths) for order in orders)
                online=min(completion(order,lengths) for order in orders if order[0]==first)
                assert optimum==4;instances.append(dict(lengths=lengths,online_best_after_first=online,clairvoyant=optimum))
            assert any(r['online_best_after_first']>r['clairvoyant'] for r in instances)
            policies.append(dict(first=first,instances=instances))
        record('schedule',[31,33,34,35],'unit-quanta single-machine sum-of-completion-times; H031 remains objective-dependent',policies=policies,advice_bits=1)
        parity=[]
        for n in range(1,9):
            for observed_mask in range((1<<n)-1):
                unseen=next(i for i in range(n) if not (observed_mask>>i)&1)
                x=0;y=1<<unseen
                assert x&observed_mask==y&observed_mask and x.bit_count()%2!=y.bit_count()%2
                parity.append(dict(n=n,read_mask=observed_mask,x=x,y=y))
        record('parity',[36,37,38,40],'502 static partial-observation witnesses; adaptive lower bound is a written indistinguishability argument',cases=parity,promise=[0,3],promised_parity=0)
        record('information',[18,28,30,43,68,70,95],'pigeonhole arguments; finite counts illustrate the universal proof',subsets_of_3=8,two_bit_summaries=4,three_bit_inputs=8,strings_shorter_than_3=7,
               lossy_summary_collision=dict(inputs=[[0],[1]],summary='one element',distinguishing_query='contains 0'),and_unseen=dict(observed_x=1,possible_y=[0,1],possible_result=[0,1]))
        fragments=[]
        for x,y in itertools.product(range(16),repeat=2):
            coded=x^y;assert coded^y==x and coded^x==y
            fragments.append(dict(x=x,y=y,fragment=coded))
        polynomials=[]
        for slope,intercept in itertools.product(range(5),repeat=2):
            values=[intercept,(slope+intercept)%5]
            assert (values[1]-values[0])%5==slope
            polynomials.append(dict(coefficients=[intercept,slope],values=values))
        record('coding-linear',[41,42,44],'GF(2) erasure and GF(5) degree-one interpolation examples only',xor_cases=fragments,polynomial_cases=polynomials)
        projection=[]
        for r in itertools.product((0,1),repeat=2):
            passed=r[0]-r[1]==0;projection.append(dict(r=r,forged_pass=passed))
        assert sum(r['forged_pass'] for r in projection)==2
        assert next(r for r in projection if r['r']==(1,1))['forged_pass']
        record('public-projection',[46,47,48,50],'exact 2x2 one-round random-vector sample space; public challenge forgery',error_matrix=[[1,-1],[0,0]],vectors=projection,independent_failure_bound=[str(F(1,2)**k) for k in range(1,7)],public_failure_probability='1')
        record('reclamation',[51,52,53,55],'symbolic invisible-reader worlds; no actual unsafe dereference. H053/H055 need definitions/progress assumptions.',writer_visible={'shared_pointer':None,'announcements':[]},hidden_worlds=[{'reader':'none'},{'reader':'retired node'}],
               conditional_tradeoff='If updates must continue indefinitely, keep every possibly held node or risk freeing a hidden reference. Blocking updates escapes this premise.')
        assert not 1<=math.exp(1)*0
        record('privacy',[56,57,58,60],'exact deterministic disclosure violates pure DP; noise/accounting results are prior theory',event='output equals 0',probability_count0=1,probability_count1=0,finite_epsilon='any',delta=0)
        merges=[]
        for order in itertools.permutations((frozenset({'a'}),frozenset({'b'}),frozenset({'a'}))):
            state=set()
            for message in order:state|=message
            assert state=={'a','b'};merges.append([sorted(m) for m in order])
        record('crdt',[61,62,65],'grow-only convergence and sole-resource uniqueness counterexample',orders=merges,local_grants=[True,True],merged_allocations=2,capacity=1)
        record('absence',[63],'for any finite no-message prefix, a later message remains possible',prefixes=[1,2,8],indistinguishable_worlds=['no message ever','message delivered after termination'])
        dictionary=b'alpha beta gamma delta '*10;payload=dictionary*100
        compressor=zlib.compressobj(zdict=dictionary);packed=compressor.compress(payload)+compressor.flush()
        assert len(packed)+len(dictionary)<len(payload)
        decompressor=zlib.decompressobj(zdict=dictionary);assert decompressor.decompress(packed)+decompressor.flush()==payload
        original=bytes(rng.randrange(256) for _ in range(256));previous=0;residuals=[]
        for value in original:residuals.append((value-previous)%256);previous=value
        previous=0;restored=[]
        for value in residuals:previous=(previous+value)%256;restored.append(previous)
        assert bytes(restored)==original
        record('compression',[66,67],'specified corpus/dictionary and reversible residual transform; not every-input compression',input_bytes=len(payload),dictionary_bytes=len(dictionary),compressed_bytes=len(packed),residual_bytes=len(residuals),roundtrip=True)
        aa=1.1;bb=1e16;cc=-1e16+2
        left=aa*bb+aa*cc;right=aa*(bb+cc)
        assert math.isfinite(left) and math.isfinite(right) and left!=right
        record('float',[73],'actual finite Python binary64 operations; no reassociation',inputs=[v.hex() for v in (aa,bb,cc)],left=left.hex(),right=right.hex())
        record('equivalence',[71,74,75],'written undecidability reduction, not an executable proof of the halting theorem',finite_domain_example=list(range(-4,5)),equivalent_values=[2*x for x in range(-4,5)],
               reduction='Let P run machine M then return zero. Under a cost model making immediate constant-zero the only cost-zero program, a universal minimum-equivalent-program procedure would decide whether M halts. H074 requires bounded total semantics, not finite syntax alone.')
        collisions={}
        for word in range(16):collisions.setdefault(word.bit_count()%2,[]).append(word)
        assert any(len(v)>1 for v in collisions.values())
        assert len({(word,word.bit_count()%2) for word in range(16)})==16
        record('inverse',[76,78],'distinctions retained versus discarded',many_to_one=collisions,reversible_pairs=16)
        record('energy',[79,80],'UNVERIFIED: no physical measurement',measured=False,logical_reversibility_is_not_an_energy_upper_bound=True)
        x=integral=0;trajectory=[]
        for t in range(32):
            integral=max(-4,min(4,integral+x));u=max(-1,min(1,integral));old=x;x+=2-u
            assert x>=old+1;trajectory.append(dict(t=t,u=u,x=x))
        record('control',[81,82,83,85],'bounded-actuator counterexample only; no stochastic biomolecular experiment',trajectory=trajectory,zero_disturbance_equilibrium=True)
        old=json.loads((ROOT.parent/'raw-results/follow-on/summary.json').read_text())
        assert F(old['naive_optional_probability'])>F(1,20) and F(old['anytime_probability'])<=F(1,20)
        record('statistics',[86,87,90],'links to earlier complete 65,536-path enumeration; not a new run or arbitrary-dependence guarantee',previous_file='../raw-results/follow-on/summary.json',previous_sha256=hashlib.sha256((ROOT.parent/'raw-results/follow-on/summary.json').read_bytes()).hexdigest(),
               H090='NEEDS FORMALIZATION, vacuous intervals/stopping loopholes not excluded')
        scores=[0]*20;rank=math.ceil((len(scores)+1)*.95);q=sorted(scores)[rank-1]
        assert q==0 and abs(1)>q
        record('conformal',[88],'split-conformal finite calibration/test distribution-shift counterexample',calibration=scores,rank=rank,q=q,test_score=1,covered=False)
        before='abcdef';removed=before[2:4];after=before[:2]+before[4:];restored=after[:2]+removed+after[2:]
        assert restored==before
        record('undo',[91,92,93],'local edit inverse and uncontrolled observer; no OT implementation benchmark',local_before=before,local_after=after,retained=removed,restored=restored,
               external_before={'published':0,'observer_copy':0},external_after_compensation={'published':0,'observer_copy':1})
        def hs(word):
            return sum((sum((word>>(j-1))&1 for j in range(1,8) if j&p)%2)*p for p in (1,2,4))
        codes=[]
        for data in range(16):
            word=sum(((data>>i)&1)<<(j-1) for i,j in enumerate((3,5,6,7)))
            for pbit in (1,2,4):
                parity_bit=sum((word>>(j-1))&1 for j in range(1,8) if j&pbit)%2
                word|=parity_bit<<(pbit-1)
            assert hs(word)==0;codes.append(word)
        assert min((x^y).bit_count() for x,y in itertools.combinations(codes,2))==3
        coding=[]
        for code in codes:
            for fault in [0]+[1<<i for i in range(7)]:
                damaged=code^fault;location=hs(damaged);corrected=damaged^(1<<(location-1)) if location else damaged
                nearest=[x for x in codes if (x^damaged).bit_count()<=1]
                assert nearest==[code] and corrected==code
                assert (damaged.bit_count()%2)!=(code.bit_count()%2) if fault else True
                coding.append(dict(code=code,fault=fault,damaged=damaged,corrected=corrected))
        record('coding',[96,97],'all Hamming (7,4) codewords and radius-one faults; independent nearest-codeword oracle',cases=coding)
        record('prediction',[98,100],'causal indistinguishable-prefix argument, not physical fault prediction',history=[0,0,0],possible_futures=[0,1],
               predictions=[dict(predict=p,wrong_on=1-p) for p in (0,1)])
        with (a.output/'checks.jsonl').open('w') as stream:
            for row in records:stream.write(json.dumps(row,default=str)+'\n')
        reviewed=list(csv.DictReader((ROOT/'remaining-80-review.csv').open()))
        covered={identity for row in records for identity in row['ids']}
        assert {int(row['id'][1:]) for row in reviewed}<=covered
        # H020's full incremental compiler is located prior work; no such
        # compiler or mixed-precision/OT/biological implementation is claimed here.
        summary=dict(seed=a.seed,reviewed_ids=80,evidence_groups=len(records),finite_fixture_counts=dict(dual=729,beliefs=7,context_schedules=6,independent_schedules=6,
            additive_updates=500,partial_parity_transcripts=len(parity),xor_fragments=256,polynomials=25,hamming_cases=128),
            no_unexpected_failures=True,scope='a group may cover several known/qualified claims; counts are not 80 independent new algorithms')
        (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
    except Exception as error:
        (a.output/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()),indent=2)+'\n');raise

if __name__=='__main__':main()

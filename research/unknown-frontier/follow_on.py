"""Exact finite optional-stopping model and actuator-bound counterexample."""
import argparse,gzip,hashlib,json,math
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def tail(t,k):
    return min(Fraction(1),2*sum((Fraction(math.comb(t,j),2**t) for j in range(min(k,t-k)+1)),Fraction(0)))

def independent_tail(t,k):
    distance=abs(2*k-t)
    return sum((Fraction(math.comb(t,j),2**t) for j in range(t+1) if abs(2*j-t)>=distance),Fraction(0))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    alpha=Fraction(1,20);horizon=16
    (a.output/'plan.json').write_text(json.dumps(dict(horizon=horizon,paths=2**horizon,alpha=str(alpha),protocol_sha256=hashlib.sha256((ROOT/'follow-on-protocol.md').read_bytes()).hexdigest()),indent=2)+'\n')
    probabilities={};sizes=[]
    for t in range(1,horizon+1):
        for k in range(t+1):
            assert tail(t,k)==independent_tail(t,k)
            probabilities[t,k]=tail(t,k)
        size=sum((Fraction(math.comb(t,k),2**t) for k in range(t+1) if probabilities[t,k]<=alpha),Fraction(0))
        assert size<=alpha
        sizes.append(dict(t=t,exact_rejection_probability=str(size)))
    naive=anytime=final=0
    with gzip.open(a.output/'coin-paths.jsonl.gz','wt') as raw:
        for word in range(2**horizon):
            k=0; first_naive=first_anytime=None
            for t in range(1,horizon+1):
                k+=(word>>(t-1))&1
                if first_naive is None and probabilities[t,k]<=alpha:first_naive=t
                if first_anytime is None and probabilities[t,k]<=alpha/Fraction(t*(t+1)):first_anytime=t
            naive+=first_naive is not None;anytime+=first_anytime is not None
            final+=probabilities[horizon,k]<=alpha
            raw.write(json.dumps(dict(word=word,bit_order='least significant first',first_naive=first_naive,first_anytime=first_anytime,final_p=str(probabilities[horizon,k])))+'\n')
    assert Fraction(naive,2**horizon)>alpha
    assert Fraction(anytime,2**horizon)<=alpha
    power_time=next(t for t in range(1,65) if tail(t,t)<=alpha/Fraction(t*(t+1)))
    x=integral=0;trajectory=[]
    for t in range(32):
        integral=max(-4,min(4,integral+x))
        u=max(-1,min(1,integral));previous=x;x=x+2-u
        assert x>=previous+1
        trajectory.append(dict(t=t,previous=previous,integral=integral,action=u,x=x))
    assert 0+0-0==0
    summary=dict(classification='EXPERIMENTALLY DEMONSTRATED: exact finite model',fair_coin_paths=2**horizon,horizon=horizon,
                 naive_optional_rejections=naive,naive_optional_probability=str(Fraction(naive,2**horizon)),
                 anytime_rejections=anytime,anytime_probability=str(Fraction(anytime,2**horizon)),
                 final_time_rejections=final,final_time_probability=str(Fraction(final,2**horizon)),
                 fixed_time_sizes=sizes,anytime_all_ones_detection_time=power_time,
                 actuator_counterexample=trajectory,H087='known optional-stopping failure reproduced',
                 H085='FALSIFIED under bounded-actuator disturbance fixture',new_capability_established=False,
                 assumptions='independent fair coins for size guarantee; alpha-spending baseline; deterministic bounded-control simulation')
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('fixed_time_sizes','actuator_counterexample')}),flush=True)

if __name__=='__main__':main()

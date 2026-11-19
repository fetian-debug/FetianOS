"""P3 linear-code family validation; no larger-n nonlinear-optimality claim."""
import argparse,hashlib,json,random,traceback
from functools import reduce
from operator import xor
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def parity(word,rows):return sum(((word&row).bit_count()%2)<<i for i,row in enumerate(rows))
def rows_of(columns,bits):return [sum(((value>>bit)&1)<<i for i,value in enumerate(columns)) for bit in range(bits)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=2090)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'plan.json').write_text(json.dumps(dict(id='H113',seed=a.seed,protocol_sha256=hashlib.sha256((ROOT/'family-protocol.md').read_bytes()).hexdigest(),
          source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),m_range=[3,10],words_per_condition=100,
          hypothesis='linear redundancy m+1 at n=2^m-3, m at n=2^m-2; nonlinear larger-n optimum UNVERIFIED'),indent=2)+'\n')
    rng=random.Random(a.seed);conditions=[];records=[]
    try:
        for m in range(3,11):
            for deficit in (3,2):
                n=(1<<m)-deficit;bits=m+(deficit==3)
                columns=[i+1 for i in range(n)]
                low_xor=reduce(xor,columns,0)
                if deficit==3:
                    assert low_xor in columns
                    columns[1]|=1<<m
                rows=rows_of(columns,bits)
                errors=[0,*[1<<i for i in range(n)],(1<<n)-1]
                outputs=[parity(error,rows) for error in errors]
                assert len(set(outputs))==len(errors)
                mapping=dict(zip(outputs,errors))
                if deficit==2:assert low_xor not in columns and low_xor!=0
                else:assert (outputs[-1]&((1<<m)-1))==1 and outputs[-1]!=outputs[1]
                conditions.append(dict(m=m,n=n,linear_metadata_bits=bits,error_syndromes=outputs,
                                       low_rows_full_error_syndrome=low_xor,linear_optimum_claim=True,nonlinear_optimum_claim=False))
                for index in range(100):
                    word=rng.getrandbits(n);error=rng.choice(errors);observed=word^error
                    saved=parity(word,rows);restored=observed^mapping[parity(observed,rows)^saved]
                    assert restored==word
                    records.append(dict(m=m,n=n,index=index,word=hex(word),error=hex(error),observed=hex(observed),saved=saved,restored=hex(restored)))
        (a.output/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
        with (a.output/'cases.jsonl').open('w') as stream:
            for r in records:stream.write(json.dumps(r)+'\n')
        summary=dict(id='H113',seed=a.seed,conditions=len(conditions),random_cases=len(records),errors_checked=sum(len(c['error_syndromes']) for c in conditions),
                     observed_mismatches=0,classification='EXPERIMENTALLY DEMONSTRATED construction; universal linear bound needs written proof',
                     new_capability_established=False,larger_n_nonlinear_optimality='UNVERIFIED')
        (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
    except Exception as error:
        (a.output/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()),indent=2)+'\n');raise

if __name__=='__main__':main()

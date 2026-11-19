#!/usr/bin/env python3
"""Recompute retained finite evidence without trusting success summaries."""
import csv,hashlib,itertools,json,math,tarfile
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(path):return json.loads(path.read_text())
def verify():
    original=list(csv.DictReader((ROOT.parent/'hypotheses.csv').open()))
    rows=list(csv.DictReader((ROOT/'remaining-80-review.csv').open()))
    expected={r['id']:r['precise_statement'] for r in original if r['shortlist']=='False'}
    assert len(rows)==80 and {r['id'] for r in rows}==set(expected)
    assert all(r['original_statement']==expected[r['id']] and r['statement_sha256']==hashlib.sha256(expected[r['id']].encode()).hexdigest() for r in rows)
    freeze=read(ROOT/'raw-results/freeze.json')
    canonical=lambda path:hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    assert canonical(ROOT.parent/'hypotheses.csv')==freeze['parent_canonical_sha256']
    assert canonical(ROOT/'new-hypotheses.json')==freeze['new_hypotheses_sha256']
    assert canonical(ROOT/'protocol.md')==freeze['protocol_canonical_sha256']
    assert len(read(ROOT/'new-hypotheses.json'))==12
    for seed in (2090,2091):
        folder=ROOT/f'raw-results/seed-{seed}';proofs=read(folder/'channel-proofs.json')
        for p in proofs:
            n=p['n'];errors={0,(1<<n)-1,*[1<<i for i in range(n)]}
            differences={a^b for a in errors for b in errors}-{0};colours=p['generic_colouring'];clique=p['clique']
            assert len(clique)==(16 if n==5 else 8)
            assert all((a^b) in differences for a,b in itertools.combinations(clique,2))
            assert all(colours[x]!=colours[x^d] for x in range(1<<n) for d in differences)
            assert len(set(colours))==len(clique)
        records=[json.loads(line) for line in (folder/'channel-cases.jsonl').open()]
        assert len(records)==1184 and len({(r['n'],r['word'],r['window'],r['bit']) for r in records})==1184
        for r in records:
            n=r['n'];errors={0,(1<<n)-1,*[1<<i for i in range(n)]}
            assert r['observed']^r['word'] in errors and r['effective_error']==r['observed']^r['word']
            assert r['rust_result']==r['generic_result']==r['word']
        random_cases=[json.loads(line) for line in (folder/'propagation-random.jsonl').open()]
        assert len(random_cases)==1000
        for r in random_cases:
            bits=[(r['word']>>i)&1 for i in range(r['n'])]
            for index,(control,target) in enumerate(r['gates']):
                if index==r['window']:bits[r['bit']]^=1
                bits[target]^=bits[control]
            if r['window']==len(r['gates']):bits[r['bit']]^=1
            observed=sum(value<<i for i,value in enumerate(bits))
            assert observed==r['observed']==r['word']^r['matrix_error']
        assert len(read(folder/'channel-mutants.json'))==10
        causal=read(folder/'causal.json')['models']
        assert causal['A']['observation']==causal['B']['observation'] and causal['A']['intervention']==causal['B']['intervention']
        assert causal['A']['response']=='0' and causal['B']['response']=='1'
        sample=read(folder/'sampling.json');pi=list(map(F,sample['target']))
        for name,key in [('synchronous','after_sync'),('sequential','after_sequential')]:
            matrix=[[F(value) for value in row] for row in sample[name]]
            assert all(sum(row)==1 for row in matrix)
            after=[sum(pi[i]*matrix[i][j] for i in range(4)) for j in range(4)]
            assert after==list(map(F,sample[key]))
            assert (after==pi)==(name=='sequential')
        plan=read(folder/'plan.json')
        with tarfile.open(folder/'source-snapshot.tar.gz','r:gz') as archive:
            for path,value in plan['sources'].items():assert hashlib.sha256(archive.extractfile(path).read()).hexdigest()==value,path
    checks=[json.loads(line) for line in (ROOT/'raw-results/original-80-fixed-seed-2090/checks.jsonl').open()]
    assert {int(r['id'][1:]) for r in rows}<={identity for row in checks for identity in row['ids']}
    assert next(r for r in checks if r['hook']=='energy')['measured'] is False
    assert next(r for r in checks if r['hook']=='float')['left']!=next(r for r in checks if r['hook']=='float')['right']
    strategies=[json.loads(line) for line in (ROOT/'raw-results/other-fields-planned/classical-magic-square.jsonl').open()]
    assert len(strategies)==4096 and len({json.dumps([r['alice'],r['bob']]) for r in strategies})==4096
    for r in strategies:
        assert all(sum(row)%2==0 for row in r['alice']) and all(sum(col)%2==1 for col in r['bob'])
        assert r['wins']==sum(r['alice'][i][j]==r['bob'][j][i] for i in range(3) for j in range(3))
    assert max(r['wins'] for r in strategies)==8
    family=read(ROOT/'raw-results/family-2090/conditions.json')
    assert len(family)==16
    for r in family:
        m,n=r['m'],r['n'];columns=list(range(1,n+1))
        if n==(1<<m)-3:columns[1]|=1<<m
        expected_syndromes=[0,*columns]
        full=0
        for value in columns:full^=value
        expected_syndromes.append(full)
        assert expected_syndromes==r['error_syndromes'] and len(set(expected_syndromes))==n+2
    trials=[json.loads(line) for line in (ROOT/'raw-results/family-2090/cases.jsonl').open()]
    assert len(trials)==1600 and all(r['word']==r['restored'] for r in trials)
    with tarfile.open(ROOT/'raw-results/supplemental-sources.tar.gz','r:gz') as archive:
        for entry in read(ROOT/'raw-results/supplemental-source-index.json'):
            assert hashlib.sha256(archive.extractfile(entry['entry']).read()).hexdigest()==entry['sha256']
    manifest=read(ROOT/'raw-results/manifest.json')
    for relative,record in manifest['files'].items():
        data=(ROOT/relative).read_bytes()
        if record['mode']=='crlf-to-lf':data=data.replace(b'\r\n',b'\n')
        assert hashlib.sha256(data).hexdigest()==record['sha256'],relative
    print(json.dumps(dict(original_reviews=80,additional_initial_hypotheses=12,extension='H113',
                         per_seed=dict(exhaustive_channel_events=1184,random_propagations=1000),
                         classical_strategies=4096,family_conditions=16,family_random_cases=1600,
                         new_capability_established=False,external_peer_review=False)),flush=True)

if __name__=='__main__':verify()

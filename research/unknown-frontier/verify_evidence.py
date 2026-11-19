"""Verify retained raw experiments independently of their printed summaries."""
import csv,gzip,hashlib,json,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'baseline-implementation'))
from geometry import feasible,grid_feasible
REQUIRED=['discovery-method.md','hypotheses.csv','prior-art-review.md','candidate-destruction-reports.md',
          'selected-hypothesis.md','mathematical-model.md','proof-or-falsification.md','baseline-implementation',
          'prototype','experiment-protocol.md','raw-results','reproducibility.md','independent-review-checklist.md','final-research-report.md']

def main():
    assert all((ROOT/path).exists() for path in REQUIRED)
    rows=list(csv.DictReader((ROOT/'hypotheses.csv').open()))
    assert len(rows)==100 and len({r['id'] for r in rows})==100
    assert all(all(value for value in r.values()) for r in rows)
    freeze=json.loads((ROOT/'raw-results/catalogue-freeze.json').read_text())
    assert hashlib.sha256((ROOT/'hypotheses.csv').read_bytes().replace(b'\r\n',b'\n')).hexdigest()==freeze['canonical_sha256']
    reviews=json.loads((ROOT/'raw-results/prior-art-screen.json').read_text())
    assert len(reviews)==20 and {r['id'] for r in reviews}==set(freeze['shortlisted'])
    counts=[]
    for seed in (2090,2091):
        folder=ROOT/f'raw-results/seed-{seed}';summary=json.loads((folder/'summary.json').read_text())
        records=[json.loads(line) for line in (folder/'admission.jsonl').open()]
        assert len(records)==10733
        for r in records:
            assert r['geometry']==r['certificate']==r['projection']==feasible(r['b'])
        assert all(grid_feasible(r['b'])==r['geometry'] for r in records[:729])
        transformed=[json.loads(line) for line in (folder/'metamorphic.jsonl').open()]
        assert len(transformed)==2000
        assert all(r['expected']==r['certificate']==r['projection']==feasible(r['original'])==feasible(r['transformed']) for r in transformed)
        assert len(json.loads((folder/'mutations.json').read_text()))==8
        assert summary['new_capability_established'] is False and summary['functional_mismatches']==0
        counts.append(dict(seed=seed,base_records=len(records),metamorphic_records=len(transformed)))
    follow=ROOT/'raw-results/follow-on'
    rows_count=naive=anytime=final=0
    from fractions import Fraction
    with gzip.open(follow/'coin-paths.jsonl.gz','rt') as f:
        for line in f:
            row=json.loads(line);assert row['word']==rows_count
            naive+=row['first_naive'] is not None;anytime+=row['first_anytime'] is not None
            final+=Fraction(row['final_p'])<=Fraction(1,20);rows_count+=1
    assert (rows_count,naive,anytime,final)==(65536,5368,16,1394)
    supplement=json.loads((ROOT/'raw-results/certificate-change-supplement.json').read_text())
    assert not feasible(supplement['b'],supplement['old_matrix']) and feasible(supplement['b'],supplement['new_matrix'])
    # Exact original experiment source bytes remain available even when Git
    # normalizes line endings in a fresh checkout. Never extract arbitrary paths.
    with tarfile.open(ROOT/'raw-results/experiment-source-snapshot.tar.gz','r:gz') as snapshot:
        for seed in (2090,2091):
            plan=json.loads((ROOT/f'raw-results/seed-{seed}/plan.json').read_text())
            for path,expected in plan['sources'].items():
                assert hashlib.sha256(snapshot.extractfile(path).read()).hexdigest()==expected,path
    manifest=json.loads((ROOT/'raw-results/evidence-manifest.json').read_text())
    for relative,expected in manifest['files'].items():
        data=(ROOT/relative).read_bytes()
        if expected['mode']=='crlf-to-lf':data=data.replace(b'\r\n',b'\n')
        assert hashlib.sha256(data).hexdigest()==expected['sha256'],relative
    print(json.dumps(dict(hypotheses=100,screened=20,replications=counts,coin_paths=rows_count,source_snapshot_verified=True,
                          new_capability_established=False,external_peer_review=False)),flush=True)

if __name__=='__main__':main()


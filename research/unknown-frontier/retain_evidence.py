"""Retain exact P0 source bytes and hash all committed research evidence."""
import hashlib,io,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
expected={}
for seed in (2090,2091):
    plan=json.loads((ROOT/f'raw-results/seed-{seed}/plan.json').read_text())
    for path,value in plan['sources'].items():
        assert path not in expected or expected[path]==value
        expected[path]=value
archive=ROOT/'raw-results/experiment-source-snapshot.tar.gz'
if archive.exists():
    # Preserve original experiment versions when later documentation or style
    # changes occur. Never replace the frozen snapshot with current sources.
    with tarfile.open(archive,'r:gz') as stream:
        for path,value in expected.items():
            assert hashlib.sha256(stream.extractfile(path).read()).hexdigest()==value,path
else:
    for path,value in expected.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value,('source changed since experiment',path)
    with tarfile.open(archive,'w:gz') as stream:
        for path in sorted(set(expected)|{'hypotheses.csv','raw-results/catalogue-freeze.json'}):
            stream.add(ROOT/path,arcname=path)
compiler=ROOT.parents[1]/'.build-tools/frontier/rustc-version.txt'
(ROOT/'raw-results/compiler.txt').write_bytes(compiler.read_bytes())
manifest=dict(schema_version=2,classification='OBSERVED',claim='No new capability established; retained negative research artifact',
              signatures='none; local checksums are not external attestations',
              files={str(p.relative_to(ROOT)):dict(mode='raw' if p.suffix=='.gz' else 'crlf-to-lf', sha256=hashlib.sha256(p.read_bytes() if p.suffix=='.gz' else p.read_bytes().replace(b'\r\n',b'\n')).hexdigest())
                     for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='evidence-manifest.json'})
(ROOT/'raw-results/evidence-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Original experiment source bytes match every recorded hash; evidence manifest written.')


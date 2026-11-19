"""Retain exact provenance and portable hashes; never rewrite historical trials."""
import hashlib,json,platform,subprocess,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2]

def main():
    pairs=[('original-80-seed-2090',ROOT/'raw-results/original-80-seed-2090/failed-source.py.txt','original-failed.py'),
           ('original-80-fixed-seed-2090',ROOT/'checks_original.py','original-fixed.py'),
           ('other-fields-planned',ROOT/'other_fields.py','other-fields.py'),
           ('family-2090',ROOT/'family.py','family.py')]
    archive=ROOT/'raw-results/supplemental-sources.tar.gz';index=[]
    for folder,source,name in pairs:
        plan=json.loads((ROOT/'raw-results'/folder/'plan.json').read_text())
        index.append(dict(entry=name,sha256=plan['source_sha256'],trial=folder))
    if not archive.exists():
        for (_,source,_),entry in zip(pairs,index):assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['sha256'],str(source)
        with tarfile.open(archive,'w:gz') as stream:
            for _,source,name in pairs:stream.add(source,arcname=name)
    else:
        with tarfile.open(archive,'r:gz') as stream:
            for entry in index:assert hashlib.sha256(stream.extractfile(entry['entry']).read()).hexdigest()==entry['sha256']
    (ROOT/'raw-results/supplemental-source-index.json').write_text(json.dumps(index,indent=2)+'\n')
    compiler=REPO/'.build-tools/frontier-round2/compiler.txt'
    if compiler.exists():(ROOT/'raw-results/compiler.txt').write_bytes(compiler.read_bytes())
    release=REPO/'.build-tools/round2-release-preservation.json'
    if release.exists():
        value=json.loads(release.read_text(encoding='utf-8-sig'))
        assert value['tag_name']=='preview-7-1' and value['id']==450149449
        assets={asset['name']:asset for asset in value['assets']}
        expected=[('fetianOS-0.1.0-x86_64.iso.part001',1992294400,'sha256:e9c1e61471eccc35c37042ea7a0ecc53cc080f3ecbc44eb4a06532b81316f3c3'),
                  ('fetianOS-0.1.0-x86_64.iso.part002',453871616,'sha256:41d222868563d15be4f3382b13ee7529b2b828eed5f32807d4df166a958b1a22')]
        for name,size,digest in expected:assert assets[name]['size']==size and assets[name]['digest']==digest
        value['verification_scope']='Read-only release metadata matches prior part sizes/digests; no ISO bytes downloaded or rebuilt.'
        (ROOT/'raw-results/release-observation.json').write_text(json.dumps(value,indent=2)+'\n')
    environment=dict(kernel=platform.release(),architecture=platform.machine(),python=platform.python_version(),
                     recorded_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                     base_revision='4c8541d658e31068856bfc46ee88917b5c9beddb',
                     integration='none; only the isolated round-2 research tree changes')
    (ROOT/'raw-results/environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    files={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name=='manifest.json':continue
        data=path.read_bytes();mode='raw' if path.suffix=='.gz' else 'crlf-to-lf'
        files[str(path.relative_to(ROOT))]=dict(mode=mode,sha256=hashlib.sha256(data if mode=='raw' else data.replace(b'\r\n',b'\n')).hexdigest())
    (ROOT/'raw-results/manifest.json').write_text(json.dumps(dict(schema_version=1,files=files,attestation='local unsigned checksums only'),indent=2)+'\n')
    print('Exact trial sources, unchanged release metadata and portable evidence hashes retained.')

if __name__=='__main__':main()

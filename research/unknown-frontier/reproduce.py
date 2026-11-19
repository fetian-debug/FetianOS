#!/usr/bin/env python3
"""Build/run the isolated artifacts with a caller-supplied Linux Rust compiler."""
import argparse,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=2090)
    p.add_argument('--rustc',default='rustc');p.add_argument('--follow-on',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    version=subprocess.check_output([a.rustc,'--version','--verbose'],text=True)
    (a.output/'rustc-version.txt').write_text(version)
    with tempfile.TemporaryDirectory(prefix='frontier-build-') as directory:
        binaries=[]
        for source,name in [('prototype/certificates.rs','certificates'),('baseline-implementation/projection.rs','projection')]:
            binary=Path(directory)/name
            subprocess.run([a.rustc,'--edition=2021','-O',str(ROOT/source),'-o',str(binary)],check=True)
            binaries.append(binary)
        subprocess.run([sys.executable,str(ROOT/'run_experiments.py'),'--prototype',str(binaries[0]),'--baseline',str(binaries[1]),
                        '--output',str(a.output/f'seed-{a.seed}'),'--seed',str(a.seed)],check=True)
    if a.follow_on:subprocess.run([sys.executable,str(ROOT/'follow_on.py'),'--output',str(a.output/'follow-on')],check=True)

if __name__=='__main__':main()

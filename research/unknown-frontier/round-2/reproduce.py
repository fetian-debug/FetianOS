#!/usr/bin/env python3
"""Build and rerun all round-2 protocols in fresh directories on Linux."""
import argparse,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--rustc',default='rustc')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'compiler.txt').write_text(subprocess.check_output([a.rustc,'--version','--verbose'],text=True))
    with tempfile.TemporaryDirectory(prefix='frontier-round2-build-') as directory:
        binary=Path(directory)/'metadata'
        subprocess.run([a.rustc,'--edition=2021','-O','-D','warnings',str(ROOT/'prototype/metadata.rs'),'-o',str(binary)],check=True)
        for seed in (2090,2091):
            subprocess.run([sys.executable,str(ROOT/'experiments.py'),'--binary',str(binary),'--output',str(a.output/f'seed-{seed}'),'--seed',str(seed)],check=True)
    subprocess.run([sys.executable,str(ROOT/'checks_original.py'),'--output',str(a.output/'original-80'),'--seed','2090'],check=True)
    subprocess.run([sys.executable,str(ROOT/'other_fields.py'),'--output',str(a.output/'other-fields')],check=True)
    subprocess.run([sys.executable,str(ROOT/'family.py'),'--output',str(a.output/'family'),'--seed','2090'],check=True)

if __name__=='__main__':main()

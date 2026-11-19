#!/usr/bin/env python3
"""Record bounded, local source checks; never install services or publish an ISO."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--phase', choices=('baseline', 'final'), required=True)
    parser.add_argument('--gtk-prefix', type=Path)
    parser.add_argument('--fca-bin-dir', type=Path, help='Use an explicitly staged FCA executable directory for filesystem controls')
    parser.add_argument('--stress-runs', type=int, default=0)
    parser.add_argument('--clean-only', action='store_true', help='Build both Rust crates in fresh temporary target directories')
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('Use a disposable Linux development environment, not the Windows host.')
    if not 0 <= args.stress_runs <= 1000:
        parser.error('stress-runs must be 0..1000')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHON=sys.executable)
    results = []

    def run(name, command, timeout=900, extra_env=None):
        started = time.monotonic()
        log = output / (name + '.log')
        with log.open('w') as stream:
            try:
                child = subprocess.Popen(command, cwd=ROOT, env=dict(env, **(extra_env or {})),
                                         stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = child.wait(timeout=timeout)
                    status = 'passed' if code == 0 else 'failed'
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    code, status = child.returncode, 'timed-out'
            except OSError as error:
                stream.write(str(error) + '\n')
                code, status = None, 'environment-blocked'
        if code != 0 and command[:2] == ['cargo', 'audit'] and 'no such command: `audit`' in log.read_text():
            status = 'environment-blocked'
        results.append(dict(name=name, command=command, status=status, exit_code=code,
                            seconds=round(time.monotonic()-started, 3), log=log.name,
                            log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'{name}: {status}', flush=True)

    inventory = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    (output / 'repository-files.json').write_text(json.dumps(inventory, indent=2) + '\n')
    metadata = dict(phase=args.phase, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    worktree=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
                    kernel=platform.release(), architecture=platform.machine(), python=platform.python_version(),
                    uid=os.getuid(), gid=os.getgid(),
                    toolchain=os.environ.get('RUSTUP_TOOLCHAIN'),
                    tools={tool:shutil.which(tool) for tool in ('cargo', 'rustc', 'systemd-analyze', 'qemu-system-x86_64', 'mkarchiso', 'docker', 'xvfb-run')},
                    scope='Local source/process tests only. No installed FetianOS, graphical login or hardware acceptance inferred.')
    (output / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')
    run('rust-version', ['rustc', '--version', '--verbose'])
    if args.clean_only:
        for name, manifest in (('native', 'Cargo.toml'), ('fca', 'system/fetian-fca/Cargo.toml')):
            with tempfile.TemporaryDirectory(prefix='fetian-clean-build-') as directory:
                for profile in ('debug', 'release'):
                    command = ['cargo', 'build', '--manifest-path', manifest, '--locked', '--offline', '--target-dir', directory]
                    if profile == 'release': command.append('--release')
                    run(name+'-clean-'+profile, command)
        return int(any(r['status'] != 'passed' for r in results))
    for name, manifest in (('native', 'Cargo.toml'), ('fca', 'system/fetian-fca/Cargo.toml')):
        common = ['--manifest-path', manifest]
        run(name+'-fmt', ['cargo', 'fmt', *common, '--', '--check'])
        run(name+'-clippy', ['cargo', 'clippy', *common, '--all-targets', '--locked', '--offline', '--', '-D', 'warnings'])
        run(name+'-tests', ['cargo', 'test', *common, '--locked', '--offline'])
        run(name+'-debug-build', ['cargo', 'build', *common, '--locked', '--offline'])
        run(name+'-release-build', ['cargo', 'build', *common, '--release', '--locked', '--offline'])
        run(name+'-dependency-lock', ['cargo', 'metadata', *common, '--locked', '--offline', '--format-version', '1'])
    for name, lock in (('native', 'Cargo.lock'), ('fca', 'system/fetian-fca/Cargo.lock')):
        run(name+'-vulnerability-audit', ['cargo', 'audit', '--file', lock, '--json'], timeout=120)
    run('python-regressions', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'])
    run('fca-harness-oracles', [sys.executable, '-m', 'unittest', 'discover', '-s', 'system/fetian-fca/validation', '-p', 'test_*.py', '-v'])
    run('profile', ['bash', 'scripts/validate-profile.sh'])
    run('staged-units', [sys.executable, 'scripts/verify-staged.py'])
    run('environment-capabilities', [sys.executable, 'scripts/build-environment.py', '--json'])
    run('fca-stage-executor', ['bash', 'scripts/build-fca.sh', '--release', '--offline'])
    binary_env = dict(FCA_BIN_DIR=str(args.fca_bin_dir.resolve() if args.fca_bin_dir else ROOT / 'system/fetian-fca/target/release'))
    run('fca-process', [sys.executable, 'system/fetian-fca/tests/process_tests.py'], extra_env=binary_env)
    for mode in ('deterministic', 'security'):
        command = [sys.executable, 'system/fetian-fca/validation/lab.py', mode, '--output', str(output / ('fca-'+mode))]
        if mode == 'deterministic': command.append('--include-expiry')
        run('fca-'+mode, command, extra_env=binary_env)
    run('fca-security-boundaries', [sys.executable, 'system/fetian-fca/validation/security.py', '--output', str(output/'fca-boundaries')], extra_env=binary_env)
    run('live-telemetry', [str(ROOT/'target/release/fetian-health-rs'), '--json'])
    if args.stress_runs:
        run('fca-stress', [sys.executable, 'system/fetian-fca/validation/lab.py', 'stress', '--runs', str(args.stress_runs),
                          '--seed', '2090', '--output', str(output / 'fca-stress')], extra_env=binary_env, timeout=2400)
    if args.gtk_prefix:
        prefix = args.gtk_prefix.resolve()
        gtk_env = dict(LD_LIBRARY_PATH=str(prefix/'usr/lib/x86_64-linux-gnu'),
                       GI_TYPELIB_PATH=str(prefix/'usr/lib/x86_64-linux-gnu/girepository-1.0'),
                       XDG_DATA_DIRS=str(prefix/'usr/share')+':/usr/share', FETIAN_GTK_TEST='1',
                       GSK_RENDERER='cairo', GDK_BACKEND='x11', GTK_A11Y='none')
        run('gtk-files', ['dbus-run-session', '--', 'xvfb-run', '-a', sys.executable, 'tests/gtk_files_smoke.py'], extra_env=gtk_env)
    untested = ['ISO build of this branch', 'UEFI boot of this branch (legacy BIOS is not configured)', 'graphical login/lock/logout',
                'physical GPU/network/audio/USB/storage', 'suspend/resume', '24-hour soak',
                'installed-system upgrades/reboot', 'OS idle CPU/RAM, journal and filesystem health']
    if not args.gtk_prefix: untested.append('GTK smoke (no --gtk-prefix supplied; use / for system-installed dependencies)')
    (output/'acceptance.json').write_text(json.dumps(dict(stable=False, untested=untested,
        local_checks_passed=all(r['status']=='passed' for r in results),
        incomplete_checks=[dict(name=r['name'], status=r['status']) for r in results if r['status']!='passed'],
        note='No blanket acceptance. Dependency lock checks are not vulnerability audits.'), indent=2)+'\n')
    return int(any(r['status'] != 'passed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())

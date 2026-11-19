import configparser
import errno
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

if sys.platform == 'linux':
    import fcntl

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preferences = load('stability_preferences', 'apps/fetian-files/preferences.py')
live = load('stability_live', 'system/boot/live_setup.py')
shell = load('stability_shell', 'desktop/hyprland/fetian_shell.py')


@unittest.skipUnless(sys.platform == 'linux', 'Linux process/filesystem semantics')
class StabilityTests(unittest.TestCase):
    def test_preferences_fifo_cannot_hang_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'state.json'
            os.mkfifo(fifo)
            code = 'import sys; sys.path.insert(0, sys.argv[1]); import preferences; print(preferences.load(__import__("pathlib").Path(sys.argv[2])))'
            with subprocess.Popen([sys.executable, '-c', code, str(ROOT/'apps/fetian-files'), str(fifo)], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
                try:
                    output, error = child.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill(); child.communicate()
                    self.fail('FIFO preferences blocked startup instead of returning safe defaults')
            self.assertEqual(child.returncode, 0, error)
            self.assertIn(b'System', output)

    def test_malformed_fields_do_not_discard_valid_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            path.write_text(json.dumps(dict(bookmarks=['sftp://[broken', 'file:///tmp'], tabs=None, theme='Dark')))
            state = preferences.load(path)
            self.assertEqual(state['bookmarks'], ['file:///tmp'])
            self.assertEqual(state['theme'], 'Dark')
            self.assertEqual(state['tabs'], [])

    def test_preferences_interrupted_replace_preserves_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            preferences.save(dict(bookmarks=['file:///tmp'], theme='Dark'), path)
            before = path.read_bytes()
            with patch.object(preferences.os, 'replace', side_effect=OSError(errno.ENOSPC, 'isolated disk-full injection')):
                with self.assertRaises(OSError): preferences.save(dict(theme='Light'), path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).glob('.state-*')), [])

    def test_live_state_fsync_failure_cleans_temporary_and_preserves_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'; path.write_text('previous')
            with patch.object(live.os, 'fsync', side_effect=OSError(errno.ENOSPC, 'isolated fsync failure')):
                with self.assertRaises(OSError): live.write_state(path, 'replacement', os.getuid())
            self.assertEqual(path.read_text(), 'previous')
            self.assertEqual(list(Path(directory).glob('.fetian-*')), [])

    def test_session_lock_is_not_inherited_by_compositor(self):
        scripts = ('system/boot/airootfs/usr/bin/fetian-sway-session', 'desktop/hyprland/bin/fetian-hyprland-session')
        for script in scripts:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); root.chmod(0o755)
                runtime = root/'runtime'; runtime.mkdir(); runtime.chmod(0o777)
                binaries = root/'bin'; binaries.mkdir(); binaries.chmod(0o755)
                compositor = '#!/usr/bin/python3\nimport os,sys\ntry: os.fstat(9)\nexcept OSError: sys.exit(0)\nsys.exit(42)\n'
                for name, text in [('sway', compositor), ('Hyprland', compositor), ('pacman', '#!/bin/sh\necho "hyprland 0.56.2-4"\n'), ('systemctl', '#!/bin/sh\nexit 0\n'), ('dbus-update-activation-environment', '#!/bin/sh\nexit 0\n')]:
                    path = binaries/name; path.write_text(text); path.chmod(0o755)
                def unprivileged():
                    os.setgroups([]); os.setgid(65534); os.setuid(65534)
                env = dict(os.environ, PATH=str(binaries)+':/usr/bin:/bin', XDG_RUNTIME_DIR=str(runtime), HOME=str(root), DBUS_SESSION_BUS_ADDRESS='unix:path=fixture')
                env.pop('SWAYSOCK', None); env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
                result = subprocess.run(['bash', str(ROOT/script)], env=env, capture_output=True, text=True,
                                        preexec_fn=unprivileged if os.geteuid()==0 else None, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr or 'session lock leaked into compositor')
                # The wrapper itself released its ownership after cleanup.
                with (runtime/'fetian-desktop-session.lock').open('r') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Closing the child descriptor must not release the parent's
                # lock while its compositor is still running.
                waiting = '#!/usr/bin/python3\nimport os,pathlib,signal\npathlib.Path(os.environ["XDG_RUNTIME_DIR"],"ready").touch()\nsignal.pause()\n'
                for name in ('sway', 'Hyprland'): (binaries/name).write_text(waiting)
                with subprocess.Popen(['bash', str(ROOT/script)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      preexec_fn=unprivileged if os.geteuid()==0 else None) as session:
                    try:
                        deadline = time.monotonic()+5
                        while not (runtime/'ready').exists() and session.poll() is None and time.monotonic()<deadline:
                            time.sleep(0.01)
                        self.assertTrue((runtime/'ready').exists(), 'fixture compositor did not start')
                        with (runtime/'fetian-desktop-session.lock').open('r') as lock:
                            with self.assertRaises(BlockingIOError): fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        second = subprocess.run(['bash', str(ROOT/script)], env=env, capture_output=True, text=True,
                                                preexec_fn=unprivileged if os.geteuid()==0 else None, timeout=5)
                        self.assertNotEqual(second.returncode, 0)
                        self.assertIn('already running', second.stderr)
                    finally:
                        session.terminate()
                        session.communicate(timeout=5)
                with (runtime/'fetian-desktop-session.lock').open('r') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def shell_result(self, missing=False):
        handlers = {}
        def child(command, **kwargs):
            if missing and command[0]=='nm-applet': raise FileNotFoundError('missing optional network applet')
            return Mock(pid=999999, args=command, poll=Mock(return_value=23 if command[0]=='nm-applet' else None), wait=Mock(return_value=0))
        desktop = SimpleNamespace(selected_profile=lambda:'balanced')
        spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _:None))
        def register(number, handler): handlers[number]=handler
        def stop_after_poll(_): handlers[signal.SIGTERM](signal.SIGTERM, None)
        with patch.dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE='fixture'), patch.object(shell.importlib.util, 'spec_from_file_location', return_value=spec), patch.object(shell.importlib.util, 'module_from_spec', return_value=desktop), patch.object(shell.subprocess, 'Popen', side_effect=child), patch.object(shell.signal, 'signal', side_effect=register), patch.object(shell.time, 'sleep', side_effect=stop_after_poll), patch.object(shell.os, 'killpg'):
            return shell.main()

    def test_optional_shell_child_exit_does_not_stop_panel(self):
        self.assertEqual(self.shell_result(), 0)

    def test_missing_optional_shell_child_does_not_stop_panel(self):
        self.assertEqual(self.shell_result(missing=True), 0)

    def test_required_panel_exit_remains_a_visible_failure(self):
        with patch.object(shell.subprocess, 'Popen', side_effect=FileNotFoundError('missing panel')):
            self.assertEqual(self.shell_result_required_failure(), 1)

    def shell_result_required_failure(self):
        desktop = SimpleNamespace(selected_profile=lambda:'balanced')
        spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _:None))
        with patch.dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE='fixture'), patch.object(shell.importlib.util, 'spec_from_file_location', return_value=spec), patch.object(shell.importlib.util, 'module_from_spec', return_value=desktop), patch.object(shell.signal, 'signal'):
            return shell.main()

    def test_optional_restart_policy_has_an_effective_explicit_limit(self):
        paths = ('system/boot/airootfs/usr/lib/systemd/user/fetian-bluetooth-agent.service',
                 'system/boot/airootfs/usr/lib/systemd/user/fetian-sway-idle.service',
                 'desktop/hyprland/airootfs/usr/lib/systemd/user/fetian-idle.service',
                 'desktop/hyprland/airootfs/usr/lib/systemd/user/fetian-shell.service')
        for relative in paths:
            with self.subTest(unit=relative):
                unit = configparser.ConfigParser(interpolation=None); unit.read(ROOT/relative)
                interval = unit.getint('Unit', 'StartLimitIntervalSec', fallback=0)
                burst = unit.getint('Unit', 'StartLimitBurst', fallback=0)
                delay = unit.getint('Service', 'RestartSec')
                self.assertGreater(burst, 0)
                self.assertGreater(interval, (burst+1)*delay)
                self.assertEqual(unit.get('Service', 'Restart'), 'on-failure')
                self.assertNotIn('Requires=', (ROOT/relative).read_text())


if __name__=='__main__': unittest.main(verbosity=2)

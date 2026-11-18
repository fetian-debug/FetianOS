"""Exercise update/terminal action contracts without importing a graphical session."""
import ast
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def method(name, globals):
    tree = ast.parse((ROOT / "apps/fetian-control-center/fetian_control_center.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ControlCenter")
    function = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = dict(globals)
    exec(compile(ast.Module(body=[function], type_ignores=[]), "control-center-action", "exec"), namespace)
    return namespace[name]


class Dialog:
    def __init__(self, **kwargs): pass
    def add_response(self, *args): pass
    def present(self): pass


class ControlCenterActionTests(unittest.TestCase):
    def test_check_button_only_dispatches_read_only_helper(self):
        calls = []
        application = SimpleNamespace(window=object(), background=lambda *args, **kwargs: calls.append((args, kwargs)))
        check = method("check_updates", {"Adw": SimpleNamespace(MessageDialog=Dialog), "os": os, "Path": Path, "sys": sys})
        with patch.dict(os.environ, {"FETIAN_DEV_ROOT": str(ROOT)}):
            check(application, None)
        command = calls[0][0][0]
        self.assertEqual(command[-1], "check-updates")
        self.assertNotIn("pkexec", command)
        self.assertNotIn("pacman", command)
        self.assertEqual(calls[0][1]["timeout"], 125)

    def test_update_install_keeps_terminal_attached_and_empty_terminal_is_valid(self):
        calls = []
        terminal = method("terminal", {"shutil": SimpleNamespace(which=lambda name: name == "foot")})
        application = SimpleNamespace(launch=calls.append)
        terminal(application, ["fetian-update", "install"])
        terminal(application, [])
        self.assertEqual(calls, [["foot", "-e", "fetian-update", "install"], ["foot"]])

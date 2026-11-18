import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetian_daily", ROOT / "apps/fetian-desktop/fetian_daily.py")
daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily)


class UpdateTests(unittest.TestCase):
    def result(self, code, stdout="", stderr=""):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, code, stdout, stderr)
        return run, calls

    def test_check_never_runs_a_privileged_package_transaction(self):
        run, calls = self.result(0, "firefox 1 -> 2\n")
        self.assertIn("firefox", daily.check_updates(run))
        self.assertEqual(calls, [["checkupdates"]])

    def test_no_updates_is_a_successful_distinct_result(self):
        run, _ = self.result(2)
        self.assertEqual(daily.check_updates(run), "No updates available.")

    def test_network_or_repository_failure_is_not_no_updates(self):
        run, _ = self.result(1, stderr="repository unreachable")
        with self.assertRaisesRegex(RuntimeError, "repository unreachable"):
            daily.check_updates(run)


class BatteryTests(unittest.TestCase):
    def battery(self, level, status="Discharging"):
        return [{"name": "BAT0", "capacity_percent": level, "status": status}]

    def test_thresholds_notify_once_then_escalate(self):
        alerts, state = daily.battery_decision(self.battery(14), {})
        self.assertEqual(alerts, [("BAT0", 14, "normal")])
        alerts, state = daily.battery_decision(self.battery(10), state)
        self.assertEqual(alerts, [])
        alerts, state = daily.battery_decision(self.battery(5), state)
        self.assertEqual(alerts, [("BAT0", 5, "critical")])
        self.assertEqual(daily.battery_decision(self.battery(4), state)[0], [])

    def test_charging_and_recovery_reset_notifications(self):
        for batteries in (self.battery(14, "Charging"), self.battery(25)):
            alerts, state = daily.battery_decision(batteries, {"BAT0": 15})
            self.assertEqual((alerts, state), ([], {}))

    def test_invalid_and_missing_sensors_never_become_zero(self):
        for level in (None, -1, 101, "5", True):
            self.assertEqual(daily.battery_decision(self.battery(level), {}), ([], {}))
        self.assertEqual(daily.battery_decision(None, {}), ([], {}))

    def test_corrupt_old_state_does_not_break_current_warning(self):
        self.assertEqual(daily.battery_decision(self.battery(5), {"BAT0": "corrupt"})[0], [("BAT0", 5, "critical")])

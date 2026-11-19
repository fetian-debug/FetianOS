"""Independent checks for the experiment oracle and evidence format."""
import json
from pathlib import Path
import tempfile
import unittest
from common import atomic_json, checkpoint_oracle, redact
from lab import Config, generated
from performance import distribution


class EvidenceTests(unittest.TestCase):
    def test_seed_reproduces_fault_configuration(self):
        self.assertEqual(generated(2090), generated(2090))
        for seed in range(1000):
            generated(seed).validate()

    def test_invalid_barrier_cannot_claim_a_fault_window(self):
        with self.assertRaises(AssertionError):
            Config('broker-before-commit', 1, items=64, chunk=32, barrier=2).validate()

    def test_oracle_rejects_corrupt_sum_and_cursor(self):
        state = dict(schema_version=1, next_input_position=16, last_committed_chunk=1, accumulated_result=120)
        checkpoint_oracle(dict(continuation=state), list(range(32)), 16)
        for changes in (dict(accumulated_result=121), dict(next_input_position=17), dict(last_committed_chunk=2)):
            with self.assertRaises(AssertionError):
                checkpoint_oracle(dict(continuation=dict(state, **changes)), list(range(32)), 16)

    def test_empty_distribution_does_not_invent_a_measurement(self):
        self.assertEqual(distribution([]), dict(samples=0, measured=False))
        measured = distribution(range(1, 101))
        self.assertEqual([measured[key] for key in ('p50', 'p95', 'p99', 'minimum', 'maximum')], [50, 95, 99, 1, 100])

    def test_redaction_preserves_epoch_without_usable_lease(self):
        value = redact(dict(credential=dict(lease_id='secret', epoch=3)))
        self.assertEqual(value['credential']['epoch'], 3)
        self.assertTrue(value['credential']['lease_id'].startswith('sha256:'))
        self.assertNotIn('secret', json.dumps(value))

    def test_evidence_is_valid_json_after_atomic_write(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'report.json'
            atomic_json(target, dict(classification='safely_detected_unrecoverable', recovered=False))
            self.assertFalse(json.loads(target.read_text())['recovered'])
            self.assertFalse(target.with_name('report.json.writing').exists())


if __name__ == '__main__':
    unittest.main()

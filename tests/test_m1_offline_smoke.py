"""Isolated M1 migration-smoke assertions. Not Production F tests."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from scripts.m1_offline_smoke import SOURCE_REL, PIN_SHA256, run_smoke

ROOT = Path(__file__).resolve().parent.parent

class M1OfflineSmoke(unittest.TestCase):
    def test_01_pinned_original_self_test(self):
        got = run_smoke(ROOT)
        self.assertEqual(got['result'], 'PASS_CLOUD_SMOKE_ONLY')
        self.assertTrue(got['source_self_test_executed'])
        self.assertFalse(got['production_db_binding_attested'])
        self.assertFalse(got['production_cp_sat_executed'])
        self.assertFalse(got['public_release_approved'])

    def test_02_modified_bytes_fail_closed_before_execution(self):
        with tempfile.TemporaryDirectory(prefix='wequip_m1_negative_') as d:
            dst = Path(d) / SOURCE_REL
            dst.parent.mkdir(parents=True)
            original = (ROOT / SOURCE_REL).read_bytes()
            # Same size, different SHA: proves hash check is not size-only.
            mutated = bytearray(original)
            mutated[0] ^= 1
            dst.write_bytes(mutated)
            got = run_smoke(Path(d))
            self.assertEqual(got['result'], 'FAIL_CLOSED_SOURCE_SHA_MISMATCH')
            self.assertFalse(got['source_self_test_executed'])

    def test_03_missing_original_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='wequip_m1_negative_') as d:
            got = run_smoke(Path(d))
            self.assertEqual(got['result'], 'FAIL_CLOSED_SOURCE_MISSING')
            self.assertFalse(got['source_self_test_executed'])

    def test_04_receipt_contains_no_machine_paths_or_private_data(self):
        got = run_smoke(ROOT)
        text = json.dumps(got, sort_keys=True)
        self.assertNotIn(str(ROOT), text)
        self.assertNotIn('\\\\', text)
        self.assertNotIn('C:\\', text)
        self.assertNotIn('@', text)
        self.assertNotIn('PRIVATE_REVIEW_ONLY_P0', text)
        self.assertEqual(set(got), {
            'schema','version','project_owner','migration_scope','product_state',
            'product_gate','source_name','expected_source_sha256','result',
            'source_self_test_executed','production_db_binding_attested',
            'production_cp_sat_executed','public_release_approved','network_required',
        })

    def test_05_pinned_original_bytes(self):
        raw = (ROOT / SOURCE_REL).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), PIN_SHA256)
        self.assertEqual(len(raw), 25851)

    def test_06_negative_cli_status(self):
        with tempfile.TemporaryDirectory(prefix='wequip_m1_negative_') as d:
            cp = subprocess.run([
                sys.executable,'-B',str(ROOT / 'scripts/m1_offline_smoke.py'),
                '--root',str(d),
            ],capture_output=True,text=True,check=False,timeout=15)
            self.assertEqual(cp.returncode, 2)
            self.assertEqual(json.loads(cp.stdout)['result'],'FAIL_CLOSED_SOURCE_MISSING')

if __name__ == '__main__':
    unittest.main()

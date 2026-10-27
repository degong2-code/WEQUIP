#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M1 private/cloud candidate offline smoke. No production/DB authority."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

SOURCE_REL = Path('source/Omnium_Expected_Secondary_Provider_v2.py')
PIN_SHA256 = '24baafbdc895fc7b39515ca131be3e65c1077b094cc6c6216c4d203190a44f37'
PIN_SIZE = 25851
PASS_MARKER = 'OMNIUM_EXPECTED_SECONDARY_PROVIDER_V2_SELF_TEST_PASS'


def _receipt(result: str, source_executed: bool = False) -> dict:
    return {
        'schema': 'WEQUIPM1PrivateOfflineSmokeReceipt',
        'version': '1.0',
        'project_owner': 'A_MAIN',
        'migration_scope': 'CLOUD_SMOKE_ONLY',
        'product_state': 'PAUSED',
        'product_gate': 'BROADER_PAIR_CONDITIONED_PRODUCTION_F_INTEGRATION',
        'source_name': SOURCE_REL.name,
        'expected_source_sha256': PIN_SHA256,
        'result': result,
        'source_self_test_executed': bool(source_executed),
        'production_db_binding_attested': False,
        'production_cp_sat_executed': False,
        'public_release_approved': False,
        'network_required': False,
    }


def run_smoke(root: Path) -> dict:
    root = Path(root).resolve()
    src = root / SOURCE_REL
    if src.is_symlink():
        return _receipt('FAIL_CLOSED_SOURCE_SYMLINK')
    try:
        st = src.lstat()
    except OSError:
        return _receipt('FAIL_CLOSED_SOURCE_MISSING')
    if not stat.S_ISREG(st.st_mode):
        return _receipt('FAIL_CLOSED_SOURCE_NOT_REGULAR')
    if st.st_size != PIN_SIZE:
        return _receipt('FAIL_CLOSED_SOURCE_SIZE_MISMATCH')
    try:
        raw = src.read_bytes()
    except OSError:
        return _receipt('FAIL_CLOSED_SOURCE_READ_ERROR')
    if hashlib.sha256(raw).hexdigest() != PIN_SHA256:
        return _receipt('FAIL_CLOSED_SOURCE_SHA_MISMATCH')
    try:
        ast.parse(raw.decode('utf-8-sig'), filename=SOURCE_REL.name)
    except (SyntaxError, UnicodeError):
        return _receipt('FAIL_CLOSED_SOURCE_SYNTAX')
    # Exact byte-pinned and previously inspected source only.
    # -I ignores PYTHONPATH/user site, -B prevents pycache writes.
    # The source's own synthetic self-test uses stdlib only.
    env = {
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONNOUSERSITE': '1',
        'PYTHONDONTWRITEBYTECODE': '1',
    }
    if os.name == 'nt':
        for name in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP'):
            if name in os.environ:
                env[name] = os.environ[name]
    try:
        with tempfile.TemporaryDirectory(prefix='wequip_m1_offline_') as tmp:
            cp = subprocess.run(
                [sys.executable, '-I', '-B', str(src), '--self-test'],
                cwd=tmp, env=env, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=15, check=False,
            )
    except subprocess.TimeoutExpired:
        return _receipt('FAIL_CLOSED_SELF_TEST_TIMEOUT', True)
    except OSError:
        return _receipt('FAIL_CLOSED_SELF_TEST_PROCESS', False)
    # Do not forward untrusted text/tracebacks or raw paths to CI logs.
    if cp.returncode != 0:
        return _receipt('FAIL_CLOSED_SELF_TEST_EXIT', True)
    if cp.stderr.strip():
        return _receipt('FAIL_CLOSED_SELF_TEST_STDERR', True)
    if cp.stdout.strip() != PASS_MARKER:
        return _receipt('FAIL_CLOSED_SELF_TEST_OUTPUT', True)
    return _receipt('PASS_CLOUD_SMOKE_ONLY', True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Read-only WEQUIP M1 private offline smoke')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    receipt = run_smoke(args.root)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt['result'] == 'PASS_CLOUD_SMOKE_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())

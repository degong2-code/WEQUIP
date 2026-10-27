"""Offline synthetic boundary tests; NOT a Production F or Solver execution."""
import copy
import hashlib
import importlib.util
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "Candidate_Basis_Augmentation_Model_v1.py"
EXPECTED_SHA256 = "3c74c771cc0c21580ae561ec159765a388931462c169dd161f79eb64264536c8"


def _load_exact_source():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise AssertionError("Original source SHA mismatch; fail-closed")
    spec = importlib.util.spec_from_file_location("_wequip_m2_basis_isolated", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("Original source import unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BasisBoundarySynthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basis = _load_exact_source()

    def setUp(self):
        self.catalog = {
            "gem_rules_fingerprint": "synthetic-gem-policy",
            "flask_rules_fingerprint": "synthetic-flask-policy",
            "d_binding_fingerprint": "synthetic-D-binding",
        }
        self.mode = "OMNIUM_NEUTRAL_REFERENCE"
        self.semantics = {
            "target_mode": self.mode,
            "physical_static_lane": "DIRECT_COMPONENT_AUTHORITY",
            "enchant_policy": "ENCHANT_NEUTRAL_TARGET",
            "item_secondary_effect_policy_identity": "synthetic-effect-policy-id",
            "item_secondary_effect_policy_fingerprint": "synthetic-effect-policy-sha",
            "gem_socket_policy_identity": {
                "gem_rules_fingerprint": self.catalog["gem_rules_fingerprint"],
                "D_binding_fingerprint": self.catalog["d_binding_fingerprint"],
            },
            "flask_policy_identity": {
                "flask_rules_fingerprint": self.catalog["flask_rules_fingerprint"],
                "rating": 165,
            },
            "included_components": [
                "PHYSICAL_STATIC",
                "ACTUAL_NORMAL_GEMS",
                "EXACT_SECONDARY_FLASK",
                "GENERALIZED_ITEM_SECONDARY_EFFECT_EXPECTATION",
            ],
            "omnium_policy_fingerprint": "EXCLUDED_FROM_NEUTRAL",
        }

    def check_semantics(self, **overrides):
        args = {
            "target_mode": self.mode,
            "basis_semantics": self.semantics,
            "target_stat_basis_fingerprint": self.basis.canonical_hash(self.semantics),
            "d_catalog": self.catalog,
            "expected_effect_policy_identity": "synthetic-effect-policy-id",
            "expected_effect_policy_fingerprint": "synthetic-effect-policy-sha",
            "expected_omnium_policy_fingerprint": "synthetic-omnium-policy-sha",
        }
        args.update(overrides)
        return self.basis.validate_basis_semantics(**args)

    def test_01_source_byte_sha(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), EXPECTED_SHA256)

    def test_02_neutral_basis_exact_match(self):
        self.assertEqual(self.check_semantics(), self.basis.canonical_hash(self.semantics))

    def test_03_effective_basis_requires_matching_omnium(self):
        effective = copy.deepcopy(self.semantics)
        effective["target_mode"] = "OBSERVED_EFFECTIVE_PRODUCTION"
        effective["included_components"].append("OBSERVED_OMNIUM_EXPECTED_SECONDARY")
        effective["omnium_policy_fingerprint"] = "synthetic-omnium-policy-sha"
        self.assertEqual(
            self.check_semantics(target_mode="OBSERVED_EFFECTIVE_PRODUCTION", basis_semantics=effective,
                target_stat_basis_fingerprint=self.basis.canonical_hash(effective)),
            self.basis.canonical_hash(effective)
        )

    def test_04_stale_basis_fingerprint_fails(self):
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "fingerprint mismatch"):
            self.check_semantics(target_stat_basis_fingerprint="not-current")

    def test_05_neutral_rejects_observed_omnium_component(self):
        x = copy.deepcopy(self.semantics)
        x["included_components"].append("OBSERVED_OMNIUM_EXPECTED_SECONDARY")
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "neutral mode must exclude Omnium"):
            self.check_semantics(basis_semantics=x, target_stat_basis_fingerprint=self.basis.canonical_hash(x))

    def test_06_effective_rejects_missing_omnium_component(self):
        x = copy.deepcopy(self.semantics)
        x["target_mode"] = "OBSERVED_EFFECTIVE_PRODUCTION"
        x["omnium_policy_fingerprint"] = "synthetic-omnium-policy-sha"
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "must include Omnium grammar"):
            self.check_semantics(target_mode="OBSERVED_EFFECTIVE_PRODUCTION", basis_semantics=x,
                target_stat_basis_fingerprint=self.basis.canonical_hash(x))

    def test_07_stale_d_binding_fingerprint_fails(self):
        catalog = dict(self.catalog, d_binding_fingerprint="different-binding")
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "D binding fingerprint mismatch"):
            self.check_semantics(d_catalog=catalog)

    def test_08_wrong_effect_policy_fails(self):
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "policy fingerprint mismatch"):
            self.check_semantics(expected_effect_policy_fingerprint="different-effect")

    def test_09_unsupported_mode_fails(self):
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "unsupported target mode"):
            self.check_semantics(target_mode="NOT_AN_APPROVED_MODE")

    def test_10_incomplete_candidate_basis_grammar_fails(self):
        x = copy.deepcopy(self.semantics)
        x["included_components"].remove("GENERALIZED_ITEM_SECONDARY_EFFECT_EXPECTATION")
        with self.assertRaisesRegex(self.basis.CandidateBasisAugmentationError, "component grammar incomplete"):
            self.check_semantics(basis_semantics=x, target_stat_basis_fingerprint=self.basis.canonical_hash(x))


if __name__ == "__main__":
    unittest.main()

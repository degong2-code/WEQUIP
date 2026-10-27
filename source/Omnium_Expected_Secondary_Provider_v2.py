#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WEQUIP — Omnium Expected Secondary Provider v2

Research-branch thin provider for scenario/context × Core Omnium expected-secondary
semantics. This module does not score combat DPS and does not modify Solver semantics.

Production-facing rules:
- target witnesses remain witness-specific;
- candidate branches come only from APPROVED_FOR_TARGET_OPTIMIZATION entries;
- Row4 selects the secondary axis only;
- unknown/unapproved/stale context fails closed;
- no universal Core fixed vector fallback;
- no SimC/WCL averaging;
- no ItemVariant static-stat mutation.

The provider consumes a machine-readable v2 contract. It intentionally does not
hard-code "16 total / 8 per scenario" or "exactly 30 witnesses per scenario".
"""

from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "WEQUIPOmniumExpectedSecondaryProvider"
VERSION = "2.0"
CONTRACT_SCHEMA = "WEQUIPOmniumScenarioContextExpectationContract"
CONTRACT_VERSION = "2.0"

SECONDARY_KEYS = ("crit", "haste", "mastery", "vers")
ROW4_STATS = ("CRIT", "HASTE", "MASTERY", "VERS")
APPROVED = "APPROVED_FOR_TARGET_OPTIMIZATION"
ALLOWED_APPROVAL = {
    "OBSERVED_UNREVIEWED",
    "REVIEW_REQUIRED",
    APPROVED,
    "REJECTED",
}

class OmniumProviderV2Error(RuntimeError):
    pass

def canonical_hash(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _finite_nonnegative(value: Any, label: str) -> float:
    try:
        number = float(value)
    except Exception as exc:
        raise OmniumProviderV2Error(f"{label} must be numeric") from exc
    if not math.isfinite(number) or number < 0:
        raise OmniumProviderV2Error(f"{label} must be finite/non-negative")
    return number

def _norm_core(value: Any) -> str:
    core = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if not core:
        raise OmniumProviderV2Error("Core must be non-empty")
    return core

def _norm_row4(value: Any) -> str:
    stat = str(value or "").strip().upper()
    if stat not in ROW4_STATS:
        raise OmniumProviderV2Error(f"invalid Row4 stat: {value!r}")
    return stat

def _identity(name: Any, report: Any, fight: Any) -> tuple[str, str, int]:
    n = str(name or "").strip()
    r = str(report or "").strip()
    if not n or not r:
        raise OmniumProviderV2Error("incomplete witness identity")
    try:
        f = int(fight)
    except Exception as exc:
        raise OmniumProviderV2Error("fight_id must be integer") from exc
    return (n.casefold(), r, f)

def _vector(value: Any, label: str) -> dict[str, float]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise OmniumProviderV2Error(f"{label} must be dict")
    unexpected = sorted(set(value) - set(SECONDARY_KEYS))
    if unexpected:
        raise OmniumProviderV2Error(f"{label} unsupported keys: {unexpected}")
    out = {}
    for key in SECONDARY_KEYS:
        out[key] = _finite_nonnegative(value.get(key, 0) or 0, f"{label}.{key}")
    return out

def _policy_core(payload: dict[str, Any]) -> dict[str, Any]:
    p = deepcopy(payload)
    p.pop("policy_fingerprint", None)
    return p

def _context_core(row: dict[str, Any]) -> dict[str, Any]:
    c = deepcopy(row.get("context") or {})
    return c

def _entry_core(row: dict[str, Any]) -> dict[str, Any]:
    keep = {
        "scenario_id": row.get("scenario_id"),
        "omnium_context_fingerprint": row.get("omnium_context_fingerprint"),
        "core": _norm_core(row.get("core")),
        "expectation_method": row.get("expectation_method"),
        "expected_mean_active_stack": _finite_nonnegative(
            row.get("expected_mean_active_stack"),
            "expected_mean_active_stack",
        ),
        "rating_per_application": _finite_nonnegative(
            row.get("rating_per_application"),
            "rating_per_application",
        ),
        "expected_secondary_rating": _finite_nonnegative(
            row.get("expected_secondary_rating"),
            "expected_secondary_rating",
        ),
        "witness_count": int(row.get("witness_count") or 0),
        "witness_identity_fingerprint": row.get("witness_identity_fingerprint"),
        "evidence_artifact_fingerprints":
            deepcopy(row.get("evidence_artifact_fingerprints") or {}),
        "confidence_class": row.get("confidence_class"),
        "approval_status": row.get("approval_status"),
        "provider_policy_fingerprint": row.get("provider_policy_fingerprint"),
    }
    return keep

def load_contract(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    validate_contract(payload)
    return payload

def validate_contract(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise OmniumProviderV2Error("contract must be JSON object")
    if payload.get("schema") != CONTRACT_SCHEMA:
        raise OmniumProviderV2Error("wrong v2 contract schema")
    if payload.get("version") != CONTRACT_VERSION:
        raise OmniumProviderV2Error("wrong v2 contract version")

    policy = payload.get("provider_policy")
    if not isinstance(policy, dict):
        raise OmniumProviderV2Error("provider_policy missing")
    expected_policy_fp = canonical_hash(_policy_core(policy))
    if str(policy.get("policy_fingerprint") or "") != expected_policy_fp:
        raise OmniumProviderV2Error("provider_policy fingerprint mismatch")

    contexts = payload.get("scenario_contexts")
    if not isinstance(contexts, dict) or not contexts:
        raise OmniumProviderV2Error("scenario_contexts must be non-empty dict")

    context_fps = {}
    for scenario_id, row in contexts.items():
        if not isinstance(row, dict):
            raise OmniumProviderV2Error(f"{scenario_id}: context row must be dict")
        declared = str(row.get("omnium_context_fingerprint") or "")
        calculated = canonical_hash(_context_core(row))
        if declared != calculated:
            raise OmniumProviderV2Error(
                f"{scenario_id}: omnium_context_fingerprint mismatch"
            )
        context_fps[str(scenario_id)] = declared

    targets = payload.get("target_witness_contract")
    if not isinstance(targets, dict):
        raise OmniumProviderV2Error("target_witness_contract missing")

    for scenario_id, scenario in targets.items():
        if scenario_id not in contexts:
            raise OmniumProviderV2Error(
                f"{scenario_id}: target scenario missing context"
            )
        if not isinstance(scenario, dict):
            raise OmniumProviderV2Error(f"{scenario_id}: target row must be dict")
        boundary = int(scenario.get("selected_rank_boundary") or 0)
        witnesses = scenario.get("witnesses")
        if boundary <= 0:
            raise OmniumProviderV2Error(
                f"{scenario_id}: selected_rank_boundary must be positive"
            )
        if not isinstance(witnesses, list):
            raise OmniumProviderV2Error(f"{scenario_id}: witnesses must be list")
        valid_n = int(scenario.get("valid_witness_count") or 0)
        if valid_n != len(witnesses):
            raise OmniumProviderV2Error(
                f"{scenario_id}: valid_witness_count mismatch"
            )
        if valid_n > boundary:
            raise OmniumProviderV2Error(
                f"{scenario_id}: valid N exceeds selected rank boundary"
            )

        seen = set()
        fp_rows = []
        for w in witnesses:
            if not isinstance(w, dict):
                raise OmniumProviderV2Error("target witness must be dict")
            ident = _identity(
                w.get("character_name"),
                w.get("report_code"),
                w.get("fight_id"),
            )
            if ident in seen:
                raise OmniumProviderV2Error(
                    f"{scenario_id}: duplicate witness {ident}"
                )
            seen.add(ident)
            stat = _norm_row4(w.get("row4_stat"))
            vec = _vector(w.get("vector"), "target witness vector")
            positive = [k for k, v in vec.items() if v > 0]
            total_rating = sum(vec.values())
            if total_rating > 0 and positive != [stat.lower()]:
                raise OmniumProviderV2Error(
                    f"{scenario_id}: witness Row4/vector axis mismatch"
                )
            if total_rating == 0 and positive:
                raise OmniumProviderV2Error(
                    f"{scenario_id}: zero-rating witness has positive vector"
                )
            declared_rating = w.get("effective_average_secondary_rating")
            if declared_rating is not None:
                declared_rating = _finite_nonnegative(
                    declared_rating,
                    f"{scenario_id}: witness effective_average_secondary_rating",
                )
                if abs(declared_rating - total_rating) > 1e-9:
                    raise OmniumProviderV2Error(
                        f"{scenario_id}: witness rating/vector mismatch"
                    )
            fp_rows.append({
                "identity": ident,
                "core": _norm_core(w.get("core")),
                "row4_stat": stat,
                "vector": vec,
                "mean_active_stack": w.get("mean_active_stack"),
                "timeline_provenance": w.get("timeline_provenance"),
            })
        expected_witness_fp = canonical_hash(fp_rows)
        if str(scenario.get("witness_set_fingerprint") or "") != expected_witness_fp:
            raise OmniumProviderV2Error(
                f"{scenario_id}: witness_set_fingerprint mismatch"
            )

    entries = payload.get("candidate_context_entries")
    if not isinstance(entries, list):
        raise OmniumProviderV2Error("candidate_context_entries must be list")

    seen_entries = set()
    for row in entries:
        if not isinstance(row, dict):
            raise OmniumProviderV2Error("candidate entry must be dict")
        scenario_id = str(row.get("scenario_id") or "").strip()
        core = _norm_core(row.get("core"))
        if scenario_id not in contexts:
            raise OmniumProviderV2Error(
                f"{scenario_id}: candidate entry missing context"
            )
        if row.get("omnium_context_fingerprint") != context_fps[scenario_id]:
            raise OmniumProviderV2Error(
                f"{scenario_id}/{core}: context fingerprint mismatch"
            )
        key = (scenario_id, core)
        if key in seen_entries:
            raise OmniumProviderV2Error(
                f"duplicate candidate context/Core entry: {key}"
            )
        seen_entries.add(key)

        approval = str(row.get("approval_status") or "")
        if approval not in ALLOWED_APPROVAL:
            raise OmniumProviderV2Error(
                f"{scenario_id}/{core}: invalid approval_status {approval!r}"
            )
        if row.get("provider_policy_fingerprint") != policy["policy_fingerprint"]:
            raise OmniumProviderV2Error(
                f"{scenario_id}/{core}: provider policy fingerprint mismatch"
            )

        mean_stack = _finite_nonnegative(
            row.get("expected_mean_active_stack"),
            f"{scenario_id}/{core}.expected_mean_active_stack",
        )
        rating = _finite_nonnegative(
            row.get("rating_per_application"),
            f"{scenario_id}/{core}.rating_per_application",
        )
        expected = _finite_nonnegative(
            row.get("expected_secondary_rating"),
            f"{scenario_id}/{core}.expected_secondary_rating",
        )
        if abs(mean_stack * rating - expected) > 1e-9:
            raise OmniumProviderV2Error(
                f"{scenario_id}/{core}: expected-secondary invariant mismatch"
            )
        if int(row.get("witness_count") or 0) < 0:
            raise OmniumProviderV2Error(
                f"{scenario_id}/{core}: witness_count invalid"
            )

        entry_core = _entry_core(row)
        expected_entry_fp = canonical_hash(entry_core)
        if str(row.get("provider_entry_fingerprint") or "") != expected_entry_fp:
            raise OmniumProviderV2Error(
                f"{scenario_id}/{core}: provider entry fingerprint mismatch"
            )

class OmniumExpectedSecondaryProviderV2:
    def __init__(self, contract: dict[str, Any], *, source_path: Path | None = None):
        validate_contract(contract)
        self._contract = deepcopy(contract)
        self.source_path = Path(source_path).resolve() if source_path else None
        self._policy = deepcopy(self._contract["provider_policy"])
        self._contexts = deepcopy(self._contract["scenario_contexts"])
        self._entries = {}
        for row in self._contract["candidate_context_entries"]:
            key = (
                str(row["scenario_id"]),
                _norm_core(row["core"]),
            )
            self._entries[key] = deepcopy(row)

    @classmethod
    def from_path(cls, path: Path) -> "OmniumExpectedSecondaryProviderV2":
        return cls(load_contract(path), source_path=path)

    def provider_policy_fingerprint(self) -> str:
        return str(self._policy["policy_fingerprint"])

    def scenario_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._contexts))

    def scenario_context(self, scenario_id: str) -> dict[str, Any]:
        row = self._contexts.get(str(scenario_id))
        if row is None:
            raise OmniumProviderV2Error(f"unknown scenario context: {scenario_id}")
        return deepcopy(row)

    def target_scenario_metadata(self, scenario_id: str) -> dict[str, Any]:
        row = (self._contract.get("target_witness_contract") or {}).get(
            str(scenario_id)
        )
        if not isinstance(row, dict):
            raise OmniumProviderV2Error(f"unknown target scenario: {scenario_id}")
        return {
            "selected_rank_boundary": int(row["selected_rank_boundary"]),
            "valid_witness_count": int(row["valid_witness_count"]),
            "witness_set_fingerprint": str(row["witness_set_fingerprint"]),
            "provider_policy_fingerprint": self.provider_policy_fingerprint(),
            "omnium_context_fingerprint":
                self.scenario_context(scenario_id)["omnium_context_fingerprint"],
        }

    def target_witness_vectors(
        self,
        scenario_id: str,
    ) -> dict[tuple[str, str, int], dict[str, Any]]:
        scenario = (self._contract.get("target_witness_contract") or {}).get(
            str(scenario_id)
        )
        if not isinstance(scenario, dict):
            raise OmniumProviderV2Error(f"unknown target scenario: {scenario_id}")

        out = {}
        for w in scenario.get("witnesses") or []:
            ident = _identity(
                w.get("character_name"),
                w.get("report_code"),
                w.get("fight_id"),
            )
            out[ident] = {
                "identity": {
                    "character_name": w.get("character_name"),
                    "report_code": w.get("report_code"),
                    "fight_id": int(w.get("fight_id")),
                },
                "core": _norm_core(w.get("core")),
                "row4_stat": _norm_row4(w.get("row4_stat")),
                "vector": _vector(w.get("vector"), "target witness vector"),
                "mean_active_stack": w.get("mean_active_stack"),
                "effective_average_secondary_rating":
                    w.get("effective_average_secondary_rating"),
                "timeline_provenance": w.get("timeline_provenance"),
                "source": w.get("source") or "CURRENT_SELECTED_RANK_BOUNDARY",
            }
        if len(out) != int(scenario["valid_witness_count"]):
            raise OmniumProviderV2Error(
                f"{scenario_id}: target witness map count mismatch"
            )
        return out

    def entry(
        self,
        scenario_id: str,
        core: str,
        *,
        context_fingerprint: str | None = None,
        require_approved: bool = True,
    ) -> dict[str, Any]:
        key = (str(scenario_id), _norm_core(core))
        row = self._entries.get(key)
        if row is None:
            raise OmniumProviderV2Error(f"unknown context/Core entry: {key}")

        expected_context = str(row["omnium_context_fingerprint"])
        if context_fingerprint is not None and str(context_fingerprint) != expected_context:
            raise OmniumProviderV2Error(
                f"{key}: stale/mismatched Omnium context fingerprint"
            )

        if require_approved and row.get("approval_status") != APPROVED:
            raise OmniumProviderV2Error(
                f"{key}: entry not approved for target optimization "
                f"({row.get('approval_status')})"
            )
        return deepcopy(row)

    def branches(self, scenario_id: str) -> list[dict[str, Any]]:
        rows = []
        for (sid, core), entry in self._entries.items():
            if sid != str(scenario_id):
                continue
            if entry.get("approval_status") != APPROVED:
                continue
            for stat in ROW4_STATS:
                rows.append(self._branch_from_entry(entry, stat))
        if not rows:
            raise OmniumProviderV2Error(
                f"{scenario_id}: no approved Omnium branches"
            )
        return sorted(rows, key=lambda r: (r["core"], r["row4_stat"]))

    def _branch_from_entry(
        self,
        entry: dict[str, Any],
        row4_stat: str,
    ) -> dict[str, Any]:
        stat = _norm_row4(row4_stat)
        magnitude = _finite_nonnegative(
            entry["expected_secondary_rating"],
            "expected_secondary_rating",
        )
        vector = {key: 0.0 for key in SECONDARY_KEYS}
        vector[stat.lower()] = magnitude
        branch_core = {
            "scenario_id": entry["scenario_id"],
            "core": _norm_core(entry["core"]),
            "row4_stat": stat,
            "omnium_context_fingerprint":
                entry["omnium_context_fingerprint"],
            "provider_entry_fingerprint":
                entry["provider_entry_fingerprint"],
            "provider_policy_fingerprint":
                entry["provider_policy_fingerprint"],
        }
        branch_id = (
            f"{entry['scenario_id']}|{_norm_core(entry['core'])}|{stat}|"
            f"{str(entry['provider_entry_fingerprint'])[:16]}"
        )
        return {
            **branch_core,
            "branch_id": branch_id,
            "expected_secondary_rating": magnitude,
            "fixed_secondary_vector": vector,
            "approval_status": entry["approval_status"],
            "confidence_class": entry.get("confidence_class"),
            "witness_count": int(entry.get("witness_count") or 0),
            "witness_identity_fingerprint":
                entry.get("witness_identity_fingerprint"),
            "evidence_artifact_fingerprints":
                deepcopy(entry.get("evidence_artifact_fingerprints") or {}),
            "expectation_method": entry.get("expectation_method"),
        }

    def branch(
        self,
        scenario_id: str,
        core: str,
        row4_stat: str,
        *,
        context_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        entry = self.entry(
            scenario_id,
            core,
            context_fingerprint=context_fingerprint,
            require_approved=True,
        )
        return self._branch_from_entry(entry, row4_stat)

    def branch_by_id(self, branch_id: str) -> dict[str, Any]:
        matches = []
        for scenario_id in self.scenario_ids():
            try:
                rows = self.branches(scenario_id)
            except OmniumProviderV2Error:
                continue
            matches.extend(row for row in rows if row["branch_id"] == str(branch_id))
        if len(matches) != 1:
            raise OmniumProviderV2Error(
                f"approved branch_id not unique/present: {branch_id}"
            )
        return deepcopy(matches[0])

def build_synthetic_contract() -> dict[str, Any]:
    policy = {
        "semantic_policy_version": "OMNIUM_SCENARIO_CONTEXT_EXPECTATION_V2",
        "row4_axis_only": True,
        "universal_core_fixed_vector_allowed": False,
        "unknown_or_unapproved_fails_closed": True,
        "simc_combat_value_owner": "SIMC",
    }
    policy["policy_fingerprint"] = canonical_hash(policy)

    scenarios = {}
    targets = {}
    entries = []
    for sid, spec in (
        ("ARCANE_ULATEK_HEROIC", "ARCANE"),
        ("FROST_TWIN_FANGS_HEROIC", "FROST"),
    ):
        context = {
            "season_policy": "MIDNIGHT_S2",
            "scenario_id": sid,
            "encounter_id": 1 if spec == "ARCANE" else 2,
            "difficulty_id": 4,
            "class": "MAGE",
            "spec": spec,
            "talent_context_fingerprint": "UNKNOWN",
            "external_buff_cohort_mode": "ANY",
            "provider_policy_version": policy["semantic_policy_version"],
        }
        scenarios[sid] = {
            "context": context,
            "omnium_context_fingerprint": canonical_hash(context),
        }

        witnesses = []
        for i in range(3):
            rating = 10.0 + i
            witnesses.append({
                "character_name": f"{spec}P{i}",
                "report_code": f"{spec}R{i}",
                "fight_id": i + 1,
                "core": "UNLEASHED_FIRE",
                "row4_stat": "HASTE",
                "mean_active_stack": 1.0,
                "effective_average_secondary_rating": rating,
                "vector": {
                    "crit": 0.0,
                    "haste": rating,
                    "mastery": 0.0,
                    "vers": 0.0,
                },
                "timeline_provenance": "SYNTHETIC_EXACT",
                "source": "CURRENT_SELECTED_RANK_BOUNDARY",
            })
        fp_rows = []
        for w in witnesses:
            fp_rows.append({
                "identity": _identity(
                    w["character_name"], w["report_code"], w["fight_id"]
                ),
                "core": w["core"],
                "row4_stat": w["row4_stat"],
                "vector": w["vector"],
                "mean_active_stack": w["mean_active_stack"],
                "timeline_provenance": w["timeline_provenance"],
            })
        targets[sid] = {
            "selected_rank_boundary": 5,
            "valid_witness_count": len(witnesses),
            "witnesses": witnesses,
            "witness_set_fingerprint": canonical_hash(fp_rows),
        }

        for core, approval, stack, rpa, n in (
            ("UNLEASHED_FIRE", APPROVED, 1.5, 79.9, 29),
            ("VOID_TOUCHED_ORBS", "REVIEW_REQUIRED", 1.0, 52.7, 2),
        ):
            identities = canonical_hash({
                "scenario_id": sid, "core": core, "n": n
            })
            entry = {
                "scenario_id": sid,
                "omnium_context_fingerprint":
                    scenarios[sid]["omnium_context_fingerprint"],
                "core": core,
                "expectation_method":
                    "ARITHMETIC_MEAN_EXACT_WITNESS_MEAN_ACTIVE_STACK",
                "expected_mean_active_stack": stack,
                "rating_per_application": rpa,
                "expected_secondary_rating": stack * rpa,
                "witness_count": n,
                "witness_identity_fingerprint": identities,
                "evidence_artifact_fingerprints": {"synthetic": "0" * 64},
                "confidence_class":
                    "OBSERVED_CONTEXT_COHORT" if core == "UNLEASHED_FIRE"
                    else "LOW_SAMPLE",
                "approval_status": approval,
                "provider_policy_fingerprint": policy["policy_fingerprint"],
            }
            entry["provider_entry_fingerprint"] = canonical_hash(_entry_core(entry))
            entries.append(entry)

    return {
        "schema": CONTRACT_SCHEMA,
        "version": CONTRACT_VERSION,
        "status": "RESEARCH_CONTRACT_LOCKED",
        "provider_policy": policy,
        "scenario_contexts": scenarios,
        "target_witness_contract": targets,
        "candidate_context_entries": entries,
    }

def self_test() -> None:
    contract = build_synthetic_contract()
    validate_contract(contract)
    provider = OmniumExpectedSecondaryProviderV2(contract)
    assert len(provider.target_witness_vectors("ARCANE_ULATEK_HEROIC")) == 3
    assert len(provider.branches("ARCANE_ULATEK_HEROIC")) == 4
    fire = provider.branch(
        "ARCANE_ULATEK_HEROIC", "UNLEASHED_FIRE", "MASTERY"
    )
    assert fire["fixed_secondary_vector"]["mastery"] > 0
    try:
        provider.branch(
            "ARCANE_ULATEK_HEROIC", "VOID_TOUCHED_ORBS", "HASTE"
        )
    except OmniumProviderV2Error:
        pass
    else:
        raise AssertionError("unapproved Void branch did not fail closed")
    try:
        provider.branch(
            "ARCANE_ULATEK_HEROIC",
            "UNLEASHED_FIRE",
            "HASTE",
            context_fingerprint="stale",
        )
    except OmniumProviderV2Error:
        pass
    else:
        raise AssertionError("stale context fingerprint did not fail closed")
    print("OMNIUM_EXPECTED_SECONDARY_PROVIDER_V2_SELF_TEST_PASS")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test()

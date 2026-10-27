#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

SCHEMA_NAME = "WEQUIPCandidateBasisAugmentationModel"
SCHEMA_VERSION = "1.0"
SECONDARY_KEYS = ("crit", "haste", "mastery", "vers")
TARGET_MODES = {
    "OMNIUM_NEUTRAL_REFERENCE",
    "OBSERVED_EFFECTIVE_PRODUCTION",
}
DIAMOND_ROLES = {
    "PRIMARY_32",
    "PRIMARY_23_COLOR_CRIT_EFFECT",
}


class CandidateBasisAugmentationError(RuntimeError):
    pass


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise CandidateBasisAugmentationError(reason)


def _candidate_key(candidate: dict[str, Any], index: int) -> str:
    for key in ("physical_variant_key", "candidate_variant_key", "candidate_id"):
        value = str(candidate.get(key) or "").strip()
        if value:
            return value
    return f"candidate_index:{index}"


def _vector(value: Any, label: str) -> dict[str, float]:
    _require(isinstance(value, dict), f"{label} must be dict")
    extra = sorted(set(value) - set(SECONDARY_KEYS))
    _require(not extra, f"{label} unsupported keys: {extra}")
    out = {}
    for key in SECONDARY_KEYS:
        raw = value.get(key, 0) or 0
        _require(not isinstance(raw, bool), f"{label}.{key} cannot be bool")
        try:
            out[key] = float(raw)
        except Exception as exc:
            raise CandidateBasisAugmentationError(
                f"{label}.{key} must be numeric"
            ) from exc
        _require(out[key] >= 0, f"{label}.{key} must be nonnegative")
    return out


def _load_d_catalog(d_binding: dict[str, Any]) -> dict[str, Any]:
    recovery = d_binding.get("production_catalog_recovery") or {}
    gem_rules = recovery.get("gem_rules") or {}
    flask_rules = recovery.get("flask_rules") or {}
    normalized = gem_rules.get("normalized_catalog") or {}
    gems = deepcopy(normalized.get("eligible_dual_gems") or [])
    excluded = deepcopy(normalized.get("excluded_pure_17_gems") or [])
    diamonds = deepcopy(normalized.get("user_approved_special_diamonds") or [])
    flasks = deepcopy(flask_rules.get("normalized_catalog") or [])

    _require(len(gems) == 12, f"expected 12 approved dual gems, got {len(gems)}")
    _require(len(excluded) == 4, f"expected four excluded +17 gems, got {len(excluded)}")
    _require(len(diamonds) == 2, f"expected two approved diamonds, got {len(diamonds)}")
    _require(len(flasks) == 4, f"expected four Flask choices, got {len(flasks)}")

    for row in gems:
        vec = _vector(row.get("secondary_rating"), "gem.secondary_rating")
        positives = sorted(v for v in vec.values() if v > 0)
        _require(positives == [7.0, 16.0], f"gem is not approved 16+7: {row}")
        _require(
            str(row.get("main_family") or "") in SECONDARY_KEYS,
            "gem main_family invalid",
        )
    for row in flasks:
        vec = _vector(row.get("secondary_rating"), "flask.secondary_rating")
        _require(sum(vec.values()) == 165.0, f"Flask must total 165: {row}")
        _require(sum(1 for x in vec.values() if x > 0) == 1, f"Flask must be one-axis: {row}")

    return {
        "gems": gems,
        "excluded_pure_17_gems": excluded,
        "diamonds": diamonds,
        "flasks": flasks,
        "gem_rules_fingerprint": gem_rules.get("fingerprint"),
        "flask_rules_fingerprint": flask_rules.get("fingerprint"),
        "d_binding_fingerprint": d_binding.get("binding_fingerprint"),
    }


def validate_basis_semantics(
    *,
    target_mode: str,
    basis_semantics: dict[str, Any],
    target_stat_basis_fingerprint: str,
    d_catalog: dict[str, Any],
    expected_effect_policy_identity: str,
    expected_effect_policy_fingerprint: str,
    expected_omnium_policy_fingerprint: str,
) -> str:
    _require(target_mode in TARGET_MODES, f"unsupported target mode: {target_mode}")
    _require(isinstance(basis_semantics, dict), "basis_semantics must be dict")
    calculated = canonical_hash(basis_semantics)
    _require(
        calculated == str(target_stat_basis_fingerprint),
        "target basis semantics hash/fingerprint mismatch",
    )
    _require(
        basis_semantics.get("target_mode") == target_mode,
        "basis target_mode mismatch",
    )
    _require(
        basis_semantics.get("physical_static_lane") == "DIRECT_COMPONENT_AUTHORITY",
        "physical static lane mismatch",
    )
    _require(
        basis_semantics.get("enchant_policy") == "ENCHANT_NEUTRAL_TARGET",
        "candidate target must remain enchant-neutral",
    )
    _require(
        basis_semantics.get("item_secondary_effect_policy_identity")
        == expected_effect_policy_identity,
        "generalized item-effect policy identity mismatch",
    )
    _require(
        basis_semantics.get("item_secondary_effect_policy_fingerprint")
        == expected_effect_policy_fingerprint,
        "generalized item-effect policy fingerprint mismatch",
    )
    gem_identity = basis_semantics.get("gem_socket_policy_identity") or {}
    _require(
        gem_identity.get("gem_rules_fingerprint")
        == d_catalog["gem_rules_fingerprint"],
        "gem rules fingerprint mismatch",
    )
    _require(
        gem_identity.get("D_binding_fingerprint")
        == d_catalog["d_binding_fingerprint"],
        "D binding fingerprint mismatch",
    )
    flask_identity = basis_semantics.get("flask_policy_identity") or {}
    _require(
        flask_identity.get("flask_rules_fingerprint")
        == d_catalog["flask_rules_fingerprint"],
        "Flask rules fingerprint mismatch",
    )
    _require(
        flask_identity.get("rating") == 165,
        "Flask rating policy mismatch",
    )

    included = list(basis_semantics.get("included_components") or [])
    base_required = {
        "PHYSICAL_STATIC",
        "ACTUAL_NORMAL_GEMS",
        "EXACT_SECONDARY_FLASK",
        "GENERALIZED_ITEM_SECONDARY_EFFECT_EXPECTATION",
    }
    _require(base_required.issubset(set(included)), "candidate basis component grammar incomplete")

    observed_omnium = "OBSERVED_OMNIUM_EXPECTED_SECONDARY"
    if target_mode == "OMNIUM_NEUTRAL_REFERENCE":
        _require(observed_omnium not in included, "neutral mode must exclude Omnium")
        _require(
            basis_semantics.get("omnium_policy_fingerprint") == "EXCLUDED_FROM_NEUTRAL",
            "neutral Omnium policy mismatch",
        )
    else:
        _require(observed_omnium in included, "effective mode must include Omnium grammar")
        _require(
            basis_semantics.get("omnium_policy_fingerprint")
            == expected_omnium_policy_fingerprint,
            "effective Omnium policy fingerprint mismatch",
        )
    return calculated


def augment_single_scenario_problem(
    *,
    effect_solver: Any,
    base_problem: dict[str, Any],
    d_binding: dict[str, Any],
    target_mode: str,
    basis_semantics: dict[str, Any],
    target_stat_basis_fingerprint: str,
    socket_resource_budget: int,
    owned_socketed_variant_keys: set[str] | list[str] | tuple[str, ...] = (),
    special_diamond_role: str,
    omnium_provider: Any | None,
    scenario_id: str | None,
    expected_effect_policy_identity: str,
    expected_effect_policy_fingerprint: str,
    expected_omnium_policy_fingerprint: str,
) -> dict[str, Any]:
    _require(type(socket_resource_budget) is int and socket_resource_budget >= 0,
             "socket_resource_budget must be nonnegative integer")
    _require(special_diamond_role in DIAMOND_ROLES, "unsupported special diamond role")

    fixed = base_problem.get("fixed_secondary_context") or {}
    _require(
        all(int(fixed.get(k, 0) or 0) == 0 for k in SECONDARY_KEYS),
        "legacy fixed_secondary_context must be all-zero; flexible controls are Solver-visible",
    )
    _require(
        base_problem.get("item_secondary_effect_policy_identity")
        == expected_effect_policy_identity,
        "base problem item-effect policy mismatch",
    )

    d_catalog = _load_d_catalog(d_binding)
    candidate_fp = validate_basis_semantics(
        target_mode=target_mode,
        basis_semantics=basis_semantics,
        target_stat_basis_fingerprint=target_stat_basis_fingerprint,
        d_catalog=d_catalog,
        expected_effect_policy_identity=expected_effect_policy_identity,
        expected_effect_policy_fingerprint=expected_effect_policy_fingerprint,
        expected_omnium_policy_fingerprint=expected_omnium_policy_fingerprint,
    )

    model = base_problem["model"]
    candidates = base_problem["candidates"]
    selected_vars = base_problem["selected_vars"]
    owned = {str(x) for x in owned_socketed_variant_keys}

    # ----------------------------
    # Physical-copy socket/gem state
    # ----------------------------
    socket_rows = []
    paid_added_socket_vars = []
    gem_vars_by_id: dict[int, list[Any]] = {
        int(g["item_id"]): [] for g in d_catalog["gems"]
    }
    gem_vars_by_family: dict[str, list[Any]] = {
        key: [] for key in SECONDARY_KEYS
    }
    diamond_vars = []

    for index, candidate in enumerate(candidates):
        copy_key = _candidate_key(candidate, index)
        info = candidate.get("socket_info") or {}
        default_sockets = int(info.get("default_sockets", 0) or 0)
        max_sockets = int(info.get("max_sockets", default_sockets) or default_sockets)
        can_add = bool(info.get("can_add_socket"))
        _require(default_sockets >= 0 and max_sockets >= default_sockets,
                 f"invalid socket_info for {copy_key}")
        add_capacity = max_sockets - default_sockets
        if not can_add:
            add_capacity = 0

        active_specs: list[tuple[str, Any, bool]] = []
        for socket_index in range(default_sockets):
            active_specs.append((f"N{socket_index}", selected_vars[index], False))

        for add_index in range(add_capacity):
            var = model.new_bool_var(f"cb_addsock_{index}_{add_index}")
            if copy_key in owned:
                model.add(var == selected_vars[index])
                paid = False
            else:
                model.add(var <= selected_vars[index])
                paid_added_socket_vars.append(var)
                paid = True
            active_specs.append((f"A{add_index}", var, paid))

        for socket_label, active_var, paid in active_specs:
            gem_choice_vars = []
            for gem in d_catalog["gems"]:
                gid = int(gem["item_id"])
                gv = model.new_bool_var(f"cb_gem_{index}_{socket_label}_{gid}")
                gem_choice_vars.append(gv)
                gem_vars_by_id[gid].append(gv)
                gem_vars_by_family[str(gem["main_family"])].append(gv)
            dv = model.new_bool_var(f"cb_diamond_{index}_{socket_label}")
            diamond_vars.append(dv)
            model.add(sum(gem_choice_vars) + dv == active_var)
            socket_rows.append({
                "candidate_index": index,
                "physical_copy_key": copy_key,
                "socket_label": socket_label,
                "active_var": active_var,
                "paid_added_socket": paid,
                "gem_vars": {
                    int(g["item_id"]): gem_choice_vars[pos]
                    for pos, g in enumerate(d_catalog["gems"])
                },
                "diamond_var": dv,
            })

    if paid_added_socket_vars:
        model.add(sum(paid_added_socket_vars) <= socket_resource_budget)
    else:
        _require(socket_resource_budget >= 0, "invalid socket budget")

    # Current-season complete gearsets have native neck/ring sockets, but keep
    # this conditional so the model remains well-defined for a zero-socket fixture.
    total_active_upper = len(socket_rows)
    total_active = model.new_int_var(0, max(0, total_active_upper), "cb_total_active_sockets")
    model.add(total_active == sum(row["active_var"] for row in socket_rows))
    has_socket = model.new_bool_var("cb_has_any_socket")
    if total_active_upper:
        model.add(total_active >= has_socket)
        model.add(total_active <= total_active_upper * has_socket)
    else:
        model.add(has_socket == 0)
    model.add(sum(diamond_vars) == has_socket)

    if special_diamond_role == "PRIMARY_23_COLOR_CRIT_EFFECT":
        # The approved +23 branch requires all four normal-gem main families.
        for family in SECONDARY_KEYS:
            vars_ = gem_vars_by_family[family]
            _require(vars_, f"no gem variables for family {family}")
            model.add(sum(vars_) >= has_socket)

    diamond_rows = [
        row for row in d_catalog["diamonds"]
        if row.get("role") == special_diamond_role
    ]
    _require(len(diamond_rows) == 1, "special diamond role not uniquely resolved")
    selected_diamond = diamond_rows[0]

    gem_contrib_vars = {}
    max_socket_count = max(1, total_active_upper)
    for stat in SECONDARY_KEYS:
        terms = []
        max_per_socket = 0
        for gem in d_catalog["gems"]:
            coeff = effect_solver.signed_rating_to_fixed_scaled(
                (gem.get("secondary_rating") or {}).get(stat, 0),
                label=f"gem[{gem['item_id']}].{stat}",
            )
            max_per_socket = max(max_per_socket, coeff)
            for gv in gem_vars_by_id[int(gem["item_id"])]:
                if coeff:
                    terms.append(coeff * gv)
        upper = max_per_socket * max_socket_count
        var = model.new_int_var(0, max(0, upper), f"cb_gem_{stat}_total")
        model.add(var == sum(terms))
        gem_contrib_vars[stat] = var

    # ----------------------------
    # Scenario-local Flask choice
    # ----------------------------
    flask_vars = {}
    for flask in d_catalog["flasks"]:
        fid = str(flask["flask_id"])
        flask_vars[fid] = model.new_bool_var(f"cb_flask_{fid}")
    model.add(sum(flask_vars.values()) == 1)

    flask_contrib_vars = {}
    for stat in SECONDARY_KEYS:
        terms = []
        upper = 0
        for flask in d_catalog["flasks"]:
            coeff = effect_solver.signed_rating_to_fixed_scaled(
                (flask.get("secondary_rating") or {}).get(stat, 0),
                label=f"flask[{flask['flask_id']}].{stat}",
            )
            upper = max(upper, coeff)
            if coeff:
                terms.append(coeff * flask_vars[str(flask["flask_id"])])
        var = model.new_int_var(0, max(0, upper), f"cb_flask_{stat}_total")
        model.add(var == sum(terms))
        flask_contrib_vars[stat] = var

    # ----------------------------
    # Scenario-local Omnium choice
    # ----------------------------
    omnium_branch_vars = {}
    omnium_branches = []
    omnium_contrib_vars = {}
    if target_mode == "OMNIUM_NEUTRAL_REFERENCE":
        for stat in SECONDARY_KEYS:
            var = model.new_int_var(0, 0, f"cb_omnium_{stat}_total")
            model.add(var == 0)
            omnium_contrib_vars[stat] = var
    else:
        _require(omnium_provider is not None, "effective mode requires Omnium provider")
        _require(str(scenario_id or "").strip(), "effective mode requires scenario_id")
        _require(
            omnium_provider.provider_policy_fingerprint()
            == expected_omnium_policy_fingerprint,
            "Omnium provider policy fingerprint mismatch",
        )
        omnium_branches = list(omnium_provider.branches(str(scenario_id)))
        _require(omnium_branches, "no approved Omnium branches for scenario")
        for branch in omnium_branches:
            bid = str(branch["branch_id"])
            _require(
                branch.get("approval_status") == "APPROVED_FOR_TARGET_OPTIMIZATION",
                "unapproved Omnium branch leaked into production branch list",
            )
            omnium_branch_vars[bid] = model.new_bool_var(
                f"cb_omnium_{len(omnium_branch_vars)}"
            )
        model.add(sum(omnium_branch_vars.values()) == 1)
        for stat in SECONDARY_KEYS:
            terms = []
            upper = 0
            for branch in omnium_branches:
                coeff = effect_solver.signed_rating_to_fixed_scaled(
                    (branch.get("fixed_secondary_vector") or {}).get(stat, 0),
                    label=f"omnium[{branch['branch_id']}].{stat}",
                )
                upper = max(upper, coeff)
                if coeff:
                    terms.append(coeff * omnium_branch_vars[str(branch["branch_id"])])
            var = model.new_int_var(0, max(0, upper), f"cb_omnium_{stat}_total")
            model.add(var == sum(terms))
            omnium_contrib_vars[stat] = var

    # ----------------------------
    # Final effective CHMV
    # static + E effect + gems + Flask + Omnium
    # ----------------------------
    augmented_effective_vars = {}
    augmented_effective_uppers = {}
    for stat in SECONDARY_KEYS:
        static_upper = int(base_problem["stat_upper_bounds"][stat])
        effect_upper = max(0, int(base_problem["effect_delta_bounds"][stat]["upper"]))
        gem_upper = max_socket_count * max(
            effect_solver.signed_rating_to_fixed_scaled(
                (gem.get("secondary_rating") or {}).get(stat, 0),
                label=f"gem_upper.{stat}",
            )
            for gem in d_catalog["gems"]
        )
        flask_upper = max(
            effect_solver.signed_rating_to_fixed_scaled(
                (row.get("secondary_rating") or {}).get(stat, 0),
                label=f"flask_upper.{stat}",
            )
            for row in d_catalog["flasks"]
        )
        omni_upper = 0
        for branch in omnium_branches:
            omni_upper = max(
                omni_upper,
                effect_solver.signed_rating_to_fixed_scaled(
                    (branch.get("fixed_secondary_vector") or {}).get(stat, 0),
                    label=f"omnium_upper.{stat}",
                ),
            )
        upper = max(0, static_upper + effect_upper + gem_upper + flask_upper + omni_upper)
        var = model.new_int_var(0, upper, f"cb_effective_{stat}")
        model.add(
            var
            == base_problem["stat_vars"][stat]
            + base_problem["effect_delta_vars"][stat]
            + gem_contrib_vars[stat]
            + flask_contrib_vars[stat]
            + omnium_contrib_vars[stat]
        )
        augmented_effective_vars[stat] = var
        augmented_effective_uppers[stat] = upper

    total_upper = max(1, sum(augmented_effective_uppers.values()))
    effective_total = model.new_int_var(1, total_upper, "cb_effective_total_secondary")
    model.add(effective_total == sum(augmented_effective_vars.values()))

    target_basis = base_problem["target"]["basis"]
    target_total = int(base_problem["target"]["basis_total"])
    cross_devs = {}
    for stat in SECONDARY_KEYS:
        upper = (
            target_total * augmented_effective_uppers[stat]
            + int(target_basis[stat]) * total_upper
        )
        dev = model.new_int_var(0, max(0, upper), f"cb_cross_dev_{stat}")
        model.add_abs_equality(
            dev,
            target_total * augmented_effective_vars[stat]
            - int(target_basis[stat]) * effective_total,
        )
        cross_devs[stat] = dev

    cross_upper = sum(
        target_total * augmented_effective_uppers[stat]
        + int(target_basis[stat]) * total_upper
        for stat in SECONDARY_KEYS
    )
    cross_error = model.new_int_var(0, max(0, cross_upper), "cb_cross_error_F")
    model.add(cross_error == sum(cross_devs.values()))

    # Preserve the legacy E objective surface for audit, but make the augmented
    # surface canonical for the exact ratio solver/certifier.
    augmented = dict(base_problem)
    augmented["legacy_effective_stat_vars"] = base_problem["effective_stat_vars"]
    augmented["legacy_effective_total_secondary_var"] = base_problem[
        "effective_total_secondary_var"
    ]
    augmented["legacy_cross_error_var"] = base_problem["cross_error_var"]
    augmented["effective_stat_vars"] = augmented_effective_vars
    augmented["effective_stat_upper_bounds"] = augmented_effective_uppers
    augmented["effective_total_secondary_var"] = effective_total
    augmented["effective_total_secondary_upper"] = total_upper
    augmented["cross_deviation_vars"] = cross_devs
    augmented["cross_error_var"] = cross_error
    augmented["candidate_stat_basis_fingerprint"] = candidate_fp
    augmented["candidate_basis_semantics"] = deepcopy(basis_semantics)
    augmented["candidate_basis_augmentation"] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "target_mode": target_mode,
        "scenario_id": scenario_id,
        "socket_resource_budget": socket_resource_budget,
        "owned_socketed_variant_keys": sorted(owned),
        "special_diamond": deepcopy(selected_diamond),
        "socket_rows": socket_rows,
        "paid_added_socket_vars": paid_added_socket_vars,
        "gem_catalog": deepcopy(d_catalog["gems"]),
        "excluded_pure_17_gems": deepcopy(d_catalog["excluded_pure_17_gems"]),
        "gem_contrib_vars": gem_contrib_vars,
        "flask_catalog": deepcopy(d_catalog["flasks"]),
        "flask_vars": flask_vars,
        "flask_contrib_vars": flask_contrib_vars,
        "omnium_branches": deepcopy(omnium_branches),
        "omnium_branch_vars": omnium_branch_vars,
        "omnium_contrib_vars": omnium_contrib_vars,
        "has_socket_var": has_socket,
        "total_active_socket_var": total_active,
    }
    return augmented

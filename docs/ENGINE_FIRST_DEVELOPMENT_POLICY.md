# Engine-first development and season/data replacement

**A_MAIN-approved product direction (2026-10-29).** This public-facing design note is **non-authoritative** and does not change the M1-only release scope, runtime contracts, production source or lifecycle. The full product remains **PAUSED / NOT COMPLETE**.

## What WEQUIP is building

WEQUIP is a **reusable gear-optimization engine**, not a frozen copy of one season's item database, one character's inventory, or a one-off optimization receipt.

The target operating model is:

```
Approved, versioned season/item/source data + effect and resource-policy packages
                           +
Runtime user request (scenarios, targets, owned/fixed/excluded copies, limits)
                           |
                           v
Stable producer/normalizer -> effect/stat-basis boundary -> exact joint optimizer
                           |
                           v
Complete equippable gearsets -> stable presentation result
                           |
                           v
                 Optional downstream SimulationCraft
```

**Success criterion:** for schema-compatible data changes, a new patch/season package can replace the previous approved dataset while the **engine implementation bytes remain unchanged**, subject to data/source/policy validation. Actual game-mechanic changes require explicitly versioned rule/adapter changes or narrowly justified engine extensions; a semantic change is not merely a data refresh.

## Engineering rules

- Distinguish `DATA_ONLY`, `RULE_POLICY_CHANGE`, `ENGINE_SEMANTIC_CHANGE`, and `USER_REQUEST_ONLY` before touching implementation.
- Treat character inventory, fixed gear, remaining crafting resources, acquisition restrictions, scenarios and priorities as **run-time input**, not global engine constants. Validate internal consistency, physical-copy identity, resource usage and legality—not whether a changing live account currently owns the declared item.
- Preserve exact item/source/ilvl/bonus/physical-copy identity and check reachability **before** stat resolution. A WCL observation does not grant acquisition eligibility.
- Resource, tier, embellishment, socket and gem constraints must be Solver-visible; do not repair a solution with post-hoc filtering. Effect uncertainty is **fail-closed**, never silently converted to zero.
- Enforce equality of target and candidate stat-basis fingerprints. Report `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, timeouts and scope of certification truthfully.
- Reuse approved Producer, Effect Provider, Joint Solver and Presentation components. Add a new module/API/validator only for a proven consumer-interface gap; do not rebuild the engine for one current-season fixture.
- Keep fast, deterministic, offline CI focused. Real season DB, costly Solver runs, user data, Windows/SimC and live APIs are separately approved execution boundaries.

## Minimum evidence for reusable engine readiness

1. Run **two distinct compatible dataset fixtures** with the **same engine source SHA** and verify complete, source-qualified gearset outputs. Synthetic fixtures certify the interface and invariants only, not live-season optimality.
2. Vary runtime owned/fixed physical copies, resources, route permissions, pair restrictions and scenario priorities; show changes occur through input and constraints, not engine code edits.
3. Test a deliberately incompatible season/policy version and unresolved item effect: **fail closed** without guessed costs, invisible exception rules, or fake optimality.
4. Execute an approved real-data vertical slice from candidate production through exact optimization and presentation; bind all source/data/policy/result identities and check rollback/cache invalidation behavior.

An unresolved effect for one mandatory-item fixture blocks certification **for that fixture**. It must not halt engine development against other supported inputs, and the mandatory item must not be silently removed to manufacture success.

## Publication and authority

This is documentation only. No private source, private DB/WCL data, credentials, user profile, internal handoff material or additional product code is authorized for publication by this document. M1 smoke tests remain limited in scope. A_MAIN owns contract promotion, exact source identity, validation and release decisions.

# WEQUIP — M1 Offline Provider Smoke (initial public-source scope)

This is the **first, intentionally limited public-source foundation** of WEQUIP, not the complete World of Warcraft gearset optimizer. It tests a byte-pinned Omnium expected-secondary provider with synthetic data. **Production F remains PAUSED / NOT COMPLETE**; a successful M1 check does not prove obtainable gearsets, end-to-end Solver correctness, actual CP-SAT execution, SimC parity or live DB binding.

## Scope

- `source/Omnium_Expected_Secondary_Provider_v2.py` — unchanged project source, SHA256 `24baafbdc895fc7b39515ca131be3e65c1077b094cc6c6216c4d203190a44f37`.
- `scripts/m1_offline_smoke.py` — exact-byte/size checks, isolated synthetic self-test, sanitized JSON receipt.
- `tests/test_m1_offline_smoke.py` — 6 focused positive/negative checks.
- `.github/workflows/m1-offline-smoke.yml` — manual `workflow_dispatch` only, read-only permission, pinned checkout.
- `RELEASE_CANDIDATE_MANIFEST.json` — exact file identities and scope limitation.

## Run offline

```sh
python3 -B scripts/m1_offline_smoke.py
python3 -B -m unittest discover -s tests -v
```

No credentials, Master DB, real WCL/Blizzard records, SimulationCraft installation or solver are required. This is a **code-level offline path**, not an OS-enforced network sandbox. GitHub Actions results must be verified separately against the committed SHA; local dry-run results must not be presented as hosted Actions PASS.

## Release and license boundary

The WEQUIP user confirmed that WEQUIP Python code was directly authored or AI-generated and **approved publication of this M1-only source scope on 2026-10-27**. This is not approval to release the full product, historical Runtime, private handoff ZIP, user data, raw WCL, entire database or earlier internal project history.

**No open-source license has been selected.** Public visibility does not automatically grant general reuse/modification/distribution rights. Third-party data and future product-code inclusion require their own review.

**Historic receipt compatibility:** `public_release_approved: false` produced by the unchanged migration smoke runner reflects its original pre-publication candidate/prod-release guard; it is not a live claim about the repository's GitHub visibility. The `RELEASE_CANDIDATE_MANIFEST.json` records this distinct M1 publication approval. We preserve the tested runner bytes rather than silently rewriting its semantics.

## Long-term architecture direction (2026-10-29)

WEQUIP's product is a **season/data-replaceable optimization engine**, not a single M1 fixture or current-season dataset. Read [Engine-first development policy](docs/ENGINE_FIRST_DEVELOPMENT_POLICY.md) for the distinction between data, game-rule policy, runtime user input, and stable Solver semantics, plus its two-dataset/same-engine-SHA readiness check. This documentation does **not** expand M1 publication or production certification scope.

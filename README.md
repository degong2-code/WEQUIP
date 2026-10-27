# WEQUIP — M1 Offline Provider Smoke (initial public-source scope)

This is the **first, intentionally limited public-source foundation** of WEQUIP, not the complete World of Warcraft gearset optimizer. It tests a byte-pinned Omnium expected-secondary provider with synthetic data. **Production F remains PAUSED / NOT COMPLETE**; a successful M1 check does not prove obtainable gearsets, end-to-end Solver correctness, actual CP-SAT execution, SimC parity or live DB binding.

## Scope

- `source/Omnium_Expected_Secondary_Provider_v2.py` — unchanged project source, SHA256 `24baafbdc895fc7b39515ca131be3e65c1077b094cc6c6216c4d203190a44f37`.
- `scripts/m1_offline_smoke.py` — exact-byte/size checks, isolated synthetic self-test, sanitized JSON receipt.
- `tests/test_m1_offline_smoke.py` — 6 focused positive/negative checks.
- `.github/workflows/m1-offline-smoke.yml` — `push`-triggered CI on isolated `work/wequip-m1-auto-ci` (not `main`), scoped to source, scripts, tests, workflow and release-manifest changes; read-only permission, pinned checkout.
- `RELEASE_CANDIDATE_MANIFEST.json` — exact file identities and scope limitation.

**Snapshot identity:** `RELEASE_CANDIDATE_MANIFEST.json` describes the original approved first-public-commit candidate at `f52f8cebf22b01595f0bf0200fbb729ffe933e69`. It is immutable historical release evidence, **not** a live checksum manifest for subsequent development-branch commits. For CI, compare the actual Git tree and the Actions run's `head_sha`; do not treat the old candidate manifest's workflow/test hashes or pre-publication status fields as current branch state.

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

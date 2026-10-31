# WEQUIP Private-Source Runner (TEST_ONLY)

## Purpose and boundary

This workflow uses the public degong2-code/WEQUIP repository only as a GitHub-hosted execution host for focused tests against two exact commits in private degong2-code/ai-project-lab.

It does not publish, mirror, commit, or upload private WEQUIP source code or data. The public repository stores only this workflow, this setup document, and a small non-secret trigger receipt. No private source artifact or cache is uploaded.

This runner is TEST_ONLY. It does not certify Production F, MIG-04, a real-season database, Windows runtime behavior, SimulationCraft parity, or complete Gearset/Envelope E2E.

## Exact private source pins

| Purpose | Private commit SHA | Test scope |
|---|---|---|
| PR #8 SSFINDOUT Target V1 Receiver | fb82e2127ca70848976484c84e0f91179ee75e80 | JSON Schema, cross-field semantics, normalization, negative/fail-closed cases |
| PR #9 Absolute CHMV Balanced | 3a980caadacb340991b07778785e6700d587e46c | Native OR-Tools CP-SAT objective and exact arithmetic regression |

The workflow pins both source SHAs as literals. It accepts no arbitrary source-ref input and only runs on the public repository's main branch after A_MAIN pushes the dedicated trigger file.

## Test suites

1. PR #8: test_receiver_adapter_v1.py
2. PR #9: test_absolute_chmv_balanced_v1.py
3. Existing EffectAware regression: test_effectaware_cp_sat_v1_1.py
4. Existing Stage13 resource/copy/tier/socket regression: test_stage13_resource_copy_basis_v1_1.py

Dependencies are pinned to jsonschema==4.25.1 and ortools==9.14.6206. The runner requires Python 3.12.

These focused tests do not prove full Joint optimization, canonical Production F integration, global OPTIMAL, or production completion.

## One-time user setup

The user performs only the one-time private-repository authorization. A_MAIN performs the trigger commit and all subsequent test execution, log inspection, correction, and reruns.

### 1. Environment

In degong2-code/WEQUIP, create or retain Environment:

wequip-private-source-runner

Configure deployment branches/tags as Selected branches and tags, allowing only main.

Do not configure Required reviewers or Wait timer. They would reintroduce a manual approval on every run, which is not part of the intended operating model. The workflow uses deployment: false; it does not create deployment records. The existing main branch rule is already present; do not add a duplicate.

If Required reviewers were previously enabled, remove that protection rule. The branch restriction to main must remain.

### 2. Temporary read-only Fine-grained PAT

Create a Fine-grained PAT with:

- Resource owner: degong2-code
- Repository access: Only select repositories
- Selected repository: ai-project-lab only
- Repository permissions:
  - Contents: Read-only
  - Metadata: Read-only
- Expiration: 7 days (or the shortest practical period)

No Actions, Administration, Issues, Pull requests, Workflows, or write permissions are needed.

Never paste the token into ChatGPT, a commit, an issue, a workflow file, or a log.

### 3. Add the Environment Secret

In Settings → Environments → wequip-private-source-runner → Environment secrets, add:

WEQUIP_PRIVATE_SOURCE_READ_TOKEN

Use the PAT value. Do not create a repository-wide secret. Do not send the PAT to ChatGPT.

### 4. Automatic test execution — no user clicks or approvals

After the user confirms that the Environment Secret has been saved, A_MAIN creates or updates:

docs/private-source-runner/trigger.json

on main. That single push automatically starts this workflow. The workflow only listens for a push to this exact path on main; ordinary source commits and pull-request events do not trigger it.

The trigger receipt contains only a request ID, TEST_ONLY marker, and the two fixed source SHAs. It contains no credentials and cannot select arbitrary code.

The user does not need to click Run workflow, approve a deployment, run local commands, or upload logs. A_MAIN inspects the Actions run, analyzes failures, makes authorized corrections, and triggers subsequent runs by updating the same marker file with a new request ID.

### 5. Cleanup

After the focused test evidence has been captured:

1. Revoke the Fine-grained PAT.
2. Delete WEQUIP_PRIVATE_SOURCE_READ_TOKEN from Environment secrets.
3. Retain the sanitized Actions receipt and trigger metadata; no private source archive or raw workspace is retained.

## Security controls

- Public host permissions: contents: read only.
- Trigger: push to one fixed marker path on main; no pull_request, schedule, or arbitrary ref input.
- Private source SHAs are hard-coded in the workflow and independently checked against the trigger receipt.
- Private checkouts use fetch-depth: 1, persist-credentials: false, and non-cone sparse-checkout allowlists.
- PR #8 checkout is limited to projects/wequip/development/ssfout_target_v1/.
- PR #9 checkout is limited to projects/wequip/development/effectaware/ and projects/wequip/source/runtime/.
- Negative assertions verify that repository root README, private workflow files, and migration paths are not materialized.
- The PAT is used only for a presence check and the private checkout action. It is never printed, persisted in Git configuration, or passed to Python test processes.
- No private-source archive, artifact, or cache is uploaded.
- Logs contain test output and a sanitized receipt with source SHAs and suite outcomes only.
- No WCL/Blizzard credentials, season database, user data, SimC binary, or production runtime is used.

Keep write access to the public repository limited to trusted maintainers while the temporary Environment Secret exists. The Environment is restricted to main; fork pull requests and arbitrary branches do not receive this secret.

## Interpretation

A green run proves only that the exact pinned code passed these focused tests on the specified public Ubuntu runner and dependency versions.

It does not prove:

- the SSFINDOUT producer exports this contract;
- the Receiver resolves source-qualified item records or exact variants;
- Absolute CHMV is wired into the production candidate/Stage12/Stage13 consumer;
- the multi-specialization Joint objective is Absolute CHMV;
- a globally optimal complete gearset was produced;
- the real season database, Windows runtime, or SimC pipeline is production-ready.

Production remains PAUSED / NOT COMPLETE until A_MAIN separately verifies the real downstream consumer and approved production E2E.

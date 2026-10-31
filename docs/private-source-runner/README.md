# WEQUIP Private-Source Runner (TEST_ONLY)

## Purpose and boundary

This workflow reuses the existing public `degong2-code/WEQUIP` repository as a **temporary execution host** for focused tests against two exact commits in the private `degong2-code/ai-project-lab` repository.

It does **not** publish, mirror, commit, or upload private WEQUIP source code or data. The public repository receives only this workflow and this setup document. The existing M1 public-source scope and the separate M2 branch are unchanged.

This runner is not a production runtime and does not certify Production F, MIG-04, a real-season database, Windows runtime behavior, SimulationCraft parity, or complete Gearset/Envelope E2E.

## Exact private source pins

| Purpose | Private commit SHA | Test scope |
|---|---|---|
| PR #8 SSFINDOUT Target V1 Receiver | `fb82e2127ca70848976484c84e0f91179ee75e80` | JSON Schema, cross-field semantics, normalization, negative/fail-closed cases |
| PR #9 Absolute CHMV Balanced | `3a980caadacb340991b07778785e6700d587e46c` | Native OR-Tools CP-SAT objective and exact arithmetic regression |

The workflow contains these SHAs as fixed literals. It accepts no arbitrary source-ref input and runs only from the public repository's `main` branch.

The environment is used only as an approval/secret gate. The workflow sets `deployment: false`, so it does not create a deployment record.

## Test suites

The workflow runs four suites:

1. PR #8: `test_receiver_adapter_v1.py`
2. PR #9: `test_absolute_chmv_balanced_v1.py`
3. Existing EffectAware regression: `test_effectaware_cp_sat_v1_1.py`
4. Existing Stage13 resource/copy/tier/socket regression: `test_stage13_resource_copy_basis_v1_1.py`

Dependencies are pinned to `jsonschema==4.25.1` and `ortools==9.14.6206`. The runner requires Python 3.12.

The two baseline EffectAware/Stage13 suites are included to protect the existing native CP-SAT and resource/copy constraints while testing the new objective. They do not prove full Joint optimization or production integration.

## Required owner setup

Do this only after reviewing and merging the runner PR.

### 1. Create the protected environment

In `degong2-code/WEQUIP`:

1. Open **Settings → Environments → New environment**.
2. Name it exactly `wequip-private-source-runner`.
3. Add a required reviewer (preferably a second trusted maintainer; if the repository owner must approve their own run, do not enable **Prevent self-review**).
4. Set deployment branches/tags to **Selected branches**, then allow only branch `main`.
5. Save the protection rules.

Do not run the workflow before the environment has been configured. GitHub automatically creates a referenced environment if it does not exist, but that new environment has no protection rules or secrets.

### 2. Create a temporary read-only Fine-grained PAT

Create a Fine-grained personal access token with:

- Resource owner: `degong2-code`
- Repository access: **Only select repositories**
- Selected repository: `ai-project-lab`
- Repository permissions:
  - **Contents: Read-only**
  - **Metadata: Read-only**
- Expiration: shortest practical period (recommended 1–7 days)

No Actions, Administration, Issues, Pull requests, or write permissions are needed.

Never paste the token into ChatGPT, a commit, an issue, a workflow file, or a log.

### 3. Add the token as an environment secret

In **Settings → Environments → wequip-private-source-runner → Environment secrets**, add:

`WEQUIP_PRIVATE_SOURCE_READ_TOKEN`

Use the PAT value. Do not create a repository-wide secret for this workflow.

### 4. Run the focused test workflow

1. Open **Actions → WEQUIP private-source focused tests (TEST_ONLY)**.
2. Select **Run workflow** on branch `main`.
3. Approve the environment gate when requested.
4. Inspect the sanitized run summary and each test suite's actual result.

The workflow uses `workflow_dispatch` only. It does not run for pull requests, pushes, schedules, or arbitrary branches.

## Security controls implemented in the workflow

- Public host permissions are read-only: `contents: read`.
- Private repository and commit SHAs are fixed in the workflow.
- The private checkout is limited to:
  - PR #8: `projects/wequip/development/ssfout_target_v1/`
  - PR #9: `projects/wequip/development/effectaware/`
  - PR #9: `projects/wequip/source/runtime/`
- `fetch-depth: 1` and `persist-credentials: false` are set for both private checkouts.
- The PAT is supplied only to the checkout action. It is not placed in a shell environment or passed to Python tests.
- No private-source archive, test artifact, cache, or source copy is uploaded.
- The public log contains test output and a sanitized receipt with commit SHAs and suite outcomes only.
- No WCL/Blizzard credentials, season database, user data, SimC binary, or production runtime is used.

The environment's required-reviewer gate must be configured before the secret is added. Keep write access to this public repository limited to trusted maintainers while the temporary secret exists.

## Cleanup after the run

After the required test evidence has been captured:

1. Revoke the Fine-grained PAT.
2. Delete `WEQUIP_PRIVATE_SOURCE_READ_TOKEN` from the environment.
3. Keep the sanitized Actions receipt; do not upload private source or raw test workspaces.

## Interpretation of results

A green workflow proves only that the exact pinned code passed these focused tests on the specified public Ubuntu runner and dependency versions.

It does not prove:

- the SSFINDOUT producer exports this contract;
- the Receiver resolves source-qualified item records or exact variants;
- Absolute CHMV is wired into the production candidate/Stage12/Stage13 consumer;
- the multi-specialization Joint objective is Absolute CHMV;
- a globally optimal complete gearset was produced;
- the real season database, Windows runtime, or SimC pipeline is production-ready.

Production state remains PAUSED / NOT COMPLETE until A_MAIN separately verifies the real downstream consumer and the approved production E2E.

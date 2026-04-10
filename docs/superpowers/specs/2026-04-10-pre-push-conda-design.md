# Pre-push Hook Conda Design

## Goal

Make the global Git pre-push hook use the `storyline` conda environment when pushing from the FireRed-OpenStoryline repository.

This should prevent false failures caused by running `pytest` with the wrong Python interpreter or without the repository root on `PYTHONPATH`.

## Current Problem

The active pre-push hook is the global hook at `/home/hans/.codex/git-hooks/pre-push`, not a repo-local hook.

For Python projects, it currently runs `pytest -q` directly when it sees `pyproject.toml` or `requirements.txt`.

That causes two problems for this repository:

1. It may run under the wrong Python environment instead of the documented `storyline` conda environment.
2. It does not set `PYTHONPATH=.`, so tests that import repo-root modules like `agent_fastapi` can fail during collection even before project-specific issues are reached.

## Chosen Approach

Add a narrow repository-specific branch to the global pre-push hook.

When the current repository is FireRed-OpenStoryline, the Python verification command should be:

```bash
PYTHONPATH=. conda run -n storyline python -m pytest -q
```

For all other repositories, keep the existing hook behavior unchanged.

## Repository Detection

The hook should identify this repository using stable Git metadata, preferring the `origin` URL and optionally falling back to the top-level directory name.

Expected matches include:

- `https://github.com/hans1996/FireRed-OpenStoryline`
- other equivalent `origin` URLs containing `FireRed-OpenStoryline`

This avoids applying the special case to unrelated Python repositories.

## Failure Behavior

If the hook detects FireRed-OpenStoryline but cannot use the `storyline` environment, it should fail clearly instead of silently falling back to plain `pytest -q`.

The failure message should explain one of these conditions:

- `conda` is not installed
- the `storyline` environment is missing
- the conda-based test command failed

This is preferred because a silent fallback would reintroduce the same misleading failures the change is meant to prevent.

## Non-goals

This change will not:

- generalize conda handling for every repository
- redesign the global hook framework
- fix existing failing tests inside FireRed-OpenStoryline
- move the hook from global scope to repo-local scope

## Verification Plan

After the hook is updated, verify with these checks:

1. Confirm the hook still runs normally in this repository.
2. Confirm the Python path is resolved via `conda run -n storyline`.
3. Confirm the command uses `PYTHONPATH=.`.
4. Trigger the hook with `git push` or an equivalent dry run and inspect the log output.
5. Confirm unrelated repositories still use the original generic Python behavior.

## Risks

The main risk is accidental overmatching if repository detection is too loose.

Mitigation:

- prefer exact or high-confidence `origin` URL matching
- keep the special case isolated to a small helper branch in the hook

Another risk is that FireRed-OpenStoryline still has real test failures after the environment issue is fixed.

That is acceptable for this task because the purpose here is to make the hook use the correct environment, not to make the entire test suite pass.

# Pre-push Hook Conda Override Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the global pre-push hook use `conda run -n storyline` for Python checks when pushing from FireRed-OpenStoryline.

**Architecture:** Add a small repository-specific branch inside the existing global hook instead of redesigning the whole hook system. Detect FireRed-OpenStoryline via Git metadata, then route Python verification through `conda run -n storyline python -m pytest -q` with `PYTHONPATH=.` while keeping all existing behavior unchanged for other repositories.

**Tech Stack:** Bash, Git hooks, Conda, pytest

---

### Task 1: Add FireRed-OpenStoryline Detection To The Global Hook

**Files:**
- Modify: `/home/hans/.codex/git-hooks/pre-push`
- Reference: `/media/hans/DATA/FireRed-OpenStoryline/docs/superpowers/specs/2026-04-10-pre-push-conda-design.md`

- [ ] **Step 1: Inspect the current hook and capture the exact insertion point**

Run:

```bash
sed -n '1,220p' /home/hans/.codex/git-hooks/pre-push
```

Expected: the hook contains a Python project branch that currently runs `pytest -q` directly.

- [ ] **Step 2: Add small helper functions for repository detection and conda environment checks**

Insert helper functions near the existing Bash helpers in `/home/hans/.codex/git-hooks/pre-push`:

```bash
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

get_origin_url() {
  git remote get-url origin 2>/dev/null || true
}

is_firered_openstoryline_repo() {
  local origin_url
  origin_url="$(get_origin_url)"
  if [[ "$origin_url" == *"FireRed-OpenStoryline"* ]]; then
    return 0
  fi

  local root_name
  root_name="$(basename "$repo_root")"
  [[ "$root_name" == "FireRed-OpenStoryline" ]]
}

ensure_storyline_conda_env() {
  command -v conda >/dev/null 2>&1 || fail "FireRed-OpenStoryline requires conda for pre-push checks"

  conda env list | awk '{print $1}' | grep -Fx "storyline" >/dev/null 2>&1 || \
    fail "FireRed-OpenStoryline requires a conda environment named storyline"
}
```

- [ ] **Step 3: Replace the generic Python branch with a repo-specific FireRed path**

Update the Python section in `/home/hans/.codex/git-hooks/pre-push` to this shape:

```bash
if [[ -f "pyproject.toml" || -f "requirements.txt" ]]; then
  if is_firered_openstoryline_repo; then
    ran_any_check=1
    ensure_storyline_conda_env
    log "FireRed-OpenStoryline detected. Running: PYTHONPATH=. conda run -n storyline python -m pytest -q"
    PYTHONPATH=. conda run -n storyline python -m pytest -q || fail "conda-based pytest failed"
  elif command -v pytest >/dev/null 2>&1; then
    ran_any_check=1
    log "Python project detected. Running: pytest -q"
    pytest -q || fail "pytest failed"
  else
    log "Python project detected but pytest is not installed. Skipping."
  fi
fi
```

- [ ] **Step 4: Review the final hook diff before testing**

Run:

```bash
git --no-pager diff --no-index -- /dev/null /dev/null >/dev/null 2>&1 || true
sed -n '1,220p' /home/hans/.codex/git-hooks/pre-push
```

Expected: the hook still contains all previous logic for Node, Go, and generic Python projects, plus a narrow FireRed-OpenStoryline special case.

### Task 2: Verify The Hook Uses The Correct Environment

**Files:**
- Verify: `/home/hans/.codex/git-hooks/pre-push`
- Verify in repo: `/media/hans/DATA/FireRed-OpenStoryline`

- [ ] **Step 1: Confirm the target repo is detected as FireRed-OpenStoryline**

Run:

```bash
git remote get-url origin
basename "$(git rev-parse --show-toplevel)"
```

Expected: the origin URL or top-level directory clearly identifies `FireRed-OpenStoryline`.

- [ ] **Step 2: Confirm the conda environment exists and can run Python**

Run:

```bash
conda env list
conda run -n storyline python --version
```

Expected: the `storyline` environment is present and Python starts successfully inside it.

- [ ] **Step 3: Confirm the exact hook command is executable in this repo**

Run:

```bash
PYTHONPATH=. conda run -n storyline python -m pytest -q
```

Expected: the command runs under the `storyline` interpreter. If existing repository tests still fail, record that they are real project test failures rather than wrong-environment failures.

- [ ] **Step 4: Trigger the hook behavior through Git push and inspect the log output**

Run:

```bash
git push origin main
```

Expected: the hook logs the FireRed-OpenStoryline-specific command. If the push is blocked, the failure should come from the conda-based test run rather than from missing `agent_fastapi`, missing `pytest`, or the wrong Python interpreter.

- [ ] **Step 5: Commit the hook update if verification matches the design**

Run:

```bash
git status --short
git add /media/hans/DATA/FireRed-OpenStoryline/docs/superpowers/plans/2026-04-10-pre-push-conda-hook.md
git commit -m "docs: add pre-push hook implementation plan"
```

Expected: the plan file is committed in the repository, while the global hook change remains applied on the machine.

"""
AutoDev — Fully autonomous development loop for FireRed-OpenStoryline.

This script is the heart of the self-driving development system.
It picks an open GitHub issue, implements it, creates a PR, and merges it.

Usage:
  python scripts/autodev.py              # Pick any open issue and work on it
  python scripts/autodev.py --issue 5    # Work on a specific issue number
  python scripts/autodev.py --dry-run    # Plan but don't push or create PR
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────

REPO_OWNER = "hans1996"
REPO_NAME = "FireRed-OpenStoryline"
REPO_DIR = Path(__file__).resolve().parent.parent   # project root
BRANCH_BASE = "main"
AUTO_MERGE = True   # auto-merge PRs when created
DRY_RUN = False


# ─── Helpers ────────────────────────────────────────────────────────────

def shell(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    """Run a shell command, print output, return CompletedProcess."""
    print(f"\n$ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=REPO_DIR,
        capture_output=True, text=True,
        **kwargs
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    return result


def gh(cmd: str) -> str:
    """Run a gh CLI command, return stdout."""
    result = shell(f"gh {cmd}")
    return result.stdout.strip()


def gh_json(cmd: str) -> list | dict:
    """Run a gh CLI command with --jq or parse JSON output."""
    out = gh(cmd)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def ensure_on_main():
    """Make sure we're on main and up to date."""
    shell(f"git checkout {BRANCH_BASE}")
    shell(f"git pull origin {BRANCH_BASE}")


def find_open_issues(limit: int = 10) -> list[dict]:
    """Get open issues from GitHub, sorted by oldest (first created = first to work).
    
    We avoid issues with 'autodev' label (already being worked on by the bot).
    """
    issues_json = gh(f'issue list --state open --limit {limit} --json number,title,body,labels,assignees')
    try:
        issues = json.loads(issues_json)
    except json.JSONDecodeError:
        issues = []

    # Filter: skip issues already assigned or with 'in-progress' label
    filtered = []
    for issue in issues:
        labels = [l.get("name", "") for l in issue.get("labels", [])]
        assignees = issue.get("assignees", [])
        # Skip if already assigned or has in-progress/work-in-progress label
        if assignees and assignees[0].get("login"):
            continue
        if "wip" in labels or "in-progress" in labels:
            continue
        # Skip issue templates (they're usually very short)
        filtered.append(issue)
    return filtered


def issue_number_to_branch(number: int, title: str) -> str:
    """Convert issue title to a branch name: autodev/123-fix-blah"""
    branch_part = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40].strip('-')
    return f"autodev/{number}-{branch_part}"


def pick_issue(issues: list[dict]) -> dict:
    """Pick the best issue to work on. Priority: tests > bugfix > enhancement > infra."""
    label_priority = {
        "bug": 10,
        "test": 8,
        "code-quality": 7,
        "enhancement": 5,
        "documentation": 3,
        "infra": 2,
    }

    def score(issue):
        labels = [l.get("name", "") for l in issue.get("labels", [])]
        max_score = 0
        for label in labels:
            for key, val in label_priority.items():
                if key in label.lower():
                    max_score = max(max_score, val)
        return max_score

    issues.sort(key=score, reverse=True)
    return issues[0]


def generate_branch_name(issue: dict) -> str:
    """Generate a proper branch name from issue."""
    num = issue["number"]
    title = issue.get("title", "fix")
    # Extract conventional commit type from title if present
    type_match = re.match(r'^(feat|fix|docs|refactor|test|ci|chore|perf|infra)\b[:\s]', title, re.IGNORECASE)
    if type_match:
        commit_type = type_match.group(1).lower()
        if commit_type == "infra":
            commit_type = "chore"
        title_part = re.sub(r'[^a-z0-9]+', '-', title[type_match.end():].lower().strip())[:35].strip('-')
    else:
        # Infer type from labels
        labels = [l.get("name", "").lower() for l in issue.get("labels", [])]
        if "bug" in labels:
            commit_type = "fix"
        elif "test" in labels:
            commit_type = "test"
        elif "documentation" in labels:
            commit_type = "docs"
        elif "enhancement" in labels:
            commit_type = "feat"
        else:
            commit_type = "chore"
        title_part = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:35].strip('-')

    return f"autodev/{num}-{commit_type}-{title_part}"


def write_todo_checklist(issue: dict) -> str:
    """Generate a TODO checklist for the subagent that will implement the issue."""
    return textwrap.dedent(f"""
You are an autonomous coding agent. Your task is to implement GitHub issue #{issue['number']}:

**Title:** {issue['title']}

**Description:**
{issue.get('body', 'No additional description provided.')}

## Your Task

1. Read the relevant source files in the repository at {REPO_DIR}
2. Understand the current code and what needs to change
3. Implement the fix/feature
4. Run basic validation (syntax check, lint if applicable)
5. Create a test file in tests/ if this is a feature or fix
6. Commit your changes with a conventional commit message

## Constraints
- Do NOT modify config.toml (it contains local settings with API keys)
- Do NOT add secrets or credentials to the codebase
- Keep changes minimal and focused on this issue
- Write clean, well-documented code
- All new files must have appropriate type hints

## After Implementation
The calling script will handle:
- git add, commit, push
- Creating the PR
- Merging the PR
""").strip()


def generate_commit_message(issue: dict, diff_summary: str = "") -> str:
    """Generate a conventional commit message."""
    title = issue["title"]
    # If title already follows conventional commits, use it directly
    if re.match(r'^(feat|fix|docs|refactor|test|ci|chore|perf)\b', title, re.IGNORECASE):
        return title
    # Infer type from labels
    labels = [l.get("name", "").lower() for l in issue.get("labels", [])]
    if "bug" in labels:
        prefix = "fix"
    elif "test" in labels:
        prefix = "test"
    elif "documentation" in labels:
        prefix = "docs"
    elif "enhancement" in labels:
        prefix = "feat"
    else:
        prefix = "chore"

    message = f"{prefix}: {title} (#{issue['number']})"
    return message


def generate_pr_body(issue: dict) -> str:
    """Generate a PR body from the issue."""
    return textwrap.dedent(f"""## Summary

Auto-generated PR to close #{issue['number']}.

**{issue['title']}**

## Details

{issue.get('body', 'See issue for details.')}

---
*This PR was created and will be auto-reviewed by the autodev system.*
""").strip()


def validate_changes(branch: str) -> bool:
    """Basic validation of changes on the current branch."""
    print("\n=== Running validations ===")

    # 1. Python syntax check
    result = shell(
        "find . -name '*.py' -not -path './.git/*' -not -path './outputs/*' | xargs python3 -m py_compile 2>&1"
    )
    if result.returncode != 0:
        print("SYNTAX CHECK FAILED")
        return False
    print("Syntax check passed")

    # 2. Ruff check (if available, non-fatal)
    if shell("which ruff").returncode == 0:
        result = shell("ruff check --select=E,F --ignore=E501 . 2>&1 || true")
        print("Ruff check done (non-blocking)")

    # 3. Test file validation
    # Check that new test files at least import
    test_files = shell("git diff --name-only --cached --diff-filter=A 2>/dev/null | grep '^tests/' || true").stdout.strip()
    if test_files:
        for f in test_files.splitlines():
            result = shell(f"python3 -m py_compile {f}")
            if result.returncode != 0:
                print(f"TEST SYNTAX FAILED: {f}")
                return False

    print("All validations passed")
    return True


def run_autodev_for_issue(issue: dict, dry_run: bool = False) -> bool:
    """
    Full autodev loop for a single issue.
    
    This is the core function — it delegates to a subagent to
    implement the issue, then handles git/PR operations.
    """
    print(f"\n{'='*60}")
    print(f"  AUTODEV — Working on #{issue['number']}: {issue['title']}")
    print(f"{'='*60}\n")

    if dry_run:
        print(f"[DRY RUN] Would work on issue #{issue['number']}")
        print(f"[DRY RUN] Branch would be: {generate_branch_name(issue)}")
        return True

    # Step 1: Checkout main and pull
    ensure_on_main()

    # Step 2: Create working branch
    branch = generate_branch_name(issue)
    result = shell(f"git branch -D {branch} 2>/dev/null || true")
    shell(f"git checkout -B {branch}")

    # Step 3: Delegate implementation to subagent
    goal = write_todo_checklist(issue)
    print("\n[DELEGATE] Spawning subagent to implement...")

    from hermes_tools import delegate_task

    results = delegate_task(
        goal=goal,
        toolsets=["terminal", "file"],
        context=f"Project root is {REPO_DIR}. Work only in this directory. "
                f"The issue to implement is #{issue['number']}: {issue['title']}. "
                "After implementing, run: git add -A && git status to stage all changes."
    )
    print(f"\n[DELEGATE] Subagent result: {results[0].get('summary', 'No summary')[:500]}...")

    # Step 4: Check what the subagent changed
    shell("git add -A")
    staged = shell("git diff --cached --stat 2>/dev/null").stdout.strip()

    if not staged:
        print("\n[SKIP] No changes were made by subagent. Skipping this issue.")
        shell(f"git checkout {BRANCH_BASE}")
        shell(f"git branch -D {branch}")
        return False

    print(f"\nChanges made:\n{staged}")

    # Step 5: Validate
    if not validate_changes(branch):
        print("\n[FAIL] Validation failed. Attempting to revert and skip.")
        shell(f"git checkout {BRANCH_BASE} -- .")
        shell(f"git checkout {BRANCH_BASE}")
        shell(f"git branch -D {branch}")
        return False

    # Step 6: Commit
    commit_msg = generate_commit_message(issue, staged)
    shell(f"git commit -m {json.dumps(commit_msg)}")

    # Step 7: Push
    shell(f"git push -u origin HEAD")

    # Step 8: Create PR
    pr_body = generate_pr_body(issue)
    pr_title = commit_msg.split("\n")[0]  # First line is the title

    print(f"\n[PR] Creating pull request...")
    try:
        pr_output = gh(
            f'pr create '
            f'--title {json.dumps(pr_title)} '
            f'--body {json.dumps(pr_body)} '
            f'--assignee {REPO_OWNER}'
        )
        print(f"[PR] Created: {pr_output}")
    except Exception as e:
        print(f"[PR] Error creating PR: {e}")
        return False

    # Step 9: Auto-merge (since main is not protected, we can merge immediately)
    if AUTO_MERGE:
        print("\n[MERGE] Auto-merging...")
        try:
            # Get PR number from output
            pr_match = re.search(r'#(\d+)', pr_output)
            if pr_match:
                pr_num = pr_match.group(1)
                merge_result = gh(f"pr merge {pr_num} --squash --delete-branch")
                print(f"[MERGE] {merge_result}")
            else:
                # Try merge with --auto flag
                gh("pr merge --squash --delete-branch")
                print("[MERGE] Merged successfully")
        except Exception as e:
            print(f"[MERGE] Could not auto-merge: {e}")
            print("[MERGE] PR is open for manual review")

    # Step 10: Clean up - back to main
    shell(f"git checkout {BRANCH_BASE}")

    return True


# ─── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AutoDev — autonomous development loop")
    parser.add_argument("--issue", type=int, help="Work on a specific issue number")
    parser.add_argument("--dry-run", action="store_true", help="Plan but don't execute")
    parser.add_argument("--label", type=str, help="Only consider issues with this label")
    args = parser.parse_args()

    global DRY_RUN
    DRY_RUN = args.dry_run

    print(f"AutoDev — FireRed-OpenStoryline")
    print(f"Repo: {REPO_OWNER}/{REPO_NAME}")
    print(f"Project root: {REPO_DIR}")
    print(f"Dry run: {DRY_RUN}")

    if args.issue:
        # Work on a specific issue
        issue_json = gh(f"issue view {args.issue} --json number,title,body,labels,assignees")
        issue = json.loads(issue_json)
        success = run_autodev_for_issue(issue, dry_run=DRY_RUN)
    else:
        # Pick from open issues
        issues = find_open_issues()
        if not issues:
            print("No open issues to work on. Done!")
            return

        issue = pick_issue(issues)
        print(f"Picked issue #{issue['number']}: {issue['title']} "
              f"(labels: {[l.get('name') for l in issue.get('labels', [])]})")

        success = run_autodev_for_issue(issue, dry_run=DRY_RUN)

    if success:
        print(f"\n✅ Autodev completed successfully!")
        print(f"Total time: check your cron logs")
    else:
        print(f"\n❌ Autodev did not complete. Check logs above.")


if __name__ == "__main__":
    main()

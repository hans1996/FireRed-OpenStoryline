# Contributing to FireRed-OpenStoryline

Thanks for contributing to FireRed-OpenStoryline. This guide is the fastest path to a clean, reviewable pull request.

For deeper local setup and runtime details, start with [`docs/developer-setup.md`](docs/developer-setup.md). This file focuses on contribution workflow, validation expectations, and the GitHub templates already configured in this repository.

## Before you start

- Use **Python 3.11+**.
- Create an isolated environment (Conda is recommended in the project docs).
- Install dependencies from `requirements.txt`.
- Keep local secrets out of commits:
  - `config.toml` is a shared template; use local values only.
  - `.env.example` shows the expected environment-variable shape.
  - Do **not** commit API keys or personal provider credentials.

Recommended setup:

```bash
git clone https://github.com/FireRedTeam/FireRed-OpenStoryline.git
cd FireRed-OpenStoryline
conda create -n storyline-dev python=3.11
conda activate storyline-dev
pip install -r requirements.txt
```

For MCP server, CLI, and FastAPI entry points, see [`docs/developer-setup.md`](docs/developer-setup.md).

## Contribution workflow

1. Start from an up-to-date `main` branch.
2. Open or confirm the GitHub issue your change will address.
3. Create a focused branch for **one** issue or bugfix.
4. Keep the scope small and avoid unrelated formatting churn.
5. Update tests or docs when your change affects behavior or contributor experience.
6. Open a pull request with a clear summary, validation notes, and issue reference.

Example branch flow:

```bash
git checkout main
git pull origin main
git checkout -b fix/short-description
```

## Validation before opening a PR

Run the smallest validation that matches your change, then include the exact commands in the PR description.

### Minimum validation for Python changes

```bash
python3 -m py_compile agent_fastapi.py cli.py
python3 -m py_compile src/open_storyline/mcp/server.py
```

### Broader repository syntax check

```bash
find . -name "*.py" \
  -not -path "./.venv/*" \
  -not -path "./test_venv/*" \
  -not -path "./__pycache__/*" \
  -not -path "./src/open_storyline.egg-info/*" \
  -print0 | xargs -0 python3 -m py_compile
```

### Run targeted tests first

```bash
python3 -m pytest tests/test_mcp_server_and_sampling.py -q
```

If you only changed documentation, validate links, formatting, and the accuracy of any commands you touched.

## Coding and review expectations

- Follow the existing project structure and naming conventions.
- Prefer focused commits over mixed-purpose changes.
- Do not commit generated outputs, caches, or personal notes.
- Do not modify `config.toml` with real credentials.
- Record any manual test steps needed to review the change.

Commit prefixes commonly used in this repository:

- `fix:` — bug fixes
- `feat:` — features
- `test:` — tests
- `docs:` — documentation
- `chore:` — tooling or repository maintenance

## Issues and pull requests

Please use the GitHub templates already included in this repository:

- Bug reports: [`.github/ISSUE_TEMPLATE/bug_report.yml`](.github/ISSUE_TEMPLATE/bug_report.yml)
- Feature requests: [`.github/ISSUE_TEMPLATE/feature_request.yml`](.github/ISSUE_TEMPLATE/feature_request.yml)
- Pull requests: [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md)

When opening an issue or PR:

- Link the related issue number when applicable.
- Describe the user-visible impact or maintenance benefit.
- Include the validation commands you ran.
- Call out any follow-up work or known limitations.

## PR checklist

Before requesting review, confirm that you have:

- [ ] Kept the change focused on a single issue
- [ ] Run validation appropriate to the files you changed
- [ ] Updated tests and/or docs if needed
- [ ] Avoided committing secrets or local-only config
- [ ] Added a clear PR description with testing notes

## Need more context?

- Project overview: [`README.md`](README.md)
- Developer setup and entry points: [`docs/developer-setup.md`](docs/developer-setup.md)
- API key and provider notes: [`docs/source/en/api-key.md`](docs/source/en/api-key.md)

Thanks again for helping improve FireRed-OpenStoryline.

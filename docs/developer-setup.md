# Developer Setup Guide

This guide is for contributors who want to run FireRed-OpenStoryline locally, inspect the MCP server, and validate code changes before opening a pull request.

## Prerequisites

- Python 3.11 or newer
- Conda or another virtual-environment tool
- `ffmpeg` available on your machine for media workflows
- Access to the model providers you plan to test (LLM, VLM, Pexels, and optional TTS / transition providers)

## 1. Create a local environment

The main README uses Conda in its install instructions, so the same setup is recommended for development:

```bash
git clone https://github.com/FireRedTeam/FireRed-OpenStoryline.git
cd FireRed-OpenStoryline
conda create -n storyline-dev python=3.11
conda activate storyline-dev
pip install -r requirements.txt
```

If you prefer another environment manager, the important requirement is to use Python 3.11+ and install the repository dependencies from `requirements.txt`.

## 2. Configure local secrets

Keep your local credentials in `config.toml` and any provider-specific environment variables in `.env` if needed.

Important notes:

- `config.toml` in the repository is the shared template; fill in your own values locally.
- Do **not** commit secrets.
- Many development tasks can be validated without real keys, but end-to-end MCP and web runs require valid provider settings.

Useful files:

- `config.toml` — project paths, MCP server settings, provider blocks
- `.env.example` — example environment variables
- `docs/source/en/api-key.md` — provider setup reference

## 3. Learn the main entry points

The project has two primary runtime entry points plus a standalone MCP server:

### MCP server

```bash
PYTHONPATH=src python -m open_storyline.mcp.server
```

This loads settings from `config.toml`, creates the FastMCP server, and registers the configured node tools from `src/open_storyline/mcp/register_tools.py`.

### CLI chat interface

```bash
python cli.py
```

Use this when you want to interact with the agent from the terminal.

### FastAPI web interface

```bash
uvicorn agent_fastapi:app --host 127.0.0.1 --port 8005
```

Use this when you want to validate the browser experience or API endpoints.

## 4. Know where to make changes

A quick map of the most important contributor-facing files:

- `src/open_storyline/agent.py` — high-level agent orchestration
- `src/open_storyline/config.py` — settings models and config loading
- `src/open_storyline/mcp/` — MCP server, tool registration, sampling hooks
- `src/open_storyline/nodes/` — workflow nodes for media search, script generation, planning, and rendering
- `src/open_storyline/storage/` — session and artifact persistence
- `agent_fastapi.py` — web application and API routes
- `cli.py` — terminal entry point
- `tests/` — regression coverage

## 5. Validate changes before opening a PR

At minimum, run syntax checks on any Python files you changed:

```bash
python3 -m py_compile agent_fastapi.py cli.py
python3 -m py_compile src/open_storyline/mcp/server.py
```

For broader validation, compile the whole repository while excluding virtual environments and generated metadata:

```bash
find . -name "*.py" \
  -not -path "./.venv/*" \
  -not -path "./test_venv/*" \
  -not -path "./__pycache__/*" \
  -not -path "./src/open_storyline.egg-info/*" \
  -print0 | xargs -0 python3 -m py_compile
```

The test suite lives under `tests/`. Run the targeted tests for the area you touched first, then expand if your change affects shared behavior.

Example:

```bash
python3 -m pytest tests/test_mcp_server_and_sampling.py -q
```

## 6. Recommended pull-request workflow

1. Start from an up-to-date `main` branch.
2. Create a focused branch for one issue.
3. Keep changes minimal and avoid unrelated formatting churn.
4. Do not modify `config.toml` with personal keys.
5. Include the exact validation commands you ran in the PR description.

Commit prefixes used in this repository:

- `fix:` — bug fixes
- `feat:` — features
- `test:` — tests
- `docs:` — documentation
- `chore:` — tooling or repository maintenance

## 7. Common development pitfalls

- The MCP server imports tools from configured node packages, so config changes can affect what tools are exposed.
- The web UI and MCP server can both depend on local provider credentials; syntax-only checks are useful when secrets are unavailable.
- Generated outputs are written under `outputs/` and cache data under `.storyline/`.
- Keep commits focused on tracked project files only; local drafts and personal notes should stay untracked.

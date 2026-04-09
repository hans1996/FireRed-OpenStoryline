# TODO / Roadmap — FireRed-OpenStoryline

Auto-generated on 2026-04-07. Refreshed on 2026-04-10 to reflect completed tracked work in the repository.

---

## Infrastructure (P0)

- [x] #1 — Enable GitHub Issues on fork repo
- [x] #2 — Add GitHub Actions CI workflow (lint + syntax check)
- [x] #3 — Add ruff/pylint to CI and enforce linting on PRs
- [x] #4 — Add pytest integration test to CI
- [ ] #5 — Add CONTRIBUTING.md
- [ ] #6 — Add CODE_OF_CONDUCT.md

## Tests (P0 — Critical)

- [x] #7 — Add test for agent_fastapi.py ChatSession lifecycle
- [x] #8 — Add test for MCP server / sampling handler
- [x] #9 — Add test for node_manager (node registration and execution order)
- [x] #10 — Add test for plan_timeline nodes (AI + Pro variants)
- [x] #11 — Add test for ffmpeg_utils
- [x] #12 — Add test for media_handler
- [x] #13 — Add test for session_manager and agent_memory
- [x] #14 — Add test for skills_io
- [x] #15 — Add test for all node input/output schemas
- [x] #16 — Add test for config loading (config.toml + .env)
- [x] #17 — Add test for webhook / AI transition client
- [x] #18 — Add test for CLI entry points

## Code Quality (P1)

- [x] #19 — Implement compress_log parameter in node_summary (marked as TODO)
- [ ] #20 — Review and fix all 33 TODO/FIXME/HACK comments in the codebase
- [x] #21 — Add type hints to agent_fastapi.py (currently minimal typing)
- [x] #22 — Add type hints to cli.py
- [ ] #23 — Standardize imports across all modules (ruff: isort)
- [ ] #24 — Replace bare `except:` clauses with specific exception types
- [ ] #25 — Add docstrings to all public functions and classes

## Features (P1)

- [ ] #26 — Add support for custom node plugins (plugin architecture)
- [ ] #27 — Add progress callback / WebSocket streaming for long-running tasks
- [ ] #28 — Add video preview endpoint in FastAPI
- [ ] #29 — Add batch processing mode (multiple prompts in one run)
- [ ] #30 — Add export/import session as JSON for reproducibility
- [ ] #31 — Add undo/redo support for session editing
- [ ] #32 — Add support for multi-language subtitles in output video

## Documentation (P1)

- [x] #33 — Add API documentation (OpenAPI/Swagger for FastAPI endpoints)
- [ ] #34 — Add node architecture diagram in docs/
- [ ] #35 — Add developer setup guide (not just end-user)
- [ ] #36 — Add MCP tool documentation — what tools are available and how to extend
- [ ] #37 — Add changelog (CHANGELOG.md)
- [ ] #38 — Translate CONTRIBUTING.md to Chinese

## Bug Fixes (P2)

- [ ] #39 — Fix hardcoded paths (e.g., /media/hans/... in test file)
- [x] #40 — Ensure .env is never committed (add to .gitignore if missing)
- [ ] #41 — Fix fork sync — keep up to date with upstream FireRedTeam/FireRed-OpenStoryline

## Performance (P2)

- [ ] #42 — Profile and optimize plan_timeline node (likely longest-running)
- [ ] #43 — Add caching for LLM responses (repeat prompts)
- [ ] #44 — Optimize ffmpeg_utils for large video files
- [ ] #45 — Add GPU memory monitoring and auto-unload logic

## Security (P2)

- [ ] #46 — Add rate limiting to FastAPI endpoints
- [ ] #47 — Validate and sanitize all user upload file types
- [ ] #48 — Add authentication option for deployment (API key or OAuth)
- [ ] #49 — Review all subprocess calls for injection vulnerabilities

## Chores (P3)

- [x] #50 — Add pre-commit hook config (pre-commit.yaml)
- [ ] #51 — Add editorconfig for consistent formatting
- [ ] #52 — Remove unused files from __pycache__/
- [x] #53 — Clean up .env.example with all required variables
- [ ] #54 — Add issue templates (bug report, feature request)
- [ ] #55 — Add PR template

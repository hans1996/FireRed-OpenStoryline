# MCP Tools and Extension Guide

This document explains which MCP tools FireRed-OpenStoryline exposes by default, how those tools are registered, and how contributors can safely add new ones.

## Overview

The project exposes editing capabilities through a local FastMCP server. When you run:

```bash
PYTHONPATH=src python -m open_storyline.mcp.server
```

`src/open_storyline/mcp/server.py` loads `config.toml`, creates a `FastMCP` server, and calls `src/open_storyline/mcp/register_tools.py` to register the tool surface.

There are two categories of MCP tools:

1. **Node-backed tools** — generated from classes under `src/open_storyline/nodes/`
2. **Built-in helper tools** — registered directly inside `register_tools.py`

## Default MCP tools

By default, the repository exposes the node packages and node names listed under `[local_mcp_server]` in `config.toml`.

### Default node-backed tools

These names come from the default `available_nodes` list in `config.toml`:

- `load_media`
- `search_media`
- `split_shots`
- `local_asr`
- `speech_rough_cut`
- `generate_ai_transition`
- `understand_clips`
- `filter_clips`
- `group_clips`
- `generate_script`
- `generate_voiceover`
- `select_bgm`
- `recommend_transition`
- `recommend_text`
- `plan_timeline_pro`
- `plan_timeline_ai_transition`
- `render_video`

There is also a node class named `ScriptTemplateRecomendation` in the config list. Its exported tool name comes from `NodeMeta.name`, which is `script_template_rec`.

The exact tool name exposed to MCP is always the `meta.name` value on the node class, not the Python class name.

### Built-in helper tools

`src/open_storyline/mcp/register_tools.py` also registers two helper tools directly:

- `read_node_history` — load a prior node result by `artifact_id`
- `write_skills` — persist generated skill markdown to the configured skill directory

## How node-backed tools are registered

The registration path is:

1. `create_server()` in `src/open_storyline/mcp/server.py` creates `FastMCP`
2. `register(server, cfg)` in `src/open_storyline/mcp/register_tools.py` scans configured node packages
3. The registry imports modules to trigger `@NODE_REGISTRY.register()` decorators
4. Each configured node class is instantiated with `Settings`
5. `create_tool_wrapper()` converts the node into an MCP-compatible async tool function
6. FastMCP registers the wrapper with the node's `meta.name` and `meta.description`

Important implementation details:

- `NODE_REGISTRY.scan_package()` imports every module inside each configured package.
- The MCP wrapper reads request headers and extracts `X-Storyline-Session-Id`.
- Request arguments are merged with FastMCP-injected keyword arguments before node execution.
- `input_schema.model_fields` are converted into keyword-only MCP parameters using `Annotated[...]`, so Pydantic field metadata becomes tool schema descriptions.
- The wrapper creates a `NodeState` with `artifact_id`, language, session data, and an MCP-aware LLM client.

## Configuration knobs that control the MCP surface

The most important `[local_mcp_server]` fields in `config.toml` are:

- `server_name` — the FastMCP server name
- `server_transport` — transport type (`stdio`, `sse`, or `streamable-http`)
- `connect_host`, `port`, `path`, `url_scheme` — connection settings
- `inline_media` — media transport policy (`auto`, `always`, `never`)
- `available_node_pkgs` — Python packages to scan for node classes
- `available_nodes` — node class names to expose as MCP tools
- `server_cache_dir` — artifact and cache storage used during tool execution

If a node exists in the codebase but is not listed in `available_nodes`, it will not be exposed to MCP clients by default.

## How to add a new MCP tool

The preferred path is to add a new node-backed tool.

### 1. Create or update a node class

Add a node class under a scanned package such as `src/open_storyline/nodes/core_nodes/`.

A node should:

- inherit from `BaseNode`
- be decorated with `@NODE_REGISTRY.register()`
- define `meta = NodeMeta(...)`
- define `input_schema`
- implement its async processing logic

Minimal shape:

```python
from open_storyline.nodes.core_nodes.base_node import BaseNode, NodeMeta
from open_storyline.utils.register import NODE_REGISTRY

@NODE_REGISTRY.register()
class MyNode(BaseNode):
    meta = NodeMeta(
        name="my_tool",
        description="Describe what the tool does",
        node_id="my_tool",
        node_kind="my_tool",
    )
    input_schema = MyInputSchema
```

### 2. Add the node to config

Make sure the package is listed in `available_node_pkgs` and the class name is listed in `available_nodes`.

For example:

```toml
[local_mcp_server]
available_node_pkgs = ["open_storyline.nodes.core_nodes"]
available_nodes = ["LoadMediaNode", "MyNode"]
```

### 3. Restart the MCP server

The registry scan runs at startup. Restart the server after changing node packages, node classes, or MCP-related config.

### 4. Add validation

When adding or changing node-backed MCP tools, update or add tests under `tests/` for the registration path, schema, or runtime behavior.

## When to use a built-in helper instead

If the functionality is not a workflow node and does not need the full `BaseNode` lifecycle, you can register a direct FastMCP helper inside `src/open_storyline/mcp/register_tools.py`.

This is how the project currently implements:

- `read_node_history`
- `write_skills`

Use this approach for narrow utility helpers that operate on server context or persisted artifacts rather than the main editing graph.

## Contributor tips and pitfalls

- The MCP tool name comes from `NodeMeta.name`, so keep it stable once clients depend on it.
- Class registration and MCP exposure are separate: `@NODE_REGISTRY.register()` makes a node discoverable, while `available_nodes` determines whether it is actually exposed.
- Session-aware behavior depends on the `X-Storyline-Session-Id` header. Avoid bypassing the wrapper if you need artifact isolation.
- Media transport behavior changes with `inline_media`; local and remote MCP setups may exercise different payload paths.
- Built-in helpers in `register_tools.py` should still return structured dictionaries that match the rest of the tool ecosystem.

## Related files

- `src/open_storyline/mcp/server.py`
- `src/open_storyline/mcp/register_tools.py`
- `src/open_storyline/config.py`
- `src/open_storyline/utils/register.py`
- `src/open_storyline/nodes/core_nodes/base_node.py`
- `tests/test_mcp_server_and_sampling.py`

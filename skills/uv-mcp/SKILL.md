---
name: uv-mcp
description: Inspect / manage uv workspaces, venvs, lockfiles via the uv-mcp server at `http://uv-mcp:9002/sse`. Use when the user types `/uv-mcp <tool> [args]`, asks about workspace members, dependency state, lockfile drift, or env inspection in the neuro-harness monorepo. Trigger on phrases like "what's in my uv workspace", "is the lockfile current", "list workspace members", "what version of X is pinned", or any uv-specific introspection request.
---

# /uv-mcp

Shortcut to the uv-mcp server (`http://uv-mcp:9002/sse`). Exposes uv's workspace + venv state to agents over MCP.

## How it works

```bash
docker compose exec -T app uvx mcp2cli --mcp http://uv-mcp:9002/sse <tool> --args '<k=v>...'
```

Tool list:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://uv-mcp:9002/sse --list
```

Common tools (subset — check `--list` for the live set):

- `list_workspace_members`
- `list_dependencies` — for a member
- `lockfile_status` — drift between pyproject + uv.lock
- `env_state` — which venv, which python, which packages

## Examples

- `/uv-mcp list_workspace_members`
- `/uv-mcp lockfile_status`
- `/uv-mcp env_state`

## When NOT to use

- For *editing* uv config / lockfile: use Read + Edit + `uv lock` directly. `/uv-mcp` is read-only-ish inspection.
- For *running* code: just `uv run …` from the host or app container.

## Companions

- `/forge`, `gitnexus-*` skills (codebase structure), `relentless-inception` (uv-workspaces / uv-package agents within the orchestrator)

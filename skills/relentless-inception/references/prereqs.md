# Prerequisites

The skill expects the following tools and credentials. The entrypoint runs `scripts/check_prereqs.sh` first and refuses to start if anything's missing, surfacing the remediation hint.

---

## Tools

| Tool        | Why                                                     | Install                                       |
|-------------|---------------------------------------------------------|-----------------------------------------------|
| claude-code | This is a Claude Code skill                              | already present if you're reading this        |
| codex       | adversarial-review + rescue model routing               | run the `codex:setup` skill                   |
| uv          | shipping, member install                                 | `curl -LsSf https://astral.sh/uv/install.sh \| sh`  |
| dagger      | Una + Dagger shipping ladder                             | `curl -fsSL https://dl.dagger.io/dagger/install.sh \| sh` |
| docker      | live containerized testing                               | Docker Desktop or compatible engine            |
| tmux        | rescue-mode relay (relentless_relay.sh)                  | `brew install tmux`                            |
| jq          | ship-report parsing, status line                         | `brew install jq`                              |
| git         | obvious                                                  | usually preinstalled                           |

## Credentials

| Env var               | Required? | Used for                                                  |
|-----------------------|-----------|-----------------------------------------------------------|
| OPENROUTER_API_KEY    | yes       | gpt-5.5, gemini-latest, gpt-pro-latest, gpt-latest routes |
| ANTHROPIC_API_KEY     | usually*  | opus-* routes outside Claude Code's built-in routing      |
| GITHUB_TOKEN          | optional  | PR creation, GitHub Actions kickoff                        |
| TEMPORAL_API_KEY      | optional  | only for `--exec=skynet` with Temporal Cloud              |
| HF_TOKEN              | optional  | Hugging Face MCP access                                    |

*Inside Claude Code with API keys configured via `/login`, this is set automatically.

Place credentials in `~/.claude/.env` (gitignored by default) OR export them in the shell before invoking. The skill never reads, logs, or echoes a credential value — only its presence.

---

## MCPs

These MCP servers are expected to be reachable. The skill works with reduced functionality when one is missing, but features depending on a missing MCP are skipped:

| MCP             | Required for                                             | Reduced-mode if missing                       |
|-----------------|----------------------------------------------------------|------------------------------------------------|
| git-nexus       | architecture-analyzer's inverse-engineering pass        | analyzer runs without cross-repo symbol search |
| context7        | planner's current-docs lookups                          | planner uses its training-data knowledge only  |
| mcp2cli         | kitchen-sink-monorepo's CLI-ref generation              | mode unavailable                                |
| infranodus      | Obsidian/graph visualization                             | tearsheet has no graph view                     |
| serena          | symbolic code search inside the orchestrator             | falls back to grep/Read                         |

Configure MCPs in `~/.claude/settings.json` under the `mcpServers` key OR (preferred) federate them through ContextForge. The neuro-harness project's `config/contextforge/virtual-server.yaml` registers most of them already.

---

## External skills the orchestrator may invoke

The orchestrator can delegate to other installed skills when appropriate:

- `codex:adversarial-review` — used for gate evaluation
- `codex:codex-rescue` — used for the rescue consortium's codex-side agent
- `docs-dual-lookup` — used when an agent role needs library docs
- `parallel-web` / `perplexity-search` / `research-lookup` — used by architecture-analyzer for upstream comparisons
- `deep-tool-wiki` — used when the orchestrator hits a HyperFrequency-forked tool it doesn't know

None of these are strictly required, but their absence reduces the quality of the relevant step.

---

## Run check

Before kicking off a run:

```bash
bash ~/.claude/skills/relentless-inception/scripts/check_prereqs.sh
```

Exit code 0 = ready. Non-zero = print remediation hints and refuse. The orchestrator entrypoint runs this automatically.

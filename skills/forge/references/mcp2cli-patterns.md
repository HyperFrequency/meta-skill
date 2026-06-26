# mcp2cli patterns for cross-MCP workflows

Three patterns cover most multi-MCP work:

## 1. Discover-then-dispatch

When you don't know the tool name:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://turbovault:9004/sse --list
docker compose exec -T app uvx mcp2cli --mcp http://turbovault:9004/sse <tool> --args 'k=v'
```

For interactive exploration of a fresh server. Cache the `--list` output in
your reply so the user sees what's available without re-querying.

## 2. Parallel fan-out (one MCP, many invocations)

When the same MCP needs to be called N times with different args (e.g.,
search 5 queries in parallel):

```bash
docker compose exec -T app bash -lc '
  for q in "agentic patterns" "MCP federation" "pine script v5" "uv workspaces" "temporal workflows"; do
    uvx mcp2cli --mcp http://turbovault:9004/sse search --args "query=$q" &
  done
  wait
'
```

Stream-friendly. Catch backpressure by capping parallelism (use `xargs -P`
or `parallel`).

## 3. Pipeline across MCPs

When a deliverable chains servers — the canonical example being:

  parallel-web-search  →  vault-ingest (turbovault)  →  graph-build (infranodus)

This is what `/scrape-ingest-organize` automates. The shape:

```bash
# Step 1: parallel scrape (uses Parallel Web API or whatever scraper is configured)
SCRAPE_OUT=$(uvx mcp2cli --mcp <scraper> scrape --args 'urls=[...]')

# Step 2: ingest each result as a note in the vault
echo "$SCRAPE_OUT" | jq -c '.[]' | while read -r entry; do
  uvx mcp2cli --mcp http://turbovault:9004/sse write_note \
    --args "title=$(echo "$entry" | jq -r .title)&body=$(echo "$entry" | jq -r .body)"
done

# Step 3: ask turbovault to organize (tagging, link-suggestion, etc.)
uvx mcp2cli --mcp http://turbovault:9004/sse organize_recent --args 'since=24h'

# Step 4: build an ontology over the new notes via infranodus
uvx mcp2cli --mcp http://infranodus-mcp:9005/sse generate_knowledge_graph \
  --args 'source=vault&since=24h'
```

Each step's output feeds the next. The workflow skill bundles this with
error handling, logging, and partial-resume.

## Common mistakes

- **Quoting JSON args** — mcp2cli passes args as key=value strings;
  values containing special chars need shell-quoting. Use `--args-json` if
  the value is a JSON object.
- **Long-running tools** — some MCP tools take minutes (knowledge-graph
  build). Don't run them in the user's foreground without setting
  expectations; consider streaming or background mode.
- **Auth differences** — direct-to-bridge URLs (e.g., http://gitnexus:9001/sse)
  are unauthenticated inside the compose network. The gateway at
  http://localhost:4444 IS auth-gated. Stick to the in-network URLs when
  running from inside the app container.

## Composing skills, not just commands

`/forge` is the floor — the bare CLI surface. Workflow skills like
`/scrape-ingest-organize` are the ceiling. The pattern: a workflow skill
plans the chain (which MCPs, in what order, with what args), calls `/forge`
for each step, and surfaces the composed result.

For one-off composition, an agent can write a small bash script (like the
ones above) and run it via Bash. For repeated workflows, capture the chain
as a new skill (`/skill-creator` builds them).

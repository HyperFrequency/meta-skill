---
name: doc-sync-embed-verify
description: Document changes across the HyperFrequency tool ecosystem, update knowledge graphs and reasoning ontologies in Obsidian + InfraNodus, sync the deep-tool-wiki repo to Devin DeepWiki, and check all 14+ upstream tool repos for documentation updates that need re-ingestion. Use when any HyperFrequency tool changes, when upstream releases new versions, when the user says "sync docs", "update the wiki", "check for doc updates", or on a scheduled cadence. Also triggered automatically by the PostToolUse hook on git push to deep-tool-wiki and by the GitHub Action on PR merge.
---

# /doc-sync-embed-verify

Unified documentation lifecycle management for the HyperFrequency tool ecosystem. This skill handles the full loop: detect changes → document → update knowledge graphs → sync → verify.

## What it does (5-phase pipeline)

### Phase 1: DETECT — Check for upstream doc changes

For each of the 14 indexed tools, check whether the upstream repo's docs have changed since last ingestion:

```bash
# For each tool, compare the upstream's latest commit on docs/ + README against the stored ingestion date
for tool in optuna nautilus-trader vectorbtpro nautilus-admin mlflow h2o-3 tardis-python qlib featuretools tsfel hftbacktest hyper-stats xfeat alpha-factory; do
  # Read the ingestion date from the wiki frontmatter
  ingested=$(grep "^ingested:" ~/Desktop/auto-brain/deep-tool-wiki/${tool}/wiki.md | head -1 | awk '{print $2}')
  
  # Get the upstream repo from frontmatter
  upstream=$(grep "^upstream:" ~/Desktop/auto-brain/deep-tool-wiki/${tool}/wiki.md | head -1 | sed 's/upstream: *//')
  
  # Check if upstream has new commits since ingestion
  gh api "repos/${upstream}/commits?since=${ingested}T00:00:00Z&path=docs" --jq 'length' 2>/dev/null
  gh api "repos/${upstream}/commits?since=${ingested}T00:00:00Z&path=README.md" --jq 'length' 2>/dev/null
done
```

Tools with significant changes (>5 commits touching docs/) are flagged for re-ingestion.

### Phase 2: DOCUMENT — Re-ingest stale tools

For each flagged tool:
1. Re-clone upstream docs via `~/.claude/scripts/deep-tool-wiki.py clone`
2. Re-fetch DeepWiki content via `mcp2cli --mcp https://mcp.deepwiki.com/mcp read-wiki-contents`
3. Re-scrape the documentation website
4. Re-fetch YouTube transcript (if a newer/better tutorial exists)
5. Spawn a Sonnet agent to re-synthesize the wiki body (1500+ lines)
6. Spawn an Opus agent to regenerate the dual reasoning ontology

The re-ingested wiki.md replaces the old one in `~/Desktop/auto-brain/deep-tool-wiki/<tool>/wiki.md`.

### Phase 3: EMBED — Update knowledge graphs + ontologies

For each re-ingested tool:
1. **InfraNodus**: Delete the old graph and create a new one under the same name (`deep-tool-wiki-<tool>`):
```bash
INFRANODUS_API_KEY="..." mcp2cli --mcp-stdio "npx -y infranodus-mcp-server" \
  create-knowledge-graph \
  --graph-name "deep-tool-wiki-<tool>" \
  --modify-analyzed-text extractEntitiesOnly \
  --text "$(cat /tmp/dtw-<tool>-ontology.txt)" \
  --context "Re-ingesting updated reasoning ontology for <tool> after upstream doc changes detected by doc-sync-embed-verify"
```

2. **Obsidian**: Replace the curated page at `/Library/Obsidian-Vault/Auto-Quant/DeepTools/<tool>.md` with updated overview + why-use + quick-start + cross-links + full dual ontology.

3. **Index page**: Regenerate `_DeepTools-Index.md` with the union ontology:
```bash
python3 ~/.claude/scripts/deep-tool-wiki.py update-index
```

### Phase 4: SYNC — Push to GitHub + trigger Devin DeepWiki re-index

1. Commit changed wiki files to the local repo:
```bash
cd ~/Desktop/auto-brain/deep-tool-wiki
git add -A
git commit -m "docs: re-ingest <tool1>, <tool2>, ... via /doc-sync-embed-verify

Upstream doc changes detected since last ingestion.
Re-synthesized wiki bodies, regenerated dual ontologies,
persisted updated InfraNodus graphs."
git push origin main
```

2. Trigger Devin DeepWiki re-index (it auto-detects pushes if the repo is connected; otherwise ping via MCP):
```bash
mcp2cli --mcp https://mcp.devin.ai/mcp \
  --auth-header "Authorization:Bearer cog_..." \
  ask-question --repo-name HyperFrequency/deep-tool-wiki \
  --question "What tools were recently updated?"
```
This forces a re-read which triggers re-indexing.

3. **Update Augment Code workspace index** — ensure each re-ingested tool's upstream repo is indexed by auggie for semantic code search:
```bash
# For each updated tool, auggie indexes the upstream repo
mcp2cli --mcp https://api.augmentcode.com/mcp \
  --auth-header "Authorization:Bearer ..." \
  augment-code-search --repo-owner <upstream-org> --repo-name <upstream-repo> \
  --query "main entry point and core API surface"
```
This primes auggie's index. If the repo isn't indexed yet, auggie will suggest adding it.

4. **Update Context7** — query Context7 with the upstream library name to confirm it's still indexed:
```bash
mcp2cli --mcp-stdio "npx -y @upstash/context7-mcp" resolve-library-id \
  --library-name <tool-name> --query "core API overview"
```
If Context7 doesn't have the library, note it in the report (no programmatic add available).

### Phase 5: VERIFY — Confirm consistency

After sync, verify:
1. **Git state**: `git status` clean, `git log --oneline -1` matches expected commit
2. **File integrity**: Each tool's wiki.md has frontmatter, both ontology sections, >1500 lines
3. **InfraNodus graphs exist**: For each updated tool, query `analyze-existing-graph-by-name` to confirm the graph is accessible
4. **Obsidian pages updated**: Check modification timestamps on `/Library/Obsidian-Vault/Auto-Quant/DeepTools/<tool>.md`
5. **DeepWiki accessible**: `mcp2cli ... read-wiki-structure --repo-name HyperFrequency/deep-tool-wiki` returns the expected topic list
6. Report: list of tools checked, tools re-ingested, tools unchanged, any failures

## When to use

- **Manually**: User says "sync docs", "update the wiki", "check for updates", "refresh all tools"
- **Automatically**: Triggered by:
  - `PostToolUse` hook on `git push` to deep-tool-wiki
  - GitHub Action on PR merge to deep-tool-wiki
  - Scheduled cron (via `/schedule`) — recommended: weekly
- **Per-tool refresh**: User says "refresh optuna" or "update nautilus-trader docs" — runs the pipeline for just that tool

## When NOT to use

- For querying existing docs → use `/deep-tool-wiki`
- For adding a brand new tool → use the fork auto-ingest hook first, then `/doc-sync-embed-verify` to polish

## Infrastructure context

The user's environment:
- **Local server**: 2× 192-core CPUs (384 cores total)
- **Extensible to cloud**: Ray cluster, Dask distributed, or Kubernetes for burst
- For distributed nautilus_trader backtests with optuna: RDBStorage (PostgreSQL) + one worker per core + optional Ray/Dask for cloud burst

Tools documented in the deep-tool-wiki that support this distributed workflow:
- **optuna** — trial coordination via RDBStorage
- **Ray** — distributed execution, Ray Tune integration with optuna
- **Dask** — distributed DataFrames + optuna DaskStorage
- **PostgreSQL** — shared RDBStorage backend for optuna distributed trials
- **GNU Parallel** — lightweight worker orchestration for bash-level parallelism

## Output format

When invoked, report:

```
## /doc-sync-embed-verify report

**Checked:** 14 tools
**Stale (re-ingested):** optuna (47 new commits), mlflow (23 new commits)
**Up-to-date:** 12 tools
**InfraNodus graphs updated:** deep-tool-wiki-optuna, deep-tool-wiki-mlflow
**Obsidian pages updated:** optuna.md, mlflow.md, _DeepTools-Index.md
**Git:** pushed commit abc1234 to HyperFrequency/deep-tool-wiki
**DeepWiki:** re-index triggered for HyperFrequency/deep-tool-wiki
**Verification:** all checks passed ✓
```

## Quick invocation

```
/doc-sync-embed-verify              # full pipeline, all 14 tools
/doc-sync-embed-verify optuna       # single tool refresh
/doc-sync-embed-verify --check-only # detect stale tools without re-ingesting
/doc-sync-embed-verify --force      # re-ingest all tools regardless of staleness
```

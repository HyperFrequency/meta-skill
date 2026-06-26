---
name: scrape-ingest-organize
description: End-to-end research pipeline that scrapes the web in parallel, ingests results into the Obsidian vault as linted notes, organises them via TurboVault, and builds an ontology / topical-cluster view via InfraNodus. Use when the user says "scrape and ingest", "scrape ingest organize", "research pipeline", "build me a graph from these URLs", "do my research on X and put it in my vault", or any phrasing that implies "go find this stuff and turn it into structured knowledge in my notes". Composes /forge calls across parallel-web, turbovault, and infranodus into one workflow with logging + partial-resume.
---

# /scrape-ingest-organize

The canonical multi-MCP workflow. Demonstrates the `/forge` composition pattern end-to-end.

## What it does

```
parallel-web  →  vault-ingest (turbovault)  →  organise (turbovault)  →  ontology-build (infranodus)
     ↓                    ↓                          ↓                          ↓
 N search results    N new notes in            tags + links             knowledge graph
                     ~/Vaults/neuro-quant-     auto-applied             + topical clusters
                     vault/00-raw/
```

## Step-by-step

### 1. Parallel scrape

Use the existing `parallel-web` or `perplexity-search` skill (don't reinvent — they're already installed). Fan out N queries; each returns a structured result (title, URL, content, citations).

```bash
# Conceptual; the actual scraping skill owns the API call.
# Output: scrape-results.json — array of {url, title, content, citations[]}
```

Recommended: 3–8 parallel queries. More than that and you're hammering rate limits.

### 2. Ingest each result as a vault note

For each scrape result, create a note in `~/Vaults/neuro-quant-vault/00-raw/` via TurboVault:

```bash
jq -c '.[]' scrape-results.json | while read -r r; do
  title=$(echo "$r" | jq -r .title)
  body=$(echo "$r" | jq -r '"\(.content)\n\n---\nsource: \(.url)\n"')
  docker compose exec -T app uvx mcp2cli --mcp http://turbovault:9004/sse \
    write_note --args "path=00-raw/$(echo "$title" | tr -cs 'A-Za-z0-9' -).md" --args "body=$body"
done
```

Each note lands in `00-raw/`. The `00-raw/` folder is the "inbox" — per the user's vault convention, content moves through `00-raw → 01-sorted → 02-KB-main` as it gets organised.

### 3. Organise (TurboVault)

Apply tags + suggest wikilinks across the newly-ingested batch:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://turbovault:9004/sse \
  organize_recent --args 'since=10m' --args 'apply_tags=true' --args 'suggest_links=true'
```

This applies TurboVault's auto-tagger + link-suggester to anything modified in the last 10 minutes. Output: per-note tag + link additions.

### 4. Ontology build (InfraNodus)

Build a knowledge graph + topical clusters over the new batch:

```bash
docker compose exec -T app uvx mcp2cli --mcp http://infranodus-mcp:9005/sse \
  analyze_text --args 'source=vault' --args 'paths=00-raw/' --args 'cluster=true'
```

Result: a graph file dropped at `~/neuro-harness/runtime/graphs/infranodus/<run-id>.json` — which is symlinked into the vault at `~/Vaults/neuro-quant-vault/03-ontology-main/infranodus-state/`, so the user's Obsidian app sees it as native vault content.

For a quick UI inspection: `open http://localhost:3030` (the InfraNodus web UI on the local engine).

### 5. (Optional) Promote sorted notes

After review, the user typically moves notes from `00-raw → 01-sorted → 02-KB-main`. This step is left manual unless the user asks for automation.

## Operating discipline

- **Don't dedupe across runs without checking.** If a URL was scraped last week, a fresh ingest creates a duplicate note. Check with `turbovault search query="<url>"` first.
- **Cap parallelism.** Parallel scraping is fast and can exhaust rate limits; default to 5 concurrent fetches.
- **Log every step.** Write to `~/.claude/relentless-inception/runs/scrape-<UTC>/log.jsonl` (matches the harness convention) so a failed run can be partially resumed.
- **Tear down gracefully.** A partial scrape that fails on ingest still leaves valid scrape-results.json — preserve it.

## Failure modes

- **Scrape API rate-limited:** reduce parallelism, retry.
- **TurboVault refuses a write (locked file, conflicting frontmatter):** surface the error verbatim, don't auto-overwrite.
- **InfraNodus engine returns a degraded response on AI-dependent tools** (e.g., `generate_research_ideas` returns 501 from the OSS engine): fall back to the simpler `generate_topical_clusters` and note the degradation in your report.

## Companions

- `/forge`, `/turbovault`, `/infranodus` — the underlying calls
- `parallel-web`, `perplexity-search`, `research-lookup` — pick one as the scraper
- `relentless-inception` — if the user wants this as a long-running unattended pipeline with rescue + tearsheets, wrap it in /relentless-inception with `--exec=proof-loops`

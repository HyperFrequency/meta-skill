---
name: deep-tool-wiki
description: Look up a HyperFrequency-forked tool by querying its combined private DeepWiki (HyperFrequency/deep-tool-wiki via Devin), its persistent InfraNodus knowledge graph + dual reasoning ontology, Context7 code snippets, and Auggie semantic understanding — all in parallel — and synthesize a layered answer. Use when the user asks "how does X work", "give me the API for X", "what's the conceptual model behind X", "compare X to Y", or names any indexed tool. The combined deepwiki holds the canonical 1500+ line page per tool. The Obsidian Auto-Quant vault holds the curated cross-link layer.
---

# /deep-tool-wiki

Five-source layered lookup for any HyperFrequency-forked tool. Each source plays a different role:

| Source | What it gives | When to use |
|---|---|---|
| **HyperFrequency/deep-tool-wiki** (combined private wiki, via Devin MCP) | Canonical 1500-2200 line per-tool reference: overview, why-use, mental model, deep concept defs, 12-18 walkthroughs, full API surface, patterns, pitfalls, integrations | Primary for "how does X work" / "what's the API" / "explain the mental model" |
| **InfraNodus persistent graph** (`deep-tool-wiki-<tool>`, queried via mcp2cli) | Network structure: clusters, conceptual gateways, gaps, modularity. The "shape" of the conceptual space. | When you need *why* concepts cluster a certain way, or want to find blind spots / cross-tool overlap |
| **Reasoning ontology** (in each wiki page, dual format: high-level summary + ultra-detailed) | `[[X]] does Y so [[Z]]` triples in 10 relation codes. Causal/dependency/composition logic. | When you need the *causal model*, not just the API |
| **Context7** (`mcp__context7__*`) | Up-to-date code snippets and API signatures from upstream OSS docs | When you need a CURRENT working code example or signature check |
| **Auggie** (`mcp__auggie__augment_code_search`) | Cross-framework semantic search and patterns | When the question spans multiple repos or you need cross-cutting context |

## What's in each source

The reasoning ontology and InfraNodus knowledge graph for every tool were built from the **union of four upstream sources**:
1. **Full upstream documentation** (Cognition DeepWiki content for the original repo, ~250KB-1.3MB per tool)
2. **The official documentation website** (scraped from readthedocs / docs.<tool>.io / etc.)
3. **A YouTube tutorial transcript** for the tool (one canonical video per tool)
4. **The raw GitHub repo** (README + docs/ + examples/)

The Sonnet ingest pass synthesizes a 1500-2200 line wiki body, then an Opus pass with a fresh context window generates BOTH a high-level summary ontology (30-60 triples covering only major concepts) AND an ultra-detailed ontology (200-400 triples covering everything in the wiki body), and persists the graph to InfraNodus under the name `deep-tool-wiki-<tool>` so any LLM/agent in any future session can retrieve the full graph by name.

## Indexed tools

All 14 tools have:
- A canonical wiki page in `HyperFrequency/deep-tool-wiki/<tool>/wiki.md`
- A persistent InfraNodus graph at `deep-tool-wiki-<tool>`
- A dual reasoning ontology (summary + ultra-detailed) inside the wiki page
- A curated cross-link page in the Obsidian Auto-Quant vault under `DeepTools/`

```
optuna             nautilus-trader      vectorbtpro       nautilus-admin
mlflow             h2o-3                tardis-python     qlib
featuretools       tsfel                hftbacktest       hyper-stats
xfeat              alpha-factory
```

Plus any newly forked HyperFrequency repo, auto-ingested by the `hf-fork-auto-ingest.sh` PostToolUse hook.

## Required: sitemap tree + llm-wiki nav as page 1

Every tool's `wiki.md` MUST open (after YAML frontmatter, **before** any
prose section like Overview / Deep Concepts) with:

1. **An ASCII sitemap tree** — drilled 2–3 levels deep, covering every
   feature, subsystem, or module of the tool. The tree *is* the primary
   navigation — a reader should be able to orient themselves before
   reading a single prose paragraph.
2. **A navigation note** pointing to the offline **llm-wiki** for that
   tool: `[[llm-wiki/<tool>/index]]` (resolves on disk to
   `$HOME/Dev/neuro-link/02-KB-main/<tool>/index.md`). The note
   must state explicitly that full offline context + API sigs +
   linked-pitfalls pages live under that tree.

Example (vectorbtpro):

````markdown
# vectorbtpro — sitemap

```
vectorbtpro/
├── Portfolio/
│   ├── from_signals            (signal-driven; fill defaults to signal-bar close)
│   ├── from_orders             (order-driven; explicit price/size)
│   └── from_order_func         (callable-per-bar, path-dependent)
├── Indicators/
│   ├── IndicatorFactory        (DSL: from_expr, from_apply_func, @p_/@in_/@out_)
│   ├── vbt.RSI                 (Wilder-smoothed, matches Pine ta.rsi)
│   ├── vbt.BBANDS              (ddof=0 via kwarg override)
│   └── vbt.ATR                 (Wilder-smoothed)
├── Data/
│   ├── BinanceData / CCXTData / YFData / PolygonData
│   └── Custom Data subclass
├── Optimization/
│   ├── PortfolioOptimizer
│   ├── Splitter (+ CVSplitter)
│   └── Walk-forward / Hyperopt integration
├── Analysis/
│   ├── Portfolio.stats()
│   ├── Portfolio.plot()
│   └── Tearsheet helpers
└── IO/
    ├── Parquet / HDF5 / Pickle
    └── Database (DuckDB / Postgres)
```

→ **Full offline context:** [[llm-wiki/vectorbtpro/index]]
  (navigate by tree; each leaf has API sigs + examples + linked pitfalls)
````

After the tree, continue with the existing `## Overview` + `## Deep
Concepts` + walkthroughs as before. The prose sections are deep-reads;
the tree is the fast-orient.

**When generating a new tool's wiki:** build the tree first — derive it
from the upstream repo's top-level packages/modules, not from prose.
The tree is the index; the prose explains what each leaf does.

**When refreshing a stale tool's wiki:** diff the upstream layout against
the existing tree and flag additions/removals explicitly.

## llm-wiki (offline, tree-navigable)

`02-KB-main/` is the offline vault. Each tool has a subdirectory with:

- `index.md` — tree nav for that tool (mirrors the sitemap in the
  combined wiki)
- `overview.md` — what the tool is, 1-2 paragraphs
- `<subsystem>/<leaf>.md` — one page per sitemap leaf, each with: API
  signature(s), minimal runnable example, linked pitfalls, cross-links
  to related leaves

The vault-wide `index.md` is itself a tree of all indexed tools; treat
it as the top-of-wiki navigation plane.

## Path layout — local machine vs testing / docker container

The skill operates in two environments with DIFFERENT canonical paths.
Use the right one for the context you're in:

| Context | Deep-tool-wiki (long-form) | llm-wiki (tree-navigable) |
|---|---|---|
| **Local machine** (mac, user-facing) | `$HOME/hyperfrequency/docs/deep-tool-wiki/<tool>/wiki.md` | `$HOME/hyperfrequency/neuro-link/02-KB-main/<tool>/` |
| **Testing / docker shakedown container** | `/opt/docs/deep-tool-wiki/<tool>/wiki.md` (bind-mounted from `hyperfrequency/docs/deep-tool-wiki/` at docker run) | `/opt/kb-main/<tool>/` (bind-mounted from `hyperfrequency/neuro-link/dev/02-KB-main/` — a separate copy from canonical, NOT a symlink, so test runs don't mutate the user's real vault) |

**Rule:** when writing scripts or agent prompts that run inside the
docker container, use `/opt/docs/deep-tool-wiki/` and `/opt/kb-main/`
paths. When writing content that ships to the user's mac (SKILL.md
references, vault pages, install docs), use the
`$HOME/hyperfrequency/...` absolute paths.

The testing KB lives as a distinct directory (not a symlink) so that
iterative test runs can mutate their local vault copy without
corrupting canonical content. Refresh the testing KB by `cp -R` from
canonical at the start of any new test cycle.

## Per-tool RefGraph assets

Each tool's `wiki.md` is accompanied by `assets/` containing:

- `refgraph-<primary>.mmd` (Mermaid source) + `.svg` (pre-rendered)
  — top-N most connected nodes, 2-3 levels deep, pruned for legibility
- `refgraph-<focus>.mmd` + `.svg` — a focused sub-graph (enum types,
  PyO3 boundary, include graph, strategy namespace, etc.)
- (planned) `refgraph.html` — Sigma.js interactive graph viewer.
  Clicking a node queries qdrant via qmd and returns the corresponding
  wiki page inline, rather than opening an external web URL. Models the
  UX of vectorbt.pro's `assets/RefGraph.dark.html` but routes through
  local RAG instead of the live pvt site.

For the reasoning-ontology triples that anchor the InfraNodus graph
(`[[entity1]] verb-phrase [[entity2]] [relationCode]`), see the
"Reasoning ontology format" section later in this skill. These
ontologies are PRESERVED across re-ingests — never delete existing
ontology content when refreshing a tool's wiki.

## When to use

- User mentions any indexed tool by name
- User asks "how does X work" / "what's X" / "give me an example with X"
- User wants to compare two indexed tools (use the union ontology query)
- User wants the conceptual ontology or knowledge graph for a tool
- Before recommending an API from an indexed tool, run this for cross-validation

## When NOT to use

- For general code search in the *current* repo → Grep/Read
- For arxiv papers or scientific literature → paper-lookup, perplexity-search
- For tools that aren't indexed and aren't on Context7 → fall back to WebSearch + clone
- For pure conversational follow-ups about a single concept already in context → just answer

## Procedure

### Step 1 — Identify the tool(s)

Reduce the user's question to `<tool>(s) + <topic>`. Example: `optuna + how to set up distributed RDB storage`.

### Step 2 — Decide which sources to fan out to

| Question type | Sources |
|---|---|
| Pure API / code example | DeepWiki + Context7 (parallel) |
| Conceptual / mental model | DeepWiki + InfraNodus graph (parallel) |
| Cross-tool comparison | DeepWiki for both tools + InfraNodus union query (parallel) |
| Current working code with version specifics | Context7 + DeepWiki (parallel) |
| Cross-framework patterns | Auggie + DeepWiki (parallel) |

### Step 3 — Fan out the queries IN PARALLEL (single message, multiple tool calls)

**DeepWiki content (combined private wiki)** — via Devin MCP through mcp2cli:
```bash
mcp2cli --mcp https://mcp.devin.ai/mcp \
  --auth-header "Authorization:Bearer cog_wbyhjgtghy4itsyaxfsxivm4gx6caey4ne4wcbprm4kkocqfx67q" \
  read-wiki-contents --repo-name HyperFrequency/deep-tool-wiki
```
Or for a focused question:
```bash
mcp2cli --mcp https://mcp.devin.ai/mcp \
  --auth-header "Authorization:Bearer cog_..." \
  ask-question --repo-name HyperFrequency/deep-tool-wiki \
  --question "How do I set up distributed RDB storage in optuna?"
```

**InfraNodus persistent graph** — query a saved graph by name:
```bash
INFRANODUS_API_KEY="18397:..." mcp2cli --mcp-stdio "npx -y infranodus-mcp-server" \
  analyze-existing-graph-by-name --graph-name "deep-tool-wiki-optuna" \
  --context "Retrieving the persistent reasoning ontology for optuna to answer a user question about study orchestration"
```

**Context7 code snippets**:
```bash
mcp2cli --mcp-stdio "npx -y @upstash/context7-mcp" resolve-library-id --library-name optuna
mcp2cli --mcp-stdio "npx -y @upstash/context7-mcp" query-docs --library-id /optuna/optuna --query "study optimize distributed RDBStorage"
```

**Auggie cross-framework search**:
```bash
mcp2cli --mcp https://api.augmentcode.com/mcp \
  --auth-header "Authorization:Bearer ..." \
  augment-code-search --repo-owner optuna --repo-name optuna --query "RDBStorage postgres connection pooling"
```

### Step 4 — Synthesize the answer

Layer the results:

1. **What it is** — 1 line, from the wiki Overview
2. **Conceptual model** — paraphrased from the reasoning ontology in 3-6 bullets, citing the most causal triples
3. **Current API / code example** — from Context7, with version note if available
4. **Where it fits** — from Auggie or cross-tool wikilinks if the question spans repos
5. **Source coverage** — `wiki ✓ | InfraNodus ✓ | Context7 ✓ | Auggie ✓` (or ✗ with reason)

### Step 5 — When the user asks for the raw graph or ontology

Don't paraphrase. Paste the relevant section from the wiki page verbatim — including the `[[wikilinks]]` so they stay linkable in Obsidian. Or query InfraNodus directly via `analyze-existing-graph-by-name` and surface clusters/gateways.

## Reasoning ontology format (reference)

Each wiki page contains TWO ontologies appended at the bottom, both using the InfraNodus convention:

```
[[entity1]] verb-phrase [[entity2]] [relationCode]
```

Relation codes used:
- `[isA]` — class membership
- `[partOf]` — composition
- `[hasAttribute]` — properties
- `[relatedTo]` — general association
- `[dependentOn]` — dependencies
- `[causes]` — causal
- `[locatedIn]` — spatial / belongs to
- `[occursAt]` — temporal / phase
- `[derivedFrom]` — origin / inherits from
- `[opposes]` — contrast / mutually exclusive

**High-level summary ontology** (30-60 triples) gives the major concepts only — quick tour of how the tool thinks. **Ultra-detailed ontology** (200-400 triples) covers every concept in the deep wiki body and is suitable for graph queries via InfraNodus.

The ontology is **network-structured, not hub-and-spoke**: each entity appears in 2-6 triples connecting to *different* neighbors so the graph reflects the conceptual network, not a star around the tool name. Cross-tool wikilinks (`[[DeepTools/<other-tool>]]`) make the union ontology across tools navigable.

## Output format

```
**Tool:** <name> (HyperFrequency fork of <upstream>)

**What it is:** <one-line from Overview>

**Conceptual model:**
- <paraphrased ontology triple in prose>
- <paraphrased ontology triple in prose>
- <paraphrased ontology triple in prose>

**Current API:**
\`\`\`<lang>
<code from Context7 or DeepWiki, complete and runnable>
\`\`\`

**Where it fits:** <Auggie cross-pattern note or cross-tool wikilink, optional>

**Sources:** DeepWiki ✓ | InfraNodus ✓ | Context7 ✓ | Auggie ✓
**Canonical page:** HyperFrequency/deep-tool-wiki → <tool>/wiki.md
**InfraNodus graph:** `deep-tool-wiki-<tool>`
**Obsidian curated:** [[DeepTools/<tool>]]
```

## Constraint: Context7 cannot be programmatically populated

Context7's library list is curated by Upstash. There is **no public API to add a repo**. The HyperFrequency forks therefore live in DeepWiki + InfraNodus + the Obsidian curated layer, but NOT in Context7. When you need code snippets for a HyperFrequency fork, query Context7 with the **upstream** library name (e.g. `optuna` not `HyperFrequency/optuna`) and rely on the deep wiki body for any fork-specific behavior.

## Refreshing a tool's wiki

If a tool's upstream had a major release and the wiki is stale:

```bash
# Re-clone, re-fetch deepwiki, re-scrape website, re-fetch youtube, re-spawn the
# Sonnet+Opus pipeline. Use the same script + agent prompts that built the
# original wiki — they live in ~/.claude/scripts/deep-tool-wiki.py and the
# Agent prompt template embedded in the auto-ingest hook.
~/.claude/scripts/deep-tool-wiki.py clone <upstream-org/repo> --tool <tool-name> --out /tmp/dtw-<tool>-raw.md
# ...then re-spawn Sonnet ingest + Opus ontology agents, then commit and push to HyperFrequency/deep-tool-wiki
```

Or trigger manually with the `/deep-tool-wiki` slash by prefacing with "refresh".

## Auto-trigger on new fork

The `~/.claude/hooks/hf-fork-auto-ingest.sh` hook fires on `gh repo fork` against any HyperFrequency-targeted repo. It auto-clones, runs InfraNodus on the raw material, and queues a stub wiki page. The user (or Claude) then runs `/deep-tool-wiki refresh <tool>` to fill in the deep body + dual ontology.

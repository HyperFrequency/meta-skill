---
name: llm-wiki
description: >
  Scaffold and maintain compounding LLM-curated knowledge bases on the neuro-quant stack.
  Triggers: "set up an LLM wiki", "build a research wiki", "deep-tool-wiki / deep-agent-wiki",
  "compounding second-brain over Obsidian", "wiki + ontologies", "wikilinked tool docs",
  "build a knowledge base from these sources", "maintain my wiki". Two canonical wikis
  coexist (`deep-tool-wiki` = per-tool docs, `deep-agent-wiki` = cross-cutting knowledge
  organized by ontology dimension) plus a flat top-level `ontologies/` aggregation layer.
  Every MCP call routes through the unified `neuro-harness` gateway.
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, Bash, Skill, Agent, TaskCreate, TaskUpdate
license: HyperFrequency original (derived from infranodus/skills `skill-llm-wiki`, MIT — see NOTICE.md)
---

# LLM Wiki — neuro-quant edition (v2 design)

This skill scaffolds and maintains **LLM-curated, compounding knowledge bases** on top of the user's Obsidian vault at `~/Vaults/neuro-quant-vault`. Instead of re-deriving knowledge from raw documents on every query (RAG-style), the LLM incrementally builds a persistent wiki — extracting, cross-referencing, and synthesizing once, then keeping it current as new sources arrive.

This edition differs from the upstream `infranodus/skills/skill-llm-wiki` in four load-bearing ways:

1. **Two canonical wiki shapes** — `deep-tool-wiki/` (per-tool, deeply nested) and `deep-agent-wiki/` (cross-cutting, organized by the 6 ontology dimensions). Different shapes, complementary roles.
2. **Flat top-level `ontologies/`** — six dimension ontologies plus a full-wiki union, aggregated from BOTH wikis. No per-wiki nesting; the ontology layer is the global view.
3. **Per-folder `AGENTS.md` discipline** — every subdirectory carries its own instruction-as-code file so agents that open the directory learn local conventions before writing.
4. **Gateway contract** — every MCP call routes through `neuro-harness` (mcp2cli / ContextForge). InfraNodus runs locally per `project_infranodus_local_only.md`; vault writes go through TurboVault; source ingestion goes through `web-scrape-ingest`.

---

## Required tooling — the unified gateway contract

When working with any wiki operation, **always** route MCP calls through the unified mcp2cli gateway (see the `neuro-harness` skill for the full endpoint table).

| Task | Use | Why |
| --- | --- | --- |
| Knowledge-graph + gap analysis | `infranodus` skill | Local OSS engine per `project_infranodus_local_only.md` — never default to `infranodus.com`. |
| Vault read / write / search / backlinks | `turbovault` skill | TurboVault is the only sanctioned write path into the vault. |
| Web scrape + ingest of articles, papers, blog posts | `web-scrape-ingest` skill | Composes `parallel-web` + `markitdown` + `turbovault` into one URL → `__raw/` pipeline. |
| PDF / HTML / DOCX → markdown | `markitdown` CLI | `__raw/papers/`, `__raw/patents/`, `__raw/books/` must be markdown before any wiki page references them. |
| Fast in-vault search | `ripgrep` (`rg`) | TurboVault is the API; rg is the unix tool. |
| Ontology generation | `ontology-creator` skill | Owns the relation-code vocabulary + the network-not-tree discipline. Modes: macro, agent, workflow-state, **plus dimension modes** added here (`systems`, `concepts`, `connections`, `differences`, `constraints`, `sources`). |
| Cross-tool / cross-wiki link discovery | `cornelius-find-connections` skill | Augments `infranodus merged_graph_from_texts` with prose-driven connection discovery. |
| KB coherence + tension detection | `cornelius-coherence-sweep`, `cornelius-detect-tensions` | Used in maintenance workflow W10. |
| Change propagation across linked pages | `cornelius-propagate-change` | Used in maintenance workflow W6. |

**Do not** hand-roll direct SSE calls when a gateway route exists — contract violation per `neuro-harness`. Direct SSE is allowed only for debug / liveness checks.

---

## Architecture — four layers, not three

```
┌──────────────────────────────────────────────────────────────────────┐
│  __raw/                  RAW LAYER — immutable source documents       │
│    organized by source TYPE; never auto-edited;                       │
│    paywalled stubs go to __raw/__paywalled/                           │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼   ingestion + summarization
┌──────────────────────────────────────────────────────────────────────┐
│  wikis/                  WIKI LAYER — LLM-owned content               │
│    deep-tool-wiki/<tool>/         one folder per tool                 │
│      <page>.md, <page>.md, ...                                        │
│      ontology/                    per-tool ontology dir (6 files +    │
│        <dim>-ontology.md × 6      one full-ontology aggregate)         │
│        full-ontology.md                                                │
│    deep-agent-wiki/<dimension>/   one folder per ontology dimension   │
│      <page>.md, <page>.md, ...                                        │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼   ontology generation + aggregation
┌──────────────────────────────────────────────────────────────────────┐
│  ontologies/             ONTOLOGY LAYER — global aggregation, flat    │
│    systems-ontology.md            union of systems across wikis       │
│    concepts-ontology.md           union of concepts                   │
│    connections-ontology.md        relationships between everything    │
│    differences-ontology.md        X vs Y decisions                    │
│    constraints-ontology.md        limits, anti-patterns               │
│    sources-ontology.md            provenance                          │
│    full-wiki-ontology.md          union of the 6                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼   gap analysis + queries
┌──────────────────────────────────────────────────────────────────────┐
│  output/                 ANALYSES + REPORTS                           │
│  todos/                  RESEARCH PRIORITIES (driven by gap analysis) │
└──────────────────────────────────────────────────────────────────────┘
```

The RAW layer is upstream of the WIKI layer (one-way: raw flows up; wiki never edits raw). The ONTOLOGY layer is downstream of WIKI (regenerated from wiki content). OUTPUT + TODOS are downstream of ONTOLOGY (gap analysis drives the todo list).

---

## The two canonical wikis

### `deep-tool-wiki/<tool>/` — per-tool docs

One subfolder per upstream tool. Each tool gets a **complete reference-quality wiki** of its own — the upstream docs converted to OFM, structured for wikilink navigation, with a local ontology.

```
wikis/deep-tool-wiki/
  AGENTS.md                       # how to add / maintain a tool here
  <tool>/                         # e.g. vectorbt, nautilus-trader, ray, infranodus
    AGENTS.md                     # tool-specific maintenance notes
    index.md                      # tool entry point (purpose, status, version, links)
    overview.md                   # 1-page synthesis — start here when reading
    api.md                        # public API reference
    concepts/                     # one .md per concept the tool surfaces
      <concept>.md
    examples/                     # working code examples
      <example>.md
    pitfalls.md                   # known issues, footguns, anti-patterns
    changelog.md                  # upstream version log + relevance notes
    sources.md                    # where the docs came from (URLs, dates, scrape jobs)
    ontology/                     # LOCAL 6-dimension ontology for THIS tool
      AGENTS.md                   # ontology-folder write rules
      systems-ontology.md         # tool's systems-dimension entities
      concepts-ontology.md        # tool's concepts-dimension entities
      connections-ontology.md     # tool's relationships (internal + to other tools)
      differences-ontology.md     # tool's contrasts (vs siblings, vs versions)
      constraints-ontology.md     # tool's limits / footguns / deprecations
      sources-ontology.md         # tool's provenance (papers, repos, docs)
      full-ontology.md            # combined view of the 6 above (regenerated)
  <tool-2>/
    ...
```

Use this for: `vectorbt`, `vectorbtpro`, `nautilus_trader`, `hftbacktest`, `ray`, `qlib`, `xfeat`, `featuretools`, `mlfinlab`, `infranodus`, `hmmlearn`, `TabPFN`, `chronos-forecasting`, `QuantLib`, `arch`, `Copulas`, `PyWavelets`, `filterpy`, `transformers`, `pytorch-lightning`, `pytorch-forecasting`, `stable-baselines3`, `pufferlib`, `tree-sitter`, `gitnexus`, `turbovault`, `Anthropic SDK`, `DSPy`, `MLflow`, `LangGraph`, `LlamaIndex`, etc. — anywhere "I need to look up how tool X works" is the question.

The local `<tool>/ontology/` directory holds **six dimension-specific ontology files plus one combined `full-ontology.md`**. Each `<dim>-ontology.md` is generated by `ontology-creator` in the corresponding dimension mode over the tool's curated content (NOT `__raw/`). The `full-ontology.md` is the union of the 6, regenerated whenever any of them changes (workflow W7c). Dimension-specific ontology files are the canonical inputs for global aggregation (W7) — they get concatenated with `deep-agent-wiki/<dim>/` into `ontologies/<dim>-ontology.md`.

The `deep-tool-wiki` SKILL (separate skill at `neuro-base/deep-tool-wiki/`) handles the **populate-a-single-tool** flow. This `llm-wiki` skill handles the **wiki + ontology infrastructure** the populate flow writes into.

### `deep-agent-wiki/<dimension>/` — cross-cutting knowledge by dimension

Six subfolders, one per ontology dimension. Each holds pages that **don't belong to any single tool** — cross-cutting concepts, system-level abstractions, decision frameworks, anti-patterns, provenance records.

```
wikis/deep-agent-wiki/
  AGENTS.md                       # how the dimension structure works
  systems/                        # concrete deployable systems
    AGENTS.md                     # systems-dimension write rules
    <page>.md                     # e.g. modal-sandboxes.md, lambda-labs-cluster.md
  concepts/                       # abstract ideas
    AGENTS.md
    <page>.md                     # e.g. walk-forward-validation.md, deflated-sharpe.md
  connections/                    # relationships between systems + concepts
    AGENTS.md
    <page>.md                     # e.g. nautilus-uses-hyperliquid-patch.md
  differences/                    # contrasts / when-to-use-which
    AGENTS.md
    <page>.md                     # e.g. vectorbt-vs-nautilus.md
  constraints/                    # limits, anti-patterns, gotchas
    AGENTS.md
    <page>.md                     # e.g. cant-vectorize-stateful-orders.md
  sources/                        # provenance / source list
    AGENTS.md
    <page>.md                     # e.g. mlfinlab-was-open-pre-v0.9.md
```

Use this for: cross-tool design decisions, architectural conventions, the "neuro-harness gateway contract", the "single-writer vault discipline", strategy methodology, anything where the unit of knowledge is **a concept that spans tools** rather than a tool.

Pages here cross-link aggressively to `deep-tool-wiki/<tool>/` pages.

---

## The 6 ontology dimensions

Same vocabulary used by the `ontology-creator` skill. Each dimension has a canonical question it answers and a preferred set of relation codes (see `ontology-creator/SKILL.md`):

| Dimension | Question | Typical relation codes |
| --- | --- | --- |
| **systems** | What concrete things exist? | `[isA]`, `[partOf]`, `[locatedIn]` |
| **concepts** | What abstract ideas matter? | `[isA]`, `[derivedFrom]`, `[hasAttribute]` |
| **connections** | What depends on / cites / implements what? | `[dependentOn]`, `[derivedFrom]`, `[partOf]`, `[causes]` |
| **differences** | When use X vs Y? | `[opposes]`, `[hasAttribute]`, `[locatedIn]` |
| **constraints** | What can't / shouldn't be done? | `[opposes]`, `[dependentOn]`, `[hasAttribute]` |
| **sources** | Where did this knowledge come from? | `[derivedFrom]`, `[locatedIn]`, `[hasAttribute]` |

Each dimension lives in two places:

- **Local-to-tool**: one file per dimension in `wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md`, plus a `full-ontology.md` union
- **Global**: full pages in `wikis/deep-agent-wiki/<dimension>/` AND aggregated entries in `ontologies/<dimension>-ontology.md`

The global ontology files are **regenerated** from these inputs by workflow W7 (ontology aggregation) — never hand-edited.

---

## Setup (prerequisites — one-time per machine)

1. **Obsidian vault** at `~/Vaults/neuro-quant-vault` (canonical).
2. **InfraNodus MCP (local OSS)** at `http://infranodus-mcp:9005/sse`. Per `project_infranodus_local_only.md`, never default to `infranodus.com`.
3. **TurboVault MCP** at `http://turbovault:9004/sse` (bind-mounts the vault read-write).
4. **ContextForge gateway** at `localhost:4444` (federates the MCPs).
5. **CouchDB** at `localhost:5984` for Obsidian Self-hosted LiveSync (see `neuro-harness/docs/obsidian-livesync.md`).
6. **CLI tools**:
   - `markitdown` — PDF/DOCX/HTML → markdown (`uv tool install markitdown`)
   - `ripgrep` — fast vault search (`brew install ripgrep`)
   - `jq` — JSON munging
   - `pandoc` — fallback converter for edge formats

Verify the stack:

```bash
for svc in infranodus-mcp:9005 turbovault:9004 gitnexus:9001 tree-sitter:9003; do
  printf "%-30s " "$svc"
  curl -sS --max-time 2 "http://$svc/sse" | head -1
done
mcp2cli --help | head -5
```

If a service is down, surface that to the user before running any workflow.

---

## Build workflows (W1 – W3)

### W1 — `new-tool-wiki`: add a new tool to `deep-tool-wiki/`

Goal: populate one new `deep-tool-wiki/<tool>/` from upstream docs.

```
1. CONFIRM tool name (kebab-case, matches PyPI / GitHub repo name where possible)
2. SCRAPE upstream docs via web-scrape-ingest skill
     → __raw/articles/<tool>-upstream/ as a working set
3. CONVERT non-markdown sources via markitdown
4. CURATE into wikis/deep-tool-wiki/<tool>/:
   - index.md       — purpose, current version, install, upstream URL, status
   - overview.md    — 1-page narrative synthesis (use cornelius-synthesize-insights)
   - api.md         — public surface (only what users touch — avoid the autoreference dump trap)
   - concepts/      — one .md per non-trivial concept the tool surfaces
   - examples/      — minimal runnable code examples
   - pitfalls.md    — known issues, footguns, anti-patterns (see neuro-quant memory)
   - sources.md     — verbatim list of URLs + scrape dates + commit SHAs
5. GENERATE the per-tool ontology directory:
     - For each dimension in {systems, concepts, connections, differences, constraints, sources}:
         ontology-creator <dim>-mode over the curated content (NOT __raw/)
         → wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md
     - Concat the 6 → ontology/full-ontology.md (for tool-local queries)
6. WRITE AGENTS.md per subdirectory (api/, concepts/, examples/) using the
   per-folder template below
7. RUN W7 (ontology-aggregate) on each of the 6 dimensions
     so the new tool's entries surface in ontologies/
8. RUN W8 (full-wiki-rebuild) so full-wiki-ontology.md picks up the new tool
9. LOG to log.md: timestamp, tool name, page count, ontology size, gap count
```

The `deep-tool-wiki` SKILL automates steps 2-5 for a single tool. This `llm-wiki` skill owns the scaffold (step 1) + the propagation (steps 7-9).

### W2 — `new-agent-knowledge`: add a cross-cutting page to `deep-agent-wiki/`

Goal: when knowledge belongs to NO single tool, place it in the right dimension subfolder.

```
1. CLASSIFY the knowledge to exactly one dimension:
     systems   — it's a concrete deployable thing
     concepts  — it's an abstract idea
     connections — it's a relationship between two named things
     differences — it's a contrast / when-to-use-which
     constraints — it's a limit, anti-pattern, gotcha
     sources   — it's about provenance
   If two dimensions feel right, pick the one closest to the page's title.
   The other dimensions get [[wikilinks]] back to this page in their pages.
2. WRITE wikis/deep-agent-wiki/<dimension>/<slug>.md
   - Title H1 matches the file slug
   - Frontmatter:
       dimension: <dimension>
       cross-links: [tool-a, tool-b, …]   # tools this page connects to
       sources: [<source-page>, …]        # for provenance
       verified: <date>
   - Body: 1-paragraph definition → relations to other entities (wikilinked) →
           code/diagram if useful → references
3. CROSS-LINK from tool wikis: each [[<tool>]] page that mentions this concept
   should [[wikilink]] back to the new page
4. RUN W7 (ontology-aggregate) for the dimension you wrote into
5. LOG to log.md
```

### W3 — `bootstrap`: instantiate the entire structure from zero

One script. Idempotent — running twice does no damage; missing dirs are created, existing ones are left alone.

```bash
VAULT=~/Vaults/neuro-quant-vault

# Top-level structure
mkdir -p "$VAULT"/__raw/{notes,papers,youtube,articles,search-results,patents,books,interviews,__paywalled,assets}
mkdir -p "$VAULT"/wikis/deep-tool-wiki
mkdir -p "$VAULT"/wikis/deep-agent-wiki/{systems,concepts,connections,differences,constraints,sources}
mkdir -p "$VAULT"/ontologies
mkdir -p "$VAULT"/{output,todos}

# Top-level schema files
touch "$VAULT"/{CLAUDE.md,AGENTS.md,log.md}

# Per-folder AGENTS.md
for d in \
  __raw __raw/notes __raw/papers __raw/youtube __raw/articles \
  __raw/search-results __raw/patents __raw/books __raw/interviews \
  __raw/__paywalled \
  wikis/deep-tool-wiki \
  wikis/deep-agent-wiki \
  wikis/deep-agent-wiki/systems wikis/deep-agent-wiki/concepts \
  wikis/deep-agent-wiki/connections wikis/deep-agent-wiki/differences \
  wikis/deep-agent-wiki/constraints wikis/deep-agent-wiki/sources \
  ontologies output todos; do
  touch "$VAULT/$d/AGENTS.md"
done

# Empty global ontology placeholders
for dim in systems concepts connections differences constraints sources full-wiki; do
  touch "$VAULT/ontologies/${dim}-ontology.md"
done

# Per-tool helper — call this when adding a tool (or call it ad-hoc to scaffold
# the tool's ontology/ subfolder before W1 populates content)
init_tool() {
  local tool="$1"
  local tool_root="$VAULT/wikis/deep-tool-wiki/$tool"
  mkdir -p "$tool_root"/{concepts,examples,ontology}
  touch "$tool_root"/{AGENTS.md,index.md,overview.md,api.md,pitfalls.md,changelog.md,sources.md}
  touch "$tool_root/concepts/AGENTS.md" "$tool_root/examples/AGENTS.md"
  for dim in systems concepts connections differences constraints sources; do
    touch "$tool_root/ontology/${dim}-ontology.md"
  done
  touch "$tool_root/ontology/full-ontology.md" "$tool_root/ontology/AGENTS.md"
}
# Usage: init_tool vectorbt

echo "Bootstrap complete. Now run W4 (schema-write) to populate AGENTS.md files."
echo "To add a tool: init_tool <tool-name>"
```

---

## Maintain workflows (W4 – W10)

### W4 — `schema-write`: populate every `AGENTS.md` + the top-level `CLAUDE.md`

Each `AGENTS.md` carries directory-local rules. Use this template per dimension; specialize the "What lives here" and "Anti-patterns" sections:

```markdown
# AGENTS.md — <directory>

## What lives here
<one paragraph>

## Naming
<file naming convention, e.g. kebab-case-slug.md>

## Frontmatter
<required + optional YAML keys with examples>

## Write rules
<when and how an agent writes here>

## Read rules
<context-budget rules — e.g. for __raw/papers/, read abstract first, then sections>

## Cross-links
- relevant skills: [...]
- relevant other directories: [...]

## Anti-patterns
- DON'T: <thing>
- DON'T: <thing>
```

The top-level `CLAUDE.md` / `AGENTS.md` carries the global view + load-bearing memory notes (`project_infranodus_local_only.md`, `feedback_auto_stub_pages.md`, `feedback_vault_root_clean.md`).

### W5 — `tool-update`: refresh an existing tool wiki when upstream changes

```
1. DETECT upstream change:
     - Read sources.md to get the canonical URL list + last scrape date
     - Re-fetch each URL through parallel-web with --since=<last-scrape-date>
     - Diff the markdown
2. For each changed page:
     - Re-scrape, re-convert via markitdown
     - Update wikis/deep-tool-wiki/<tool>/<page>.md
     - Append to changelog.md
3. RE-RUN ontology-creator per dimension to refresh wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md
     - Only regenerate dimensions whose source content actually changed
     - Then re-union into ontology/full-ontology.md (W7c)
4. PROPAGATE downstream:
     - For each dimension where the tool ontology changed, mark
       ontologies/<dim>-ontology.md stale → triggers W7
     - W8 will then rebuild full-wiki-ontology.md
5. LOG to log.md
```

### W6 — `cross-tool-link`: discover connections between tools

```
1. COLLECT all wikis/deep-tool-wiki/*/＜tool＞-ontology.md files
2. PASS to infranodus merged_graph_from_texts (via mcp2cli or
   /forge infranodus.merged_graph_from_texts)
3. For each cross-tool edge surfaced in the merged graph:
     a. Check if the connection already has a page in
        wikis/deep-agent-wiki/connections/
     b. If not, create a stub page with the cornelius-find-connections
        skill — frontmatter cross-links to BOTH tool pages
     c. If yes, append the new edge as evidence
4. RUN W7 for the "connections" dimension
5. LOG
```

`cornelius-find-connections` is the prose-driven half of this workflow; InfraNodus is the structural half. Use both.

### W7 — `ontology-aggregate`: rebuild a global dimension ontology

For each dimension `<dim>` in `{systems, concepts, connections, differences, constraints, sources}`:

```
1. COLLECT inputs:
     a. wikis/deep-agent-wiki/<dim>/*.md
     b. wikis/deep-tool-wiki/*/ontology/<dim>-ontology.md
        (one file per tool, pre-computed in W1 step 5 / W5 step 3)
2. PASS the union to ontology-creator with dimension mode <dim>
     (each dimension has its preferred relation-code set + annotation
      tag — see ontology-creator/SKILL.md → "Dimension Modes")
3. WRITE the merged output to ontologies/<dim>-ontology.md
     - Replace the entire file (regenerated, not appended)
     - Sort entities by slug for stable diffs
4. LOG to log.md: dimension, input file count, output relation count
```

Run W7 individually per dimension when only one dimension changed. Run it for all 6 (then W8) after a big ingest.

### W7b — per-tool ontology refresh

When a single tool's content changes but no cross-tool propagation is needed:

```
1. For each dimension whose source content changed:
     ontology-creator <dim>-mode over wikis/deep-tool-wiki/<tool>/
     → wikis/deep-tool-wiki/<tool>/ontology/<dim>-ontology.md
2. Run W7c (full-ontology rebuild for the tool)
3. Trigger W7 (global aggregate) for the changed dimensions
4. Then W8 if at least one global dimension changed
```

### W7c — per-tool `full-ontology.md` rebuild

The per-tool `full-ontology.md` is the union of the tool's six dimension ontologies. Cheap to regenerate; do it whenever any of the 6 dimension files changes:

```
cat wikis/deep-tool-wiki/<tool>/ontology/{systems,concepts,connections,differences,constraints,sources}-ontology.md \
  > wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md.new
# optional: pipe through ontology-creator topic-mode for de-dup + sort
mv wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md.new \
   wikis/deep-tool-wiki/<tool>/ontology/full-ontology.md
```

`full-ontology.md` is the **canonical tool-local query input**. Use it when the question is about one tool. Use `ontologies/full-wiki-ontology.md` when the question spans tools.

### W8 — `full-wiki-rebuild`: combine 6 dimensions into the union ontology

```
1. READ all 6 ontologies/<dim>-ontology.md files
2. CONCATENATE into one corpus
3. PASS to infranodus generate_knowledge_graph
     (this is the canonical input for W9 gap analysis)
4. WRITE the resulting unified graph + relation list to
   ontologies/full-wiki-ontology.md
5. LOG
```

`full-wiki-ontology.md` is the **canonical input** for any cross-wiki query — never query against per-dimension files directly when the question spans dimensions.

### W9 — `gap-analysis`: find what's missing

```
1. FEED ontologies/full-wiki-ontology.md to infranodus generate_content_gaps
2. INTERPRET the returned gap list:
     - Each gap = an unconnected or under-connected entity
     - Each gap is a hint: "scrape source X to fill this in"
3. WRITE todos/<date>-gaps.md with one todo per gap:
     - High-priority: gaps that bridge two existing clusters
     - Low-priority: peripheral gaps
4. CROSS-LINK each todo to the relevant wiki page (so the operator can navigate
   from todo → existing context → fill the gap)
5. LOG
```

Run W9 after every major aggregation cycle (W7 + W8).

### W10 — `lint`: vault hygiene

```
1. ORPHAN PAGES — pages with no incoming wikilinks
     - Tool wikis: every page should be linked from index.md or overview.md
     - Agent wiki: every page should be linked from at least one tool wiki
       OR from the dimension's own ontology
     - Use cornelius-coherence-sweep to detect
2. BROKEN WIKILINKS — [[target]] where target.md doesn't exist
     - Convert to stub if intentional (see __paywalled/ pattern)
     - Otherwise fix the slug or remove
3. STALE verified DATES — frontmatter verified: older than 90 days
     - Schedule a W5 (tool-update) for the relevant tool
4. CONTRADICTIONS — use cornelius-detect-tensions on each dimension folder
     to find pages whose claims contradict each other
5. WRITE output/<date>-lint-report.md
6. LOG
```

---

## How adjacent skills compose

```
                                  USER goal
                                       │
                                       ▼
                  ┌─────────────────────────────────────┐
                  │       llm-wiki (this skill)         │  ←─── workflow orchestrator
                  │       owns W1-W10                   │       picks W1..W10 by intent
                  └─────────────────────────────────────┘
                            │                  │
                ┌───────────┘                  └──────────────┐
                ▼                                             ▼
   ┌─────────────────────┐                       ┌─────────────────────┐
   │ web-scrape-ingest   │  raw ingestion        │ ontology-creator     │  ontology gen
   │  → parallel-web     │  W1, W5               │  → modes: macro,    │  W1, W7, W8
   │  → markitdown       │                       │    agent, workflow, │
   │  → turbovault writes│                       │    + dimension      │
   └─────────────────────┘                       └─────────────────────┘
            │                                                │
            │ writes to __raw/ + wikis/                      │ writes <tool>/ontology/<dim>.md (×6)
            │                                                │   and ontologies/<dim>.md
            ▼                                                ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │   turbovault   — vault read/write/search/backlinks               │
   │   (the only sanctioned write path into ~/Vaults/neuro-quant-vault) │
   └─────────────────────────────────────────────────────────────────┘
            │
            │ exposes the vault state to:
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │   infranodus + infranodus-cli  — graph operations                 │
   │     • merged_graph_from_texts        W6 (cross-tool linking)      │
   │     • generate_knowledge_graph       W8 (full-wiki union)         │
   │     • generate_content_gaps          W9 (gap analysis)            │
   │     • generate_topical_clusters      W7 (per-dim refinement)      │
   │     • develop_latent_topics          W6 (novel-entity detection)  │
   └──────────────────────────────────────────────────────────────────┘
            │
            │ structural; prose-driven half is:
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │   cornelius-*  — prose-level KB operations                        │
   │     • cornelius-find-connections     W6                           │
   │     • cornelius-coherence-sweep      W10                          │
   │     • cornelius-detect-tensions      W10                          │
   │     • cornelius-propagate-change     W5 (downstream after update) │
   │     • cornelius-synthesize-insights  W1 (overview.md generation)  │
   │     • cornelius-extract-document-insights  W1 (concept extraction) │
   └──────────────────────────────────────────────────────────────────┘
            │
            │ for harness-level orchestration of W1-W10 across many tools:
            ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │   autonomous-orchestrator — meta-agent loop                       │
   │     • PROGRAM.md directive specifies the wiki to maintain         │
   │     • Hill-climbs on wiki health metric (resolved-wikilink %,     │
   │       gap count, contradiction count)                             │
   │     • Iterates W5 + W7 + W9 overnight                             │
   └──────────────────────────────────────────────────────────────────┘
```

### Skill-by-skill: when to reach for which

| Situation | Reach for | Why |
| --- | --- | --- |
| First-time wiki setup | This skill (W3 bootstrap) | Owns the directory scaffold + AGENTS.md placeholders |
| Adding a new tool | `deep-tool-wiki` skill, then W7 + W8 here | `deep-tool-wiki` is the single-tool populate flow; W7/W8 propagate to ontologies |
| Adding a cross-cutting concept | This skill (W2) | Classifies to dimension + cross-links |
| Re-scraping upstream | This skill (W5) | Owns the diff + propagation chain |
| "Are these two tools related?" | This skill (W6) — uses both InfraNodus and Cornelius | Structural + prose halves |
| "What's missing from the wiki?" | This skill (W9) — uses InfraNodus content-gaps | Gap analysis is the gateway to todos/ |
| "Why are these two pages contradictory?" | `cornelius-detect-tensions` directly, then W10 | Lint folds the result into the report |
| Overnight automated maintenance | `autonomous-orchestrator` with PROGRAM.md set to "maintain the wiki" | Iterates W5/W7/W9 until convergence |
| Querying the wiki | `turbovault` directly or via `/forge turbovault.<tool>` | Vault is the source of truth |

---

## Per-folder `AGENTS.md` — co-located instruction-as-code

Each subdirectory carries its own `AGENTS.md`. When an agent (Claude Code, Codex, any LLM that reads `AGENTS.md` files) opens a directory, the local file tells it exactly how to treat the contents. The top-level `CLAUDE.md` / `AGENTS.md` binds globally; per-folder files specialize.

Every `AGENTS.md` covers five sections:

1. **What lives here** — one-paragraph description of the directory's role
2. **Naming + frontmatter** — file-naming convention + required YAML keys
3. **Write rules** — when and how an agent writes here
4. **Read rules** — context-budget guidance (e.g. for `__raw/papers/`, read abstract first then targeted sections)
5. **Anti-patterns** — directory-specific things NOT to do

Per-folder cross-links to the relevant skills are non-negotiable. Example for `__raw/papers/AGENTS.md`:

```markdown
## Cross-links
- web-scrape-ingest skill (the ingest path)
- markitdown skill (PDF → MD conversion)
- citation-management skill (BibTeX validation)
- paper-lookup skill (DOI/arXiv lookup)
```

Per-folder cross-links bind the directory to its operating workflows so an agent never has to guess.

---

## `__paywalled/` — stubs for unfetchable content

Web scraping does not always return content. Publisher paywalls, captchas, geo-blocks, and image-only scanned PDFs all leave an ingestion agent holding nothing but a citation. Those cases go to `__raw/__paywalled/` **as a stub note** rather than silently skipped — the wiki has a complete record of what the user asked for AND what was actually retrievable.

Stub format:

```yaml
---
title: "<full title>"
authors: [...]
year: <YYYY>
venue: "<journal or conference>"
doi: "<DOI>"
url: "<canonical-link>"
fulltext_status: paywalled          # paywalled | conversion_failed | not_available | captcha
fulltext_source: none
fetch_attempts:
  - { source: "arxiv", result: "no preprint" }
  - { source: "publisher", result: "403 Cloudflare" }
  - { source: "wayback", result: "no snapshot" }
  - { source: "ssrn", result: "abstract only" }
unblock_path: "Campus VPN; or interlibrary loan via <institution>"
verified: <date>
---

# <Title>

## Why it's here

<one-paragraph why-this-paper-matters>

## Abstract

<verbatim publisher abstract, OR "Abstract not retrievable">

## What to do if you need this

<concrete unblock path>
```

Cross-references from `wikis/` pages still resolve via `[[<slug>]]` wikilinks pointing at the paywalled stub. The graph stays connected.

**Promotion rule**: when a paywalled paper becomes retrievable, the ingestion agent moves the file from `__raw/__paywalled/` to `__raw/papers/`, runs the normal conversion pipeline, updates `fulltext_status: included`, and logs the promotion to `log.md`.

---

## CLAUDE.md / AGENTS.md template (top-level schema)

The top-level files bind globally. Template:

```markdown
# Vault schema — neuro-quant edition

This vault hosts two wikis plus a flat ontology layer. Every LLM that reads this
file must respect the conventions below.

## Layout
- __raw/                       immutable sources, never auto-edited
- wikis/deep-tool-wiki/<tool>/  per-tool docs + per-tool ontology
- wikis/deep-agent-wiki/<dim>/  cross-cutting knowledge by dimension
- ontologies/                  flat global ontology layer (6 dimensions + full union)
- output/                      analyses + reports
- todos/                       gap-driven research priorities

## Gateway contract
Every MCP call routes through neuro-harness (mcp2cli / ContextForge).
InfraNodus is LOCAL OSS — never default to infranodus.com.
Vault writes go through TurboVault (never edit .md files via subprocess + raw fs).

## Naming
kebab-case slugs for files. Page H1 matches the slug. Wikilinks are case-sensitive.

## Page-type taxonomy
- entity:        a thing (tool, system, concept)
- source-summary: a digested upstream source
- comparison:    X vs Y in a single page
- synthesis:     overview / index / log
- ontology:      a relation graph (only in /ontologies/, in <tool>/ontology/<dim>-ontology.md, or
                 in deep-agent-wiki/<dim>/ pages)

## Wikilink discipline
- [[<slug>]]:    canonical entity link
- [[<slug>|alias]]: rare; only when the alias improves readability
- broken [[<slug>]]: agent must either create the target or remove the link
                      within the same edit; no orphan stubs in 02-KB-main per
                      feedback_auto_stub_pages.md.

## Memory pins
- project_infranodus_local_only.md
- feedback_vault_root_clean.md
- feedback_auto_stub_pages.md
- feedback_doc_sync_hook_misfire.md

## Skill router
For any operation, prefer the per-skill router over hand-rolled tool calls:
- llm-wiki: workflows W1-W10 (this file's home)
- deep-tool-wiki: populate one tool's deep-tool-wiki/<tool>/
- web-scrape-ingest: URL → __raw/ pipeline
- ontology-creator: any ontology generation
- infranodus / infranodus-cli: graph operations
- turbovault: vault I/O
- cornelius-*: prose KB operations
```

---

## Multi-wiki coordination

The two wikis share one vault. Pages **should** cross-link across wiki boundaries — Obsidian resolves `[[name]]` to whichever subfolder contains the matching `.md` file, so a `deep-agent-wiki/concepts/walk-forward-validation.md` page can freely link `[[vectorbt]]` even though that page lives in `deep-tool-wiki/vectorbt/index.md`.

If two wikis ever name the same slug differently (rare but possible), use **wiki-scoped slugs**: `[[deep-agent-walk-forward-validation]]` vs `[[deep-tool-vectorbt-walk-forward]]`. Document the convention in the relevant `AGENTS.md`.

Collision check:

```bash
# Find slug collisions across wikis
find ~/Vaults/neuro-quant-vault/wikis -name '*.md' -exec basename {} .md \; \
  | sort | uniq -c | sort -rn | awk '$1>1'
```

---

## Common pitfalls

1. **Editing `__raw/` from a wiki workflow.** Raw is immutable. If a source needs fixing, write a correction in `wikis/deep-agent-wiki/sources/` referencing the raw entry — never modify the raw file. Promotion from `__paywalled/` to `papers/` is the one exception (the file moves; its content stays as-fetched).
2. **Hand-editing `ontologies/<dim>-ontology.md`.** Always regenerate via W7. Manual edits get overwritten on the next aggregation. Add the underlying concept page in `deep-agent-wiki/<dim>/` instead — that's the input.
3. **Mixing wiki shapes** — putting per-tool docs in `deep-agent-wiki/` or putting cross-cutting concepts in `deep-tool-wiki/<tool>/`. Use the right shape: if it's specific to one tool, it goes in `deep-tool-wiki/`; if it spans tools, it goes in `deep-agent-wiki/`.
4. **Auto-creating stub pages without content** in `deep-agent-wiki/` to satisfy a wikilink. Per `feedback_auto_stub_pages.md`, no empty placeholders. Either write the page now or remove the wikilink.
5. **Multiple Obsidian Sync writers.** Per `neuro-harness/docs/obsidian-livesync.md`, only desktop Obsidian participates in CouchDB sync. TurboVault + agent writers go through the filesystem; do not enable Obsidian Sync plugin on a second device pointing at the same vault.
6. **Forgetting to run W7/W8 after W5.** Tool updates that don't propagate to the global ontologies create drift — the per-tool ontology says one thing, the global says another. Always cascade.
7. **Naming a custom wiki `deep-research-wiki` etc.** without picking a shape. Pick shape A (`deep-tool-wiki`-like, per-entity nesting) or shape B (`deep-agent-wiki`-like, by-dimension subfolders). Don't invent shape C.

---

## Verification checklist (end-of-session)

After any workflow run, confirm:

- [ ] `log.md` has an entry for this session
- [ ] No new wikilinks in the touched pages are broken (`rg -o '\[\[[a-z0-9-]+\]\]' <page> | sort -u` then check each target exists)
- [ ] `verified:` date in frontmatter is today's date for any page touched
- [ ] The relevant ontology was regenerated (W7) if wiki content changed
- [ ] `full-wiki-ontology.md` was rebuilt (W8) if multiple dimensions changed
- [ ] Gap-driven todos in `todos/<date>-gaps.md` are linked back to the wiki pages that prompted them

---

## References

### Upstream
- [infranodus/skills/skill-llm-wiki](https://github.com/infranodus/skills/blob/master/skill-llm-wiki/SKILL.md) — MIT, the phase-structure baseline
- [infranodus/skills/skill-ontology-creator](https://github.com/infranodus/skills/blob/master/skill-ontology-creator/SKILL.md) — MIT, the relation-code vocabulary
- [infranodus/skills/infranodus-cli](https://github.com/infranodus/skills/blob/master/infranodus-cli/SKILL.md) — MIT, full InfraNodus tool surface

### Adjacent skills in this repo
- `deep-tool-wiki` — populate flow for a single tool
- `web-scrape-ingest` — URL → __raw/ pipeline
- `ontology-creator` — relation-code vocabulary, dimension modes
- `infranodus`, `infranodus-cli` — graph ops
- `turbovault` — vault I/O
- `cornelius-find-connections`, `cornelius-coherence-sweep`, `cornelius-detect-tensions`, `cornelius-propagate-change`, `cornelius-synthesize-insights`, `cornelius-extract-document-insights` — prose KB ops
- `autonomous-orchestrator` — overnight automated maintenance
- `neuro-harness` — the gateway contract

### Concept references
- Obsidian Self-hosted LiveSync (CouchDB) — `neuro-harness/docs/obsidian-livesync.md`
- Memory pins driving the design:
  - `project_infranodus_local_only.md`
  - `feedback_vault_root_clean.md`
  - `feedback_auto_stub_pages.md`
  - `feedback_doc_sync_hook_misfire.md`

### Last cross-checked
2026-05-24 — InfraNodus tool surface verified against upstream; gateway endpoints verified against `neuro-harness/docker-compose.yaml` HEAD.

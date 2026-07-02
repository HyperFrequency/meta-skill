# Architecture & layout

This skill scaffolds and maintains **LLM-curated, compounding knowledge bases** on top of the user's Obsidian vault at `~/Vaults/neuro-quant-vault`. Instead of re-deriving knowledge from raw documents on every query (RAG-style), the LLM incrementally builds a persistent wiki — extracting, cross-referencing, and synthesizing once, then keeping it current as new sources arrive.

This edition differs from the upstream `infranodus/skills/skill-llm-wiki` in four load-bearing ways:

1. **Two canonical wiki shapes** — `deep-tool-wiki/` (per-tool, deeply nested) and `deep-agent-wiki/` (cross-cutting, organized by the 6 ontology dimensions). Different shapes, complementary roles.
2. **Flat top-level `ontologies/`** — six dimension ontologies plus a full-wiki union, aggregated from BOTH wikis. No per-wiki nesting; the ontology layer is the global view.
3. **Per-folder `AGENTS.md` discipline** — every subdirectory carries its own instruction-as-code file so agents that open the directory learn local conventions before writing.
4. **Gateway contract** — every MCP call routes through `neuro-harness` (mcp2cli / ContextForge). InfraNodus runs locally per `project_infranodus_local_only.md`; vault writes go through TurboVault; source ingestion goes through `web-scrape-ingest`.

---

## Four layers, not three

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

## Multi-wiki coordination

The two wikis share one vault. Pages **should** cross-link across wiki boundaries — Obsidian resolves `[[name]]` to whichever subfolder contains the matching `.md` file, so a `deep-agent-wiki/concepts/walk-forward-validation.md` page can freely link `[[vectorbt]]` even though that page lives in `deep-tool-wiki/vectorbt/index.md`.

If two wikis ever name the same slug differently (rare but possible), use **wiki-scoped slugs**: `[[deep-agent-walk-forward-validation]]` vs `[[deep-tool-vectorbt-walk-forward]]`. Document the convention in the relevant `AGENTS.md`.

Collision check:

```bash
# Find slug collisions across wikis
find ~/Vaults/neuro-quant-vault/wikis -name '*.md' -exec basename {} .md \; \
  | sort | uniq -c | sort -rn | awk '$1>1'
```

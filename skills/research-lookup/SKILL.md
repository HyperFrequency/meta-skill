---
name: research-lookup
version: 0.1.0
description: Look up current research information using the Parallel Chat API (primary) or Perplexity sonar-pro-search (academic paper searches). Automatically routes queries to the best backend. Use for finding papers, gathering research data, and verifying scientific information against current web/scholarly sources. Do NOT use for queries requiring proprietary/paywalled databases or restricted full-text access, for structured lookups in named scientific databases (use database-lookup), for DOI-to-BibTeX or PubMed/Scholar metadata management (use citation-management), or for plain web search and URL extraction (use parallel-web).
allowed-tools: Read Write Edit Bash
license: MIT license
compatibility: PARALLEL_API_KEY and OPENROUTER_API_KEY required
metadata:
    skill-author: K-Dense Inc.
---

# Research Information Lookup

Real-time research information lookup with **intelligent dual-backend routing**:

- **Parallel Chat API** (`core` model): Default backend for all general research. Comprehensive, multi-source reports with inline citations via the OpenAI-compatible Chat API at `https://api.parallel.ai`.
- **Perplexity sonar-pro-search** (via OpenRouter): Used only for academic-specific paper searches where scholarly database access is critical.

The skill automatically detects query type and routes to the optimal backend.

## When to Use This Skill

- **Current Research Information**: Latest studies, papers, and findings
- **Literature Verification**: Check facts, statistics, or claims against current research
- **Background Research**: Gather context and evidence for scientific writing
- **Citation Sources**: Find relevant papers and studies to cite
- **Technical Documentation**: Specifications, protocols, or methodologies
- **Market/Industry Data**: Current statistics, trends, competitive intelligence
- **Recent Developments**: Emerging trends, breakthroughs, announcements

**Do NOT use for**: structured lookups in named scientific databases (use `database-lookup`); DOI-to-BibTeX or PubMed/Scholar metadata management (use `citation-management`); plain web search or URL extraction (use `parallel-web`); proprietary/paywalled full-text access (no backend can reach these).

## Backend Routing (Quick Reference)

```
Query arrives
    |
    +-- Academic keywords? (papers, DOI, journal, peer-reviewed, arxiv, meta-analysis...)
    |       YES --> Perplexity sonar-pro-search (academic mode)
    |
    +-- Everything else --> Parallel Chat API (core model)
```

Full keyword list, per-backend capabilities, response shapes, and manual override
flags: see `references/backend-routing.md`.

## Command-Line Usage

```bash
# Auto-routed research (recommended) — ALWAYS save to sources/
python research_lookup.py "your query" -o sources/research_YYYYMMDD_HHMMSS_<topic>.md

# Force a backend
python research_lookup.py "your query" --force-backend parallel  -o sources/research_<topic>.md
python research_lookup.py "your query" --force-backend perplexity -o sources/papers_<topic>.md

# JSON (max citation metadata) / batch
python research_lookup.py "your query" --json -o sources/research_<topic>.json
python research_lookup.py --batch "q1" "q2" "q3" -o sources/batch_research_<topic>.md
```

Environment variables, API specs (endpoints, models, rate limits), and error/fallback
behavior: see `references/api-reference.md`.

## MANDATORY: Save All Results to `sources/`

**Every result MUST be saved to the project's `sources/` folder** via the `-o` flag,
preserving all citations, source URLs, and DOIs. Before any new query, check `sources/`
(`ls sources/`) for an existing result and re-read it instead of re-querying.

Filename patterns, citation-preservation rules per format, rationale, and logging
conventions: see `references/saving-results.md`.

## Paper Quality Prioritization

When searching for papers, ALWAYS prioritize high-quality, influential work using
citation-count thresholds (by paper age) and venue quality tiers (Tier 1 premier
venues like Nature/Science/NeurIPS preferred). Full ranking tables: see
`references/paper-quality.md`.

## Complementary Tools

| Task | Tool |
|------|------|
| General web search / URL extraction | `parallel-web` skill |
| Deep research (any topic) | `research-lookup` or `parallel-web` |
| Academic paper search | `research-lookup` (auto-routes to Perplexity) |
| Structured lookups in named databases | `database-lookup` skill |
| Google Scholar / PubMed search | `citation-management` skill |
| DOI to BibTeX | `citation-management` skill |

## Integration with Scientific Writing

Supports literature review, methods validation, results contextualization, discussion
enhancement, and citation sourcing — **always save each lookup to `sources/`** so every
cited claim traces back to its raw research source.

## References

- `references/backend-routing.md` — routing keywords, per-backend capabilities, examples, overrides
- `references/api-reference.md` — env vars, API specs, CLI flags, error/fallback behavior
- `references/saving-results.md` — sources/ saving rules, citation preservation, logging
- `references/paper-quality.md` — citation ranking, venue tiers, author reputation, relevance scoring
- `references/query-best-practices.md` — structured query format, good vs poor queries, follow-up patterns

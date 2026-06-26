---
name: docs-dual-lookup
description: Query both Context7 and Augment Code (auggie) for library/framework documentation in parallel and synthesize the results. Use when looking up API references, code examples, framework usage, or library docs and you want broader/cross-validated coverage than a single source provides. Especially useful when one source is incomplete, outdated, or returns no results.
---

# Dual Documentation Lookup (Context7 + Augment Code)

Query Context7 and Augment Code in parallel and merge the answers. Use this when a single doc source is insufficient — they have different corpora and freshness, so the union usually beats either alone.

## When to use

- User asks about a library, framework, or API and wants reliable, current docs
- Single-source lookups have failed or returned thin results
- Cross-validation matters (e.g. checking that an API signature is current across sources)
- Building examples that draw on multiple ecosystems

## When NOT to use

- For general web search → use WebSearch
- For code in this repo → use Grep/Read
- For arXiv/scientific papers → use the paper-lookup or perplexity-search skills
- When you only need a quick check on one well-known library → use Context7 alone

## How it works

Both services are exposed as MCP servers in this environment:

- **Context7** (`mcp__context7__*`) — Upstash's curated up-to-date library docs database. Best for popular OSS libraries (React, Next.js, Tailwind, Postgres clients, etc.). Returns code-snippet-rich examples.
- **Auggie / Augment Code** (`mcp__auggie__*`) — Augment's context engine with broader framework + repo coverage and richer prose explanations.

## Procedure

1. **Frame the query.** Reduce to: `<library/framework name> + <specific topic>`. Example: `langchain + streaming output parsers`.

2. **Fire both lookups in parallel** in a single message with two MCP tool calls — one to context7, one to auggie. Do not serialize them.

3. **Compare the answers:**
   - If both agree → use the more concise/recent one, cite both
   - If they disagree → flag the disagreement and prefer the source with the more recent timestamp or version reference
   - If one returns nothing → use the other; note the gap
   - If both return nothing → fall back to WebSearch

4. **Synthesize.** Present a single answer with:
   - The recommended approach / API signature / code
   - A one-line note about source coverage (e.g. "confirmed by both" or "Context7 only — auggie had no entry")
   - Version/freshness if known

5. **Never blindly paste both raw responses.** Synthesize. The user wants an answer, not two answers.

## Authentication notes

- Context7 works without an API key (rate-limited). Higher limits with `CONTEXT7_API_KEY`.
- Auggie requires authentication via `auggie login` (the user must do this once interactively).
- If auggie returns an auth error, fall back to Context7 alone and tell the user auggie needs `auggie login`.

## Layered RAG fallback — qmd → qdrant → web lookup

This skill sits at the top of a **three-layer retrieval stack**. External
lookups (Context7 + Auggie) are the outer layer; the user's own offline
knowledge lives in the inner two. For HyperFrequency-forked tools the
offline stack usually has the answer; only escape to Context7/Auggie
when it doesn't.

**Layer 1 — qmd (local, fastest, tool-specific):**
- `qmd` is the local retrieval engine (BM25 + dense vector + rerank +
  query expansion) that ships with `neuro-link-recursive`.
- Pipeline: query → **qmd-query-expansion-1.7B Q4_K_M** (Qwen3-based,
  ~200 ms) → split into BM25 + vector queries → merge with RRF →
  **Qwen3-Reranker-0.6B Q8_0** rerank top-k → return.
- Corpus: the `02-KB-main/` deep-tool-wiki entries (per-tool
  `overview.md`, `pitfalls.md`, subsystem `index.md` leaves).
- Invoked by: `mcp__neuro-link-recursive__nlr_rag_query` or
  `nlr_rag_query_verified` (the latter refuses answers below
  confidence 0.6 or without source citations).
- Model prerequisites (install via `download_models.sh`, HF CLI):
  - `mradermacher/Octen-Embedding-8B-GGUF / Octen-Embedding-8B.f16.gguf` (4096-dim embedder)
  - `ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF / qwen3-reranker-0.6b-q8_0.gguf`
  - `tobil/qmd-query-expansion-1.7B-gguf / qmd-query-expansion-1.7B-q4_k_m.gguf`

**Layer 2 — Qdrant (local vector DB):**
- Two collections: `nlr_wiki` (vault text, 4096-dim cosine) and
  `math_symbols` (lookup for `\LaTeX` symbols). Both populated by qmd's
  initial ingest from `02-KB-main/`.
- Direct invocation: `mcp__neuro-link-recursive__nlr_rag_query` when you
  want raw vector hits without rerank.

**Layer 3 — Context7 + Auggie (remote, this skill):**
- Only when qmd returns nothing or the user needs external upstream
  coverage (e.g., a library not yet in the vault, or version-specific
  API checks).

### Decision rule

1. If the user's query is about a HyperFrequency-forked tool (see
   `/deep-tool-wiki` skill list — vectorbtpro, nautilus-trader,
   hftbacktest, pine-script, optuna, mlflow, h2o-3, etc.) → try qmd
   FIRST via `nlr_rag_query_verified`. Fall back to this skill only
   if qmd returns empty or low-confidence.
2. If the query is about an external library or framework not in the
   vault → skip qmd, go straight to this skill (Context7 + Auggie in
   parallel).
3. If both layers return empty → WebSearch + flag the gap to the user.

### Verifying qmd is actually running

Before trusting qmd's output:
- `~/.cache/qmd/models/` contains Qwen3 reranker + query-expansion `.gguf` files (~4 GB total)
- `$HOME/Dev/neuro-link/models/Octen-Embedding-8B.f16.gguf` exists (~8.5 GB)
- `llama-server` is listening on `127.0.0.1:8400` (embedding endpoint)
- `curl 127.0.0.1:6333/collections/nlr_wiki` returns `points_count > 0`

If any of these fails, qmd is degraded — skip Layer 1 and go straight to Context7/Auggie.

## Output format

```
**Answer:** <synthesized answer, code example if applicable>

**Sources:** Context7 ✓ | Auggie ✓  (or ✗ with reason)
**Version/freshness:** <if known>
```

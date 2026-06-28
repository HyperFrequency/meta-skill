---
name: neuro-quant-knowledge-rag-control-plane
description: >
  Control plane for the neuro-quant monorepo's knowledge / RAG substrate. Routes work
  across neuro-link (MCP/RAG server, vault health, auto-RAG hook, task queue), qmd
  (BM25 / dense / query-expansion / rerank retrieval sidecar), crawl-ingest-update
  (source ingestion and provenance), and deep-tool-wiki (canonical per-tool corpus).
  Use when the user says "neuro-link status", "qmd", "ingest a source", "ingest this",
  "deep-tool-wiki page", "refresh the wiki for X", or "auto-rag", or asks to inspect,
  repair, ingest, refresh, or query the repo-local RAG system, retrieval quality, wiki
  freshness, or ingest provenance. Open references/resource-map.md first, then load
  deep-tool-wiki/<tool>/wiki.md or 02-KB-main/<tool>/index.md only when needed. For Pine
  Script language-server implementation use neuro-quant-pine-language-tooling; for
  vectorized research, event-driven execution, or live trading use the matching quant
  sibling skill.
allowed-tools: Read, Grep, Glob, Bash
---

# Knowledge / RAG Control Plane

Use this family when the task is about the repository's knowledge substrate rather than a single quant library. Its job is to keep neuro-link, qmd, crawl-ingest-update, and deep-tool-wiki searchable, source-backed, and operationally safe.

## Scope

This family owns four related surfaces:

- `neuro-link`: top-level knowledge/memory control plane, Rust MCP/RAG entrypoint, vault health, task queue, and auto-RAG hook behavior.
- `qmd`: retrieval sidecar for BM25, dense search, query expansion, reciprocal-rank fusion, and reranking.
- `crawl-ingest-update`: source ingestion pipeline for URLs, repos, PDFs, arXiv, math-dense documents, and vault imports.
- `deep-tool-wiki`: canonical per-tool wiki corpus consumed by agents, qmd, and neuro-link.

Use this skill when the task matches one of these signals:
- deep-tool-wiki page or coverage work
- neuro-link status / RAG / vault health
- qmd retrieval quality, Qdrant or Neo4j docs ingestion
- ingesting a new source (URL, repo, PDF, arXiv)
- auto-RAG hook behavior
- k-dense-byok / resource lookup with full documentation

Do not use this skill for Pine Script language-server implementation work. Route those tasks to `neuro-quant-pine-language-tooling`.

## Required Workflow

1. Restate the goal, target repo/tool/surface, and acceptance evidence.
2. Open `references/resource-map.md` before loading broader docs.
3. Classify the request against the Operating Rules table below and pick a primary route.
4. Open `references/verification-checklist.md` for the smallest relevant proof path.
5. Use `references/handoff-template.md` when a long workflow should move to another family skill.
6. Load full docs only when needed from `deep-tool-wiki/<tool>/wiki.md` or `neuro-link/02-KB-main/<tool>/index.md`.
7. Separate verified facts, assumptions, missing resources, and blocked checks in the final answer.

## Operating Rules

Start by classifying the request:

| User intent | Primary route | Verification |
| --- | --- | --- |
| "what is in the brain", "neuro-link status", "health" | `neuro-link` status path | health probe plus explicit stale-index notes |
| "why did retrieval miss this", "improve RAG", "qmd" | `qmd` retrieval path | compare keyword, vector, expansion, and rerank behavior |
| "ingest this", "add this source" | `crawl-ingest-update` | raw artifact hash, sorted link, synthesis target |
| "refresh wiki for X", "deep-tool-wiki coverage" | `deep-tool-wiki` | coverage matrix and missing-section list |

State assumptions before doing writes. If the user has not named a target collection, wiki topic, or source, ask one clarifying question.

## neuro-link Pattern

Treat `neuro-link` as the dispatcher and audit layer. Reads should prefer MCP-backed or indexed paths when available; direct file reads are for infrastructure files and recovery.

Expected control-plane checks:

1. Confirm the active root and configured vault paths.
2. Check whether `neuro-link-recursive` and `neuro-link-http` are registered or reachable.
3. Check the auto-RAG hook path and recent hook logs before assuming retrieval is broken.
4. Compare indexed search results with direct wiki/source files if results disagree.
5. Report contradictions as index drift, not as fact resolution.

Knowledge writes should go through schema-aware update paths when available. Direct Markdown edits are acceptable only for repo-local draft content or when explicitly requested.

## qmd Pattern

Use qmd when recall quality matters. qmd is the retrieval sidecar, not the source of truth.

Minimum diagnostic loop:

1. Verify the CLI and version: `qmd --help` and, when available, `qmd --version`.
2. Identify the backend and collection: sqlite-owned collection or qdrant-backed collection.
3. Run a small query set that includes exact keyword, synonym, API-name, and concept queries.
4. Compare baseline search with `--rerank` where model cache is present.
5. Record latency and missing-model behavior separately from ranking quality.

Run the runnable **qmd Smoke Matrix** in `references/resource-map.md` against a tiny temporary collection before touching production collections.

Known risk to surface: qmd default embeddings can be dimension-incompatible with neuro-link's Octen-backed qdrant collections. Do not mix vector stores until the embedding dimension and model identity are confirmed.

## crawl-ingest-update Pattern

For new sources, preserve provenance first, synthesis second.

Required ingest contract:

- Raw artifact is immutable and content-hash addressable.
- Sorted artifact is a classified pointer or normalized copy.
- Synthesis page names its source, ingest date, confidence, and open gaps.
- Math and code blocks are preserved exactly unless a parser-specific canonicalization step is explicitly documented.

If the source is a PDF or math-dense paper, use the existing deep-ingest pipeline rather than ad hoc text extraction. If the source is a repo, ingest README, docs, examples, package manifests, and public API entrypoints before synthesizing. Fill the **Ingest Provenance Checklist** in `references/resource-map.md`.

## deep-tool-wiki Pattern

Use deep-tool-wiki as the canonical long-form tool corpus. A good page has:

- A sitemap or mental model at the top.
- Install/runtime facts separated from conceptual guidance.
- Code/API entrypoints with concrete file paths.
- Pitfalls, failure modes, and "not this tool" boundaries.
- Update provenance: source URLs, local paths, ingest date, and regeneration script if applicable.

Coverage work should produce a matrix, not vague prose. Mark each topic as `present`, `partial`, `stale`, or `missing`, with direct file paths.

## Progressive Disclosure

This skill keeps local resources in its own folder for immediate operation, but the full documentation belongs in deep-tool-wiki and the navigable leaf docs belong in 02-KB-main. Do not duplicate long API docs here. If a full doc is missing, use the generated stub path from the resource map and mark the lookup incomplete.

## Local Resources

- `references/resource-map.md`: family entry points, key runtime concepts (MCP routes, auto-RAG hook path, model-cache paths), wiki corpus sources, the qmd Smoke Matrix, the Ingest Provenance Checklist, and missing-doc status.
- `references/verification-checklist.md`: proof gates for this family.
- `references/handoff-template.md`: structured handoff for multi-step workflows.
- `evals/evals.json`: trigger, false-positive, and missing-resource cases.
- `agents/openai.yaml`: minimal UI metadata for skill discovery.

## Covered Tools

| Tool | Source | Full docs | KB lookup |
| --- | --- | --- | --- |
| neuro-link | `neuro-link` | `deep-tool-wiki/neuro-link/wiki.md` | `neuro-link/02-KB-main/neuro-link/index.md` |
| QMD | `deep-tool-wiki/qmd` | `deep-tool-wiki/qmd/wiki.md` | `neuro-link/02-KB-main/qmd/index.md` |
| k-dense-byok | `toolbox/k-dense-byok` | `deep-tool-wiki/k-dense-byok/wiki.md` | `neuro-link/02-KB-main/k-dense-byok/index.md` |
| vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` |
| Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` |
| pinelsp | `pinelsp` | `deep-tool-wiki/pinelsp/wiki.md` | `neuro-link/02-KB-main/pinelsp/index.md` |

## Guardrails

- Do not make trading, performance, API, or runtime claims from memory alone.
- Do not start services, pull large data, or mutate remote state unless the user asks for that surface.
- Do not mix vectorized research, event-driven execution, and live/execution operations without an explicit handoff.
- Prefer repo-local commands and docs over generic internet summaries.
- If strategy conversion uses an LSP or parser, keep syntax diagnostics separate from trading logic claims.
- Direct Markdown writes can bypass schema/index expectations in neuro-link; prefer schema-aware paths.
- Distinguish docs coverage from running service state: a deep-tool-wiki page can be conceptually current while local runtime wiring is stale.

## Done Criteria

A knowledge/RAG task is done when the answer includes:

- The exact surface touched or inspected.
- The evidence path or command output used.
- Any stale, missing, or contradictory state.
- A next action that is small enough to run safely.

For draft-only work, list the proposed files and explicitly say no runtime state was changed.

## Output Contract

Return the target tool, resources opened, evidence checked, findings, gaps, and the next verification step.

# Knowledge RAG Control Plane Resource Map

Open this file before loading full documentation. It keeps the skill useful without pulling large wiki files into context.

| Tool | Display | Source | Full docs | KB lookup | Status |
| --- | --- | --- | --- | --- | --- |
| `neuro-link` | neuro-link | `neuro-link` | `deep-tool-wiki/neuro-link/wiki.md` | `neuro-link/02-KB-main/neuro-link/index.md` | existing-kb-missing-deep |
| `qmd` | QMD | `deep-tool-wiki/qmd` | `deep-tool-wiki/qmd/wiki.md` | `neuro-link/02-KB-main/qmd/index.md` | existing-deep-missing-kb |
| `k-dense-byok` | k-dense-byok | `toolbox/k-dense-byok` | `deep-tool-wiki/k-dense-byok/wiki.md` | `neuro-link/02-KB-main/k-dense-byok/index.md` | missing |
| `vectorbtpro` | vectorbt.pro | `toolbox/vectorbt.pro` | `deep-tool-wiki/vectorbtpro/wiki.md` | `neuro-link/02-KB-main/vectorbtpro/index.md` | existing-full |
| `nautilus-trader` | Nautilus Trader | `toolbox/nautilus_trader` | `deep-tool-wiki/nautilus-trader/wiki.md` | `neuro-link/02-KB-main/nautilus-trader/index.md` | existing-full |
| `pinelsp` | pinelsp | `pinelsp` | `deep-tool-wiki/pinelsp/wiki.md` | `neuro-link/02-KB-main/pinelsp/index.md` | missing |

## Lookup Order

1. Use the source path when the question is about repo-local implementation.
2. Use the KB path for fast navigation, subsystem discovery, signatures, and examples.
3. Use the deep-tool-wiki path for comprehensive documentation, architecture, pitfalls, and ontology.
4. Use generated stubs only as coverage todos; do not treat a stub as source authority.

## Family Entry Points

These name the files and runtime surfaces the skill points to. They are not a guarantee that every runtime service is currently active.

| Component | Role | Primary local paths | Verification |
| --- | --- | --- | --- |
| `neuro-link` | Rust MCP/RAG server, vault control plane, hooks, task queue | `neuro-link/`, `neuro-link/.claude/skills/neuro-link/SKILL.md`, `neuro-link/hooks/` | `make proof`, `neuro-link/pkg/scripts/verify.py`, MCP list/health checks |
| `qmd` | Local retrieval sidecar: BM25, vector, query expansion, rerank | `deep-tool-wiki/qmd/wiki.md`, `deep-tool-wiki/qmd/code.md`, `deep-tool-wiki/qmd/pitfalls.md` | `qmd --help`, collection search smoke, rerank smoke if models exist |
| `crawl-ingest-update` | Source ingestion and canonicalization pipeline | `neuro-link/.claude/skills/crawl-ingest-update/SKILL.md`, `neuro-link/.claude/skills/crawl-ingest-update/scripts/` | hash-preserving raw artifact, sorted artifact, synthesis page |
| `deep-tool-wiki` | Canonical per-tool wiki corpus | `deep-tool-wiki/*/wiki.md`, `deep-tool-wiki/*/code.md`, `deep-tool-wiki/*/pitfalls.md` | coverage matrix, qmd ingest/search, stale-source scan |

## Key Runtime Concepts

- `neuro-link-recursive`: stdio MCP route for schema-aware wiki and memory operations.
- `neuro-link-http`: HTTP MCP/RAG route, typically expected at `http://127.0.0.1:8787/mcp`.
- TurboVault: vault-side lexical and graph operations where available.
- Auto-RAG hook: `neuro-link/hooks/auto-rag-inject.sh`; injects relevant wiki context into prompts.
- qmd model cache: `~/.cache/qmd/models/` for reranker and query-expansion GGUFs.
- neuro-link embedder cache: `neuro-link/models/` or `~/neuro-link-models/` for Octen embeddings.

## Wiki Corpus Sources

| Corpus | Current files | Notes for skill docs |
| --- | --- | --- |
| qmd | `deep-tool-wiki/qmd/wiki.md`, `code.md`, `pitfalls.md` | Good S-tier seed because it separates conceptual flow, subprocess contract, and pitfalls. |
| pine-script | `deep-tool-wiki/pine-script/wiki.md`, `assets/refgraph-builtins.mmd`, `assets/refgraph-strategy.mmd` | Belongs mostly to Pine family, but RAG family should know it as a retrieval target. |
| Ray / Qlib / xfeat | `deep-tool-wiki/ray-distributed/wiki.md`, `deep-tool-wiki/qlib/wiki.md`, `deep-tool-wiki/xfeat/wiki.md` | Existing auto-RAG context shows these are indexed/retrievable and should remain in coverage scans. |
| Other quant tools | `deep-tool-wiki/*/wiki.md` | Coverage should be table-driven across all tool folders. |

## qmd Smoke Matrix

Use a tiny temporary collection before touching production collections:

```bash
qmd --help
printf '%s\n' 'vectorbtpro Portfolio from_signals percent sizing' > /tmp/qmd-smoke.md
qmd --db-path /tmp/qmd-smoke.sqlite document add \
  --collection smoke \
  --document-id smoke-1 \
  --markdown-file /tmp/qmd-smoke.md
qmd --db-path /tmp/qmd-smoke.sqlite search \
  --collection smoke \
  --query 'portfolio sizing' \
  --top-k 3
```

Only add `--rerank` after confirming the qmd model cache exists.

## Ingest Provenance Checklist

- Source URL or local path.
- Retrieval time.
- SHA256 of raw artifact.
- Parser/converter used.
- Sorted classification.
- Generated wiki target.
- Known gaps or failed parses.

## Risks To Preserve

- Direct Markdown writes can bypass schema/index expectations in neuro-link.
- qmd and neuro-link can use incompatible embedding dimensions.
- Rerank/query-expansion cold starts are latency issues, not necessarily retrieval failures.
- Math PDFs need the dedicated Marker/MinerU/canonicalization flow; plain text extraction is not enough.
- Existing deep-tool-wiki pages can be conceptually current while local runtime wiring is stale; distinguish docs coverage from running service state.

## Context-Rot Boundary

If the workflow grows beyond this family, fill `handoff-template.md` and switch to the next skill instead of carrying all resources forward.

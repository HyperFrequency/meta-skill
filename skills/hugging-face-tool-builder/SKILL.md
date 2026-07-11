---
name: hugging-face-tool-builder
version: 0.1.0
description: >-
  Use when the user wants to build reusable command-line scripts or utilities
  that fetch, enrich, filter, or automate data from the Hugging Face Hub API
  (models, datasets, Spaces, papers, trending, collections) — especially when
  calls must be chained, piped, or repeated as part of a workflow. Typical jobs:
  find models tied to an arXiv paper, rank models by downloads, extract
  model-card frontmatter, or stream metadata as NDJSON for a pipeline. Covers
  HF_TOKEN auth hygiene, discovering the API shape via the OpenAPI spec with jq,
  the `hf` CLI, and composable script design in bash / Python / TypeScript. NOT
  for one-off interactive lookups (use the Hugging Face MCP server or
  `hugging-science`), for training / fine-tuning / serving models, or for
  turning an arbitrary MCP / OpenAPI / GraphQL endpoint into a CLI (use
  `mcp2cli`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "huggingface_hub / hf CLI (Apache-2.0)"
---

# Hugging Face Tool Builder

## Overview

Turn Hugging Face Hub data access into small, composable, reusable command-line
tools. When a task will be repeated, automated, or requires stitching several
API calls together, do not run ad-hoc one-liners each time — build a script that
takes arguments, emits machine-readable output, and pipes cleanly into the next
stage.

There are two access layers, and good tools mix them:

- **The REST API** at `https://huggingface.co/api/*` — JSON over HTTP for
  models, datasets, Spaces, collections, papers, trending, and account info.
- **The `hf` CLI** — repository content and Hub infrastructure (download,
  upload, auth, cache, jobs, endpoints). Replaces the deprecated
  `huggingface-cli` / `huggingface_hub` CLI.

Model and dataset **cards** (`README.md` with YAML frontmatter) are readable
directly from a repo, either via the API's `raw`/`resolve` paths or `hf download`.

## When to Use This Skill

Engage when the user wants a **reusable artifact**, not a single answer:

- "Build a script that finds all models citing arXiv paper X."
- "I need to rank the top trending models by downloads every morning."
- "Extract license + pipeline tag from these 200 model cards as a table."
- "Chain trending → model metadata → card parsing into one pipeline."
- Any task described as repeated, automated, batch, scheduled, or "for each".

## When NOT to Use This Skill

- **One-off interactive lookup** ("what's the license of Llama-3?") — use the
  Hugging Face MCP server (`hub_repo_details`, `hub_repo_search`, `paper_search`,
  `space_search`) or the `hugging-science` skill for curated scientific resources.
- **Training, fine-tuning, or serving** a model — use `transformers`,
  `fine-tuning`, or the inference-serving skills.
- **Wrapping some other API** as a CLI — use `mcp2cli` for arbitrary
  MCP / OpenAPI / GraphQL endpoints. This skill is Hugging-Face-specific.
- **Loading data into training code** — use the `datasets` library directly;
  this skill is about the *metadata/discovery* API, not the data plane.

## Authentication (HF_TOKEN)

Read the token from the `HF_TOKEN` environment variable and send it as a Bearer
header. It raises rate limits and unlocks gated/private repos:

```bash
curl -s -H "Authorization: Bearer ${HF_TOKEN}" "https://huggingface.co/api/models?limit=3"
```

Make auth **optional but automatic**: if `HF_TOKEN` is set, add the header;
otherwise fall back to anonymous (public) access. Never `echo`, log, or print the
token value — build the header array/dict from the env var and pass it straight
to the request. See `references/script-patterns.md` for the idiomatic
conditional-header pattern in each language.

## The API Surface

Main endpoints under `https://huggingface.co`:

```
/api/models        /api/datasets      /api/spaces
/api/collections   /api/daily_papers  /api/trending
/api/whoami-v2     /api/settings      /api/notifications
/oauth/userinfo
```

Detail and search patterns you will reach for constantly:

- Single repo: `/api/models/{id}`, `/api/datasets/{id}`, `/api/spaces/{id}`
- Search + filter: `/api/models?search=<term>&limit=<n>&sort=downloads&direction=-1`
- Papers on a model: arXiv IDs appear as `arxiv:<id>` entries in the repo's `tags`
- Raw card: `https://huggingface.co/{id}/raw/main/README.md`

Full parameter tables, filter/sort options, trending response shape, and the
arXiv-tag convention live in **`references/api-endpoints.md`**.

## Discovering the API Shape

The API is documented with OpenAPI at
`https://huggingface.co/.well-known/openapi.json`. **Do not fetch and read it
whole — it is far too large.** Query it with `jq` instead:

```bash
# List every endpoint path
curl -s "https://huggingface.co/.well-known/openapi.json" | jq '.paths | keys | sort'

# Inspect one endpoint's parameters/schema
curl -s "https://huggingface.co/.well-known/openapi.json" | jq '.paths["/api/models"]'
```

Also probe live endpoints with a **small** `limit` to learn the JSON shape
before committing to a design — representative, cheap, easy to eyeball.

## The `hf` CLI

Use `hf` for repo content and Hub infrastructure the REST API does not cover
(downloading files, uploads, auth, cache, jobs, inference endpoints). Key
commands: `auth`, `download`, `upload`, `repo`, `repo-files`, `cache`, `env`,
`jobs`, `endpoints`. It reads `HF_TOKEN` automatically and accepts `--token`.
For the tool-builder's view — reading cards, listing repos as data — see
**`references/hf-cli.md`**; for exhaustive CLI coverage use the sibling
`hugging-face-cli` skill instead of duplicating it here.

## Script Design Rules

Follow these when authoring any tool (they are what make the output reusable and
pipe-friendly):

1. Every script accepts `--help` describing its inputs, outputs, and env vars.
2. Test non-destructive scripts before handing them to the user; confirm before
   anything that writes or uploads.
3. Prefer a **shell** script. Reach for Python or TypeScript only when
   complexity, JSON handling, or async warrants it.
4. Honor `HF_TOKEN` as an optional Bearer header (see above).
5. **Investigate the API shape first**, then design. Prefer piping and chaining
   over monolithic logic; keep each tool doing one thing.
6. Emit machine-readable output — raw JSON, or **NDJSON** (one object per line)
   for streaming stages — so downstream `jq` and pipes just work.
7. Share concrete usage examples once the tool works.
8. Surface clarifying questions when requirements are ambiguous; do not guess
   silently.

## Composable Patterns

The payoff is Unix-style composition. A few shapes:

```bash
# top 10 of 50 models by downloads
baseline_hf_api.sh 50 | jq '[.[] | {id, downloads}] | sort_by(.downloads) | reverse | .[:10]'

# fan out: list ids -> enrich each -> re-sort the stream
baseline_hf_api.sh 50 | jq -r '.[].id' | hf_enrich_models.sh | jq -s 'sort_by(.downloads) | reverse | .[:10]'

# card frontmatter across explicit ids
printf '%s\n' openai/gpt-oss-120b meta-llama/Meta-Llama-3.1-8B \
  | hf_model_card_frontmatter.sh | jq -s 'map({id, license, has_extra_gated_prompt})'
```

Ready-to-adapt reference tools — baseline fetchers (bash/Python/TypeScript), a
stdin→NDJSON enricher, an arXiv-paper model finder, a trending-papers walker,
and a card-frontmatter extractor — are in **`references/script-patterns.md`**.

## References

- **`references/api-endpoints.md`** — endpoint catalogue, query/filter/sort
  params, OpenAPI discovery recipes, trending response shape, arXiv-tag convention.
- **`references/script-patterns.md`** — full example tools in bash, Python, and
  TypeScript; the conditional-auth-header idiom; NDJSON streaming; piping recipes;
  failure-mode handling.
- **`references/hf-cli.md`** — `hf` CLI command and flag reference, card download,
  auth, and common pitfalls.

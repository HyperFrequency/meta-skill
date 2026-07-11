# Hugging Face Hub REST API — Endpoint Reference

Base host: `https://huggingface.co`. All responses are JSON. Auth is a Bearer
header (`Authorization: Bearer $HF_TOKEN`) — optional for public data, required
for private/gated repos and higher rate limits.

> Treat exact parameter names as *probable, not guaranteed*. The API evolves.
> Before hard-coding a query, confirm the shape against the OpenAPI spec and a
> small live probe (see "Discovering the shape" below). Never invent a filter
> that you have not seen echoed by the live API.

## Endpoint catalogue

| Path | What it returns | Auth |
|------|-----------------|------|
| `/api/models` | List/search model repos | optional |
| `/api/models/{id}` | One model's full metadata | optional (req. if gated) |
| `/api/models/{id}/revision/{rev}` | Model metadata at a revision/branch/tag | optional |
| `/api/datasets` | List/search dataset repos | optional |
| `/api/datasets/{id}` | One dataset's metadata | optional |
| `/api/spaces` | List/search Spaces | optional |
| `/api/spaces/{id}` | One Space's metadata (incl. `sdk`) | optional |
| `/api/collections` | List collections | optional |
| `/api/collections/{namespace}/{slug}-{id}` | One collection's items | optional |
| `/api/daily_papers` | Curated "daily papers" feed | optional |
| `/api/trending` | Recently trending repos | optional |
| `/api/whoami-v2` | Identity, orgs, token scopes | **required** |
| `/api/settings` | Account settings | **required** |
| `/api/notifications` | User notifications | **required** |
| `/oauth/userinfo` | OIDC userinfo | **required** |

`{id}` is the full `owner/name` repo id (e.g. `meta-llama/Llama-3.2-1B`).

## Listing and search parameters (`/api/models`, `/api/datasets`, `/api/spaces`)

Common query parameters (verify against OpenAPI before relying on edge cases):

| Param | Meaning | Example |
|-------|---------|---------|
| `search` | Free-text match on id/name | `search=distilbert` |
| `author` | Filter by owner/org | `author=google` |
| `filter` | Filter by tag(s); repeatable | `filter=text-generation&filter=pytorch` |
| `sort` | Sort key | `sort=downloads`, `sort=likes`, `sort=lastModified`, `sort=trendingScore` |
| `direction` | `-1` = descending | `direction=-1` |
| `limit` | Max results | `limit=50` |
| `full` | Return full metadata objects | `full=true` |
| `expand` | Expand specific fields (repeatable) | `expand[]=downloads&expand[]=likes` |

```bash
# Top 10 text-generation models by downloads
curl -s -H "Authorization: Bearer ${HF_TOKEN}" \
  "https://huggingface.co/api/models?filter=text-generation&sort=downloads&direction=-1&limit=10" \
  | jq -r '.[] | "\(.id)\t\(.downloads)"'
```

Keep `limit` small while exploring — a `limit=3` probe is enough to learn the
object shape without paging cost.

## Single-repo object (typical fields)

`GET /api/models/{id}` returns an object that commonly includes:

- `id`, `author`, `sha`, `lastModified`, `createdAt`
- `downloads`, `likes`, `gated` (`false` | `"auto"` | `"manual"`)
- `pipeline_tag`, `library_name`
- `tags` — array of strings (see arXiv convention below)
- `siblings` — repo files: `[{ "rfilename": "..." }, ...]`
- `cardData` — parsed YAML frontmatter of the model card
- `config` — model config (when present)

Datasets and Spaces mirror this shape; Spaces add `sdk` (`gradio`, `streamlit`,
`docker`, `static`) and runtime fields.

## The arXiv-tag convention (models ↔ papers)

Papers are linked to repos through **tags**, not a dedicated field. When a repo
cites an arXiv paper, its `tags` array contains an entry of the form
`arxiv:<id>` (e.g. `arxiv:1910.01108`). This drives both directions:

```bash
# Models that cite a specific paper — search with the arxiv: prefix (URL-encode ':')
curl -s "https://huggingface.co/api/models?search=arxiv%3A1910.01108&limit=50" \
  | jq -r '.[].id'

# Papers cited by a model — pull arxiv: ids out of its tags
curl -s "https://huggingface.co/api/models/microsoft/DialoGPT-medium" \
  | jq -r '.tags[] | select(startswith("arxiv:")) | ltrimstr("arxiv:")'
```

If an `arxiv:`-prefixed search returns nothing, retry the bare id/term as a
broader fallback — narrow tag searches often miss models that only mention the
paper in prose.

## Trending response shape

`GET /api/trending?type=model&limit=N` (also `type=dataset`, `type=space`)
returns a wrapper, not a bare array:

```json
{ "recentlyTrending": [ { "repoType": "model", "repoData": { "id": "...", "downloads": 0, "likes": 0 } } ] }
```

```bash
curl -s "https://huggingface.co/api/trending?type=model&limit=5" \
  | jq -r '.recentlyTrending[].repoData.id'
```

## Reading cards and files directly

Model/dataset/Space cards are `README.md` with YAML frontmatter, fetchable
without the API:

- Raw card: `https://huggingface.co/{id}/raw/main/README.md`
- Resolve any file: `https://huggingface.co/{id}/resolve/main/{path}`
- Datasets: prefix the path with `/datasets/`; Spaces: `/spaces/`

```bash
curl -sL -H "Authorization: Bearer ${HF_TOKEN}" \
  "https://huggingface.co/meta-llama/Llama-3.2-1B/raw/main/README.md"
```

`resolve` follows LFS redirects to the actual bytes; `raw` returns the file as
stored (for text like `README.md`, both give you the card). Gated repos require
a token that has accepted the repo's terms.

## Discovering the shape (OpenAPI)

The full spec lives at `https://huggingface.co/.well-known/openapi.json`. **It is
too large to read whole — always slice it with `jq`.**

```bash
# Every documented path
curl -s "https://huggingface.co/.well-known/openapi.json" | jq '.paths | keys | sort'

# One endpoint's parameters + response schema
curl -s "https://huggingface.co/.well-known/openapi.json" | jq '.paths["/api/models"]'

# Just the parameter names an endpoint accepts
curl -s "https://huggingface.co/.well-known/openapi.json" \
  | jq -r '.paths["/api/models"].get.parameters[].name'
```

Pair the spec (authoritative parameter list) with a `limit=3` live probe
(authoritative response shape) before committing to a script's design.

# Script Patterns — composable Hugging Face tools

Reusable, pipe-friendly tools for the Hugging Face Hub API. Every script here
follows the same contract: accept `--help`, honor `HF_TOKEN` as an *optional*
Bearer header, and emit machine-readable output (raw JSON, or NDJSON — one JSON
object per line — for streaming stages). Adapt these skeletons; do not treat
them as frozen.

## The conditional-auth-header idiom

The single most reused pattern: add the auth header **only if** `HF_TOKEN` is
set, so the same tool works anonymously or authenticated. Never echo the value.

**bash** — build a header array (empty when no token):

```bash
headers=()
if [[ -n "${HF_TOKEN:-}" ]]; then
  headers=(-H "Authorization: Bearer ${HF_TOKEN}")
fi
curl -s "${headers[@]}" "https://huggingface.co/api/models?limit=3"
```

**Python** — build a dict (empty when no token):

```python
import os, urllib.request
token = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {token}"} if token else {}
req = urllib.request.Request(url, headers=headers)
```

**TypeScript** — same shape:

```ts
const token = process.env.HF_TOKEN;
const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
await fetch(url, { headers });
```

## Baseline fetcher (three languages, identical behavior)

Fetch a small list of models, print raw JSON, `HF_TOKEN`-aware. The bash version
is the default; reach for Python/TS only when you need richer JSON handling or
async.

`baseline_hf_api.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
[[ "${1:-}" == "--help" ]] && { echo "usage: baseline_hf_api.sh [limit]"; exit 0; }
LIMIT="${1:-3}"
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { echo "Error: limit must be a number" >&2; exit 1; }
headers=()
[[ -n "${HF_TOKEN:-}" ]] && headers=(-H "Authorization: Bearer ${HF_TOKEN}")
curl -s "${headers[@]}" "https://huggingface.co/api/models?limit=${LIMIT}"
```

`baseline_hf_api.py` (stdlib only, no deps):

```python
#!/usr/bin/env python3
import os, sys, urllib.request
if len(sys.argv) > 1 and sys.argv[1] == "--help":
    print("usage: baseline_hf_api.py [limit]"); raise SystemExit
limit = sys.argv[1] if len(sys.argv) > 1 else "3"
if not limit.isdigit():
    print("Error: limit must be a number", file=sys.stderr); raise SystemExit(1)
token = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {token}"} if token else {}
req = urllib.request.Request(f"https://huggingface.co/api/models?limit={limit}", headers=headers)
with urllib.request.urlopen(req) as r:
    sys.stdout.write(r.read().decode())
```

`baseline_hf_api.tsx` (run with `tsx`/Bun, uses global `fetch`):

```ts
#!/usr/bin/env tsx
const arg = process.argv[2];
if (arg === "--help") { console.log("usage: baseline_hf_api.tsx [limit]"); process.exit(0); }
const limit = arg ?? "3";
if (!/^\d+$/.test(limit)) { console.error("Error: limit must be a number"); process.exit(1); }
const token = process.env.HF_TOKEN;
const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
const res = await fetch(`https://huggingface.co/api/models?limit=${limit}`, { headers });
if (!res.ok) { console.error(`Error: ${res.status} ${res.statusText}`); process.exit(1); }
process.stdout.write(await res.text());
```

## Composable enricher (stdin → NDJSON)

The workhorse of pipelines: read model ids on stdin, fetch each one's metadata,
emit one compact JSON object per line. NDJSON streams cleanly into `jq`.

`hf_enrich_models.sh` (core loop):

```bash
#!/usr/bin/env bash
set -euo pipefail
headers=()
[[ -n "${HF_TOKEN:-}" ]] && headers=(-H "Authorization: Bearer ${HF_TOKEN}")

process_id() {
  local id="$1"; [[ -z "$id" ]] && return 0
  local resp; resp=$(curl -s "${headers[@]}" "https://huggingface.co/api/models/${id}" || true)
  # Guard: empty body, non-JSON, or an {"error": ...} payload each get a typed error line
  if [[ -z "$resp" ]] || ! jq -e . >/dev/null 2>&1 <<<"$resp"; then
    jq -cn --arg id "$id" '{id:$id, error:"request_failed"}'; return 0
  fi
  if jq -e '.error' >/dev/null 2>&1 <<<"$resp"; then
    jq -cn --arg id "$id" '{id:$id, error:"not_found"}'; return 0
  fi
  jq -c --arg id "$id" '{id:(.id//$id), downloads:(.downloads//0), likes:(.likes//0),
    pipeline_tag:(.pipeline_tag//"unknown"), tags:(.tags//[])}' <<<"$resp"
}

# Accept ids as args OR on stdin
if [[ $# -gt 0 ]]; then for id in "$@"; do process_id "$id"; done; exit 0; fi
[[ -t 0 ]] && { echo "usage: ... | hf_enrich_models.sh   (ids on stdin)"; exit 1; }
while IFS= read -r id; do process_id "$id"; done
```

Emitting a typed `{"id":..., "error":...}` line instead of aborting keeps the
stream flowing when one id 404s — the consumer filters errors downstream.

## Card frontmatter extractor (NDJSON)

Download each model's `README.md` via `hf download`, parse the YAML frontmatter,
and emit a flat record (`license`, `pipeline_tag`, `library_name`, `tags`,
`has_extra_gated_prompt`, …). Use a real YAML pass in Python rather than
regexing the block. Sketch:

```bash
#!/usr/bin/env bash
set -euo pipefail
command -v hf >/dev/null || { echo "Error: hf CLI required" >&2; exit 1; }
token_args=(); [[ -n "${HF_TOKEN:-}" ]] && token_args=(--token "$HF_TOKEN")
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

process_id() {
  local id="$1"; [[ -z "$id" ]] && return 0
  local dir="$tmp/${id//\//_}"
  if ! hf download "$id" README.md --local-dir "$dir" "${token_args[@]}" >/dev/null 2>&1; then
    jq -cn --arg id "$id" '{id:$id, error:"download_failed"}'; return 0
  fi
  # Parse the frontmatter block between the first two '---' fences, emit one JSON line
  MODEL_ID="$id" README="$dir/README.md" python3 parse_frontmatter.py
}
while IFS= read -r id; do process_id "$id"; done
```

Extract the fields you need in `parse_frontmatter.py` (split on the `---`
fences, load with a YAML parser, `json.dumps` a whitelist of keys). Flag gating
with a boolean like `has_extra_gated_prompt = "extra_gated_prompt" in frontmatter`.

## Paper ↔ model finders

**Models citing a paper** — search with the `arxiv:` prefix, fall back to a bare
search when the tag search is empty:

```bash
term="$1"; enc="arxiv%3A${term}"
resp=$(curl -s "https://huggingface.co/api/models?search=${enc}&limit=50")
if [[ "$resp" == "[]" || -z "$resp" ]]; then           # retry broader
  resp=$(curl -s "https://huggingface.co/api/models?search=${term}&limit=50")
fi
jq -r '.[] | "\(.id)\tdl=\(.downloads//0)\ttask=\(.pipeline_tag//"?")"' <<<"$resp"
```

**Papers cited by a model / trending models** — read metadata, then pull arXiv
references out of `tags` and out of the card prose (arXiv urls, `arXiv:NNNN.NNNNN`
ids, DOIs). Walk trending with `/api/trending?type=model&limit=N` →
`.recentlyTrending[].repoData.id`, then feed each id through the same extractor.

## Piping recipes

```bash
# Top 10 of 50 by downloads, no intermediate files
baseline_hf_api.sh 50 | jq '[.[] | {id, downloads}] | sort_by(.downloads) | reverse | .[:10]'

# Fan out: list ids -> enrich each -> re-sort the whole NDJSON stream
baseline_hf_api.sh 50 | jq -r '.[].id' | hf_enrich_models.sh \
  | jq -s 'sort_by(.downloads) | reverse | .[:10]'

# Card frontmatter across explicit ids -> compact table
printf '%s\n' openai/gpt-oss-120b meta-llama/Llama-3.2-1B \
  | hf_model_card_frontmatter.sh | jq -s 'map({id, license, has_extra_gated_prompt})'
```

`jq -s` ("slurp") turns an NDJSON stream back into one array when you need a
global sort or aggregate; keep it *out* of the middle of a pipe so stages stay
streaming.

## Failure modes to handle

- **Empty / non-JSON body** — network blip or HTML error page. Guard with
  `jq -e .` before parsing; emit a typed error line, do not crash the stream.
- **`{"error": "..."}` payloads** — a 200 can still carry an error object
  (missing repo, gated without access). Check `.error` explicitly.
- **Gated / private repos** — 401/403 without a token that has accepted terms.
  Surface a hint to set `HF_TOKEN`; do not silently drop the record.
- **Rate limiting (429)** — anonymous limits are low. Setting `HF_TOKEN` raises
  them; for large fans, add a small sleep or backoff between requests.
- **Deleted/renamed repos** — 404. Keep going; report the id in the error line.
- **Large OpenAPI spec** — never read it whole; always `jq`-slice it.

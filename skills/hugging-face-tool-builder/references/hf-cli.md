# The `hf` CLI — the tool-builder's slice

The `hf` command-line tool (shipped with `huggingface_hub`, formerly the
`huggingface-cli` entrypoint) reaches Hub content and infrastructure the REST
API does not expose over plain HTTP: file transfers, uploads, repo lifecycle,
local cache, cloud Jobs, and Inference Endpoints.

**This page covers only what a data/tool-builder reaches for** — reading cards,
pulling files, and listing repos as a data source. For the full command surface
(uploads, repo management, cache pruning, Jobs, Endpoints, CI auth), use the
sibling **`hugging-face-cli`** skill rather than duplicating it here.

## Command groups (orientation)

```
hf auth        login / logout / whoami / switch     # stored token management
hf download    pull files/repos from the Hub        # → cache or --local-dir
hf upload      push files/folders to the Hub        # (see hugging-face-cli)
hf repo        create / delete / move / branch / tag # repo lifecycle
hf repo-files  delete files inside a repo
hf cache       ls / rm / prune / verify             # local cache hygiene
hf jobs        run cloud GPU jobs                    # (see hugging-face-cli)
hf endpoints   manage Inference Endpoints            # (see hugging-face-cli)
hf env         print environment / cache locations
hf version     print CLI version
```

Every command supports `--help`. `hf` reads `HF_TOKEN` from the environment
automatically and accepts a `--token` override on any command.

## What tool-builders use it for

### Read a card without the API

`hf download <repo_id> README.md` fetches just the card, honoring token/gating,
into a local dir you control — handy inside an NDJSON pipeline:

```bash
tmp=$(mktemp -d)
hf download meta-llama/Llama-3.2-1B README.md --local-dir "$tmp" ${HF_TOKEN:+--token "$HF_TOKEN"}
cat "$tmp/README.md"   # YAML frontmatter + prose
```

Use `--repo-type dataset` or `--repo-type space` for those repo kinds. Add
`--revision <branch|tag|sha>` to pin a version. This is the transport under the
`hf_model_card_frontmatter.sh` pattern in `references/script-patterns.md`.

### Pull specific files by glob

```bash
hf download <repo_id> --include "*.json" --exclude "*.safetensors" --local-dir ./meta
```

Good for grabbing just `config.json` / `tokenizer_config.json` as structured
inputs without downloading multi-GB weights.

### List repos as a data source

`hf models ls` / `hf datasets ls` / `hf spaces ls` mirror the search API from the
terminal and can feed ids into a pipe:

```bash
hf models ls --filter text-generation --sort downloads --limit 20 \
  | awk 'NR>1{print $1}' | hf_enrich_models.sh   # ids -> NDJSON
```

When you need programmatic control over the results, prefer hitting `/api/models`
directly (see `references/api-endpoints.md`) — the JSON is easier to pipe than
the CLI's table output.

## Auth for scripts

- Non-interactive: set `HF_TOKEN` in the environment; `hf` picks it up with no
  `login`. Or `hf auth login --token "$HF_TOKEN"` to persist it.
- Confirm identity/scopes with `hf auth whoami`.
- Note: a token supplied via the `HF_TOKEN` env var is **not** cleared by
  `hf auth logout` — unset the variable to drop it.
- Never echo the token; reference it only by variable name.

## Pitfalls

- The old `huggingface-cli` entrypoint is deprecated — use `hf`. Older docs and
  scripts calling `huggingface-cli` still work but should be migrated.
- `hf download` prints the resolved local path last; use `--quiet` to capture
  *only* that path when scripting.
- Default per-request download timeout is short (~10s). Raise
  `HF_HUB_DOWNLOAD_TIMEOUT` for slow links or large shards.
- Set `HF_HUB_ENABLE_HF_TRANSFER=1` (with the `hf_transfer` extra installed) for
  faster large downloads.
- For anything that writes (`upload`, `repo create/delete`, `cache rm/prune`),
  confirm with the user first and prefer `--dry-run`/`-y` deliberately — those
  live in the `hugging-face-cli` skill's reference, not here.

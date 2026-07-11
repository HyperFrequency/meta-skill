# `hf` CLI — Command Reference

Authoritative option tables for the `hf` command groups, verified against
`huggingface_hub` CLI **1.21.0**. Run `hf <group> <verb> --help` for the live,
version-exact list — flags evolve between releases.

## Global concepts

- **`REPO_ID`** — `namespace/name` (e.g. `meta-llama/Llama-3.2-1B-Instruct`).
  A bare name resolves under your own namespace. Datasets/Spaces can be written
  `datasets/owner/name` / `spaces/owner/name` or targeted with `--repo-type`.
- **`--repo-type` / `--type`** — `model` (default), `dataset`, or `space`.
  `--type` is the short alias; both are accepted on `download`, `upload`,
  `upload-large-folder`, `repos …`, and `cache verify`.
- **`--revision`** — branch name, tag, or commit hash. Also accepts PR refs like
  `refs/pr/1`.
- **`--token`** — overrides the stored credential for a single call. Prefer the
  `HF_TOKEN` env var in CI. Never echo the value.
- **`hf://` URIs** — `hf://[TYPE/]owner/name/path`. Used by `cp`, `sync`,
  `repos cp`, and job volume mounts (`-v`).
- **Output format** — most read commands accept
  `--format [auto|human|agent|json|quiet]`, with shortcuts `--json` and
  `-q/--quiet` (one ID/path per line, ideal for scripting). `auto` picks
  `human` on a TTY and `agent` when piped/non-interactive.

## `hf auth` — authentication

| Verb | Purpose |
|------|---------|
| `login` | Store a token (interactive browser flow or `--token`) |
| `whoami` | Print the logged-in account and orgs |
| `list` (`ls`) | List all stored tokens |
| `switch` | Switch the active token |
| `logout` | Remove a stored token |
| `token` | Print the current token to stdout (avoid; leaks to logs) |

`hf auth login` options: `--token TEXT`, `--add-to-git-credential`
(save to the git credential helper), `--force` (re-login even if already
authenticated).

```bash
hf auth login --token "$HF_TOKEN"                        # non-interactive
hf auth login --token "$HF_TOKEN" --add-to-git-credential
hf auth whoami
```

Note: a token supplied through the `HF_TOKEN` env var is **not** cleared by
`hf auth logout` — unset the variable in your shell instead.

## `hf download`

`hf download REPO_ID [FILENAMES]... [OPTIONS]`

| Option | Meaning |
|--------|---------|
| `--type/--repo-type` | model \| dataset \| space |
| `--revision TEXT` | branch / tag / commit / `refs/pr/N` |
| `--include TEXT` | glob(s) to include, e.g. `"*.safetensors"` |
| `--exclude TEXT` | glob(s) to exclude, e.g. `"*.bin"` |
| `--local-dir TEXT` | download into a real folder instead of the cache |
| `--cache-dir TEXT` | override the cache location |
| `--force-download` | re-download even if cached |
| `--dry-run` | list what would be fetched without downloading |
| `--max-workers INT` | parallel download workers (default 8) |
| `--token TEXT` | credential override |
| `-q/--quiet` | print only the resolved local path |

```bash
hf download meta-llama/Llama-3.2-1B-Instruct                 # whole repo → cache
hf download bert-base-uncased config.json tokenizer.json     # named files
hf download org/model --include "*.safetensors" --exclude "*.bin"
hf download org/ds --repo-type dataset --revision v1.1 --local-dir ./data
LOCAL=$(hf download org/model --quiet)                        # capture path
```

Downloads land in the shared cache (`HF_HUB_CACHE`) by default and are shared
across projects via symlinks; pass `--local-dir` for a self-contained copy.
The **Xet** backend (`hf_xet`, installed by default) does chunk-level dedup for
fast large transfers; set `HF_HUB_DISABLE_XET=1` to fall back, or use the older
`hf_transfer` accelerator (`HF_HUB_ENABLE_HF_TRANSFER=1`).

## `hf upload` and `hf upload-large-folder`

`hf upload REPO_ID [LOCAL_PATH] [PATH_IN_REPO] [OPTIONS]` — single-commit upload
of a file or folder (both paths default to `.`).

| Option | Meaning |
|--------|---------|
| `--type/--repo-type` | model \| dataset \| space |
| `--revision TEXT` | target branch (created if missing with `--create-pr`) |
| `--private/--no-private` | create as private if the repo does not yet exist |
| `--include` / `--exclude TEXT` | globs to select / skip local files |
| `--delete TEXT` | glob of remote files to delete in the same commit (mirror) |
| `--commit-message` / `--commit-description TEXT` | commit text |
| `--create-pr` | open a PR instead of committing to the branch |
| `--every FLOAT` | schedule a background commit every N minutes |
| `--token TEXT` | credential override |

`hf upload-large-folder REPO_ID LOCAL_PATH [OPTIONS]` — **resumable**,
multi-worker upload for many-file / multi-GB folders. Options mirror `upload`
plus `--num-workers INT`, `--no-report`, `--no-bars`. It hashes, uploads, and
commits in chunks and safely resumes after an interruption.

```bash
hf upload org/model . .                              # cwd → repo root
hf upload org/model ./out /weights --create-pr       # folder → path, as PR
hf upload org/model ./local --delete "*" --exclude "logs/*"   # mirror
hf upload-large-folder org/model ./checkpoints --num-workers 16
```

## `hf repos` (alias `hf repo`)

| Verb | Purpose |
|------|---------|
| `create` | Create a repo (model/dataset/Space) |
| `delete` | Delete a repo permanently |
| `move` | Move/rename across namespaces |
| `settings` | Toggle private/gated and other settings |
| `duplicate` | Copy an existing repo |
| `list` (`ls`) | List your repos with storage info |
| `delete-files` | Delete files inside a repo (replaces deprecated `hf repo-files`) |
| `branch` | `create` / `delete` a branch |
| `tag` | `create` / `delete` / `list` a tag |
| `cp` | Copy files between local ↔ repo ↔ bucket via `hf://` |

`hf repos create` options: `--type/--repo-type`, **`--space-sdk TEXT`**
(hyphen; required when `--type space`, e.g. `gradio`, `docker`, `streamlit`,
`static`), `--private` / `--public` / `--protected`, `--exist-ok`,
`--resource-group-id` (Enterprise), `--region [us|eu]` (Team+),
`--flavor` (Space hardware), `--sleep-time`, `-s/--secrets`, `--secrets-file`.

```bash
hf repo create my-user/my-model --private
hf repo create my-user/my-space --type space --space-sdk gradio
hf repos duplicate openai/gdpval --type dataset
hf repos settings my-user/my-model --private
hf repos move old-ns/model new-ns/model
hf repos branch create my-user/my-model dev
hf repos tag create my-user/my-model v1.0
hf repos delete-files my-user/my-model "checkpoints/*"
```

## `hf cache`

| Verb | Purpose | Key options |
|------|---------|-------------|
| `list` (`ls`) | Show cached repos/revisions | `-f/--filter`, `--sort`, `--revisions`, `--limit` |
| `rm TARGETS…` | Delete repos/revisions | `-y/--yes`, `--dry-run` |
| `prune` | Drop detached (unreferenced) revisions | `-y/--yes`, `--dry-run` |
| `verify REPO_ID` | Checksum-verify a revision | `--local-dir`, `--fail-on-missing-files`, `--fail-on-extra-files` |

`cache ls --filter` accepts predicates like `size>1GB`, `type=model`,
`accessed>7d` (repeatable). `--sort` keys: `accessed`, `modified`, `name`,
`size`, each with optional `:asc`/`:desc`.

```bash
hf cache ls --sort size:desc --limit 20            # biggest first
hf cache ls -f "size>1GB" -f "accessed>30d"        # large + stale
hf cache rm model/gpt2 --dry-run                   # preview
hf cache rm model/gpt2 -y                           # reclaim space
hf cache prune -y                                   # drop detached revisions
hf cache verify gpt2 --fail-on-missing-files        # integrity check
```

## `hf models` / `hf datasets` / `hf spaces`

Shared verbs: `list` (`ls`), `info`, `card`. `list` with no arg searches the
Hub; with a `REPO_ID` it lists files in that repo (add `--tree`, `-R`,
`-h`/`--human-readable`).

`ls` search/filter options: `--search`, `--author`, `--filter` (tag, repeatable),
`--num-parameters "min:6B,max:128B"` (models), `--sort [created_at|downloads|
last_modified|likes|trending_score]`, `--limit` (default 30), `--expand`.

`info`/`ls` `--expand` returns only the listed properties (+ id). Valid keys
include `downloads`, `downloadsAllTime`, `likes`, `pipeline_tag`, `tags`,
`gated`, `safetensors`, `lastModified`, `library_name`, `siblings`, and more.

```bash
hf models ls --filter text-generation --sort downloads --limit 10
hf models ls --search llama --author meta-llama
hf models info meta-llama/Llama-3.2-1B-Instruct --expand downloads,likes,pipeline_tag
hf models ls org/model --tree -R                    # list files in a repo
hf datasets card HuggingFaceFW/fineweb
```

Datasets-only verbs: `parquet` (list parquet URLs), `sql` (DuckDB query over
those URLs), `leaderboard`. Spaces has a rich verb set beyond `ls/info/card`:
`pause`, `restart`, `logs`, `dev-mode`, `hardware`, `secrets`, `variables`,
`volumes`, `ssh`, `wait`, `settings`, `hot-reload`, `search`.
Note: `--sort downloads` is invalid for `hf spaces ls` (Spaces have no download
count) — sort by `likes` or `trending_score` instead.

## `hf jobs` — cloud compute

| Verb | Purpose |
|------|---------|
| `run IMAGE COMMAND…` | Run a container job |
| `uv run SCRIPT` | Run a PEP-723 UV script (inline deps) |
| `scheduled run SCHEDULE IMAGE COMMAND…` | Cron/preset schedule |
| `list` (`ls`, `ps`) | List jobs |
| `logs` / `inspect` / `stats` | Observe a job |
| `wait` / `cancel` / `ssh` | Block-until-done / stop / shell in |
| `labels` / `hardware` | Tag jobs / list flavors |

`hf jobs run` options: `-e/--env`, `-s/--secrets` (`--secrets HF_TOKEN`
forwards your token), `-l/--label`, `-v/--volume`
(`hf://[TYPE/]SOURCE:/MOUNT[:ro]`; models/datasets/spaces mount read-only,
buckets read-write), `--env-file`, `--secrets-file`, `--flavor`, `--timeout`
(`30m`, `2h`, `1d`), `-d/--detach`, `--expose PORT`, `--ssh`, `--namespace`.

`hf jobs scheduled run` takes a `SCHEDULE` first arg: one of `annually`,
`yearly`, `monthly`, `weekly`, `daily`, `hourly`, or a 5-field CRON string,
plus `--suspend`, `--concurrency`.

```bash
hf jobs run --flavor a10g-small python:3.12 python train.py
hf jobs run -d -s HF_TOKEN -v hf://datasets/org/ds:/data pytorch/pytorch bash run.sh
hf jobs uv run --flavor t4-medium train.py --epochs 3
hf jobs scheduled run "0 3 * * *" python:3.12 python nightly.py
hf jobs logs <job_id>;  hf jobs cancel <job_id>
```

### GPU/CPU flavor matrix (`hf jobs run --flavor`)

```
cpu-basic  cpu-upgrade  cpu-performance  cpu-xl
t4-small  t4-medium
l4x1  l4x4     l40sx1  l40sx4  l40sx8
a10g-small  a10g-large  a10g-largex2  a10g-largex4
a100-large  a100x4  a100x8
h200  h200x2  h200x4  h200x8
rtx-pro-6000  rtx-pro-6000x2  rtx-pro-6000x4  rtx-pro-6000x8
```

Run `hf jobs hardware` for the live list and pricing tier. Space `--flavor`
values (from `hf repos create`) are a smaller set (`cpu-basic`, `zero-a10g`,
`t4-medium`, `l4x4`, `a100-large`, …).

## `hf endpoints` — Inference Endpoints

| Verb | Purpose |
|------|---------|
| `deploy NAME` | Create a dedicated endpoint from a Hub repo |
| `update NAME` | Change repo/hardware/scaling of an endpoint |
| `list` (`ls`) | List endpoints in a namespace |
| `describe NAME` | Show endpoint status/config |
| `pause` / `resume` | Stop / restart billing |
| `scale-to-zero` | Idle to zero replicas |
| `delete NAME` | Delete permanently |
| `catalog` | Browse preset one-click deploys |

`hf endpoints deploy` **required** flags: `--repo`, `--framework` (e.g. `vllm`,
`pytorch`, `tgi`, `custom`), `--accelerator` (`cpu`/`gpu`), `--instance-size`
(e.g. `x1`, `x4`), `--instance-type` (provider-specific, e.g. `nvidia-a10g`,
`intel-icl`), `--region` (e.g. `us-east-1`), `--vendor` (e.g. `aws`, `azure`,
`gcp`). Optional: `--namespace`, `--task`, `--min-replica`/`--max-replica`,
`--scale-to-zero-timeout`, `--scaling-metric [pendingRequests|hardwareUsage]`,
`--scaling-threshold`, `--revision`, and custom-container flags
(`--custom-image`, `--health-route`, `--port`, `--container-command`,
`--container-args`) when `--framework custom`.

Discover valid `--instance-type` / `--instance-size` / `--vendor` combinations
via `hf endpoints catalog` rather than guessing.

```bash
hf endpoints deploy my-ep --repo openai/gpt-oss-120b --framework vllm \
  --accelerator gpu --instance-size x1 --instance-type nvidia-a10g \
  --region us-east-1 --vendor aws
hf endpoints scale-to-zero my-ep
hf endpoints update my-ep --min-replica 2 --max-replica 4
hf endpoints delete my-ep -y
```

## Environment variables

| Variable | Effect |
|----------|--------|
| `HF_TOKEN` | Credential read automatically by every command |
| `HF_HOME` | Root of config + cache (default `~/.cache/huggingface`) |
| `HF_HUB_CACHE` | Model/dataset cache dir |
| `HF_HUB_ENABLE_HF_TRANSFER=1` | Enable the legacy `hf_transfer` fast backend |
| `HF_HUB_DISABLE_XET=1` | Disable the default Xet transfer backend |
| `HF_XET_HIGH_PERFORMANCE=1` | Aggressive Xet throughput mode |
| `HF_HUB_DOWNLOAD_TIMEOUT` | Per-request download timeout, seconds (default 10) |
| `HF_HUB_ETAG_TIMEOUT` | Metadata/etag request timeout (default 10) |
| `HF_HUB_OFFLINE=1` | Never hit the network; use cache only |
| `HF_HUB_DISABLE_PROGRESS_BARS=1` | Quiet progress output (CI) |
| `HF_HUB_DISABLE_TELEMETRY=1` | Opt out of usage telemetry |

## Diagnostics

- `hf version` — CLI + `huggingface_hub` version.
- `hf env` — full environment dump (cache paths, token path, xet/transfer
  backends, timeouts) — paste this into bug reports.
- `hf <group> <verb> --help` — the ground truth for flags in your installed
  version.

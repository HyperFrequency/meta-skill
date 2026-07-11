---
name: hugging-face-cli
version: 0.1.0
description: >-
  Run Hugging Face Hub operations from the terminal with the `hf` CLI (the
  huggingface_hub command line). Use when you need to download
  models/datasets/spaces to the cache or a local dir, upload files and publish
  repos, create/manage repos/branches/tags/PRs, inspect or prune the local Hub
  cache, search and inspect models/datasets/spaces, or launch cloud GPU jobs
  and manage Inference Endpoints — including scripted/CI Hub auth and transfers.
  Not for the huggingface_hub Python API used inside code (import it directly),
  not for loading weights into memory or running inference/training loops (use
  `transformers` or a framework skill), and not for scientific-domain resource
  discovery (use `hugging-science`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "huggingface_hub CLI (Apache-2.0)"
---

# Hugging Face Hub CLI (`hf`)

## Overview

`hf` is the official command-line front end to the Hugging Face Hub, shipped
with the `huggingface_hub` Python package (it replaced the older
`huggingface-cli` entrypoint). It gives you terminal access to the same Hub
operations you would otherwise script against the `HfApi` Python client:
authentication, resumable model/dataset/space transfers, repository lifecycle
management, local cache inspection, Hub search, plus cloud compute via Jobs and
managed serving via Inference Endpoints.

Reach for it when the task is a Hub *operation* (move bytes, create a repo, tag
a release) rather than a Hub *computation* (load a model and run it). This skill
is a router: the sections below cover triggers, setup, and the command groups at
a glance; exhaustive flags and worked examples live in the linked references.

Install with `pip install -U "huggingface_hub[cli]"`. Fast large transfers use
the **Xet** backend (`hf_xet`), which ships and is enabled by default; the older
`hf_transfer` extra (`pip install huggingface_hub[hf_transfer]` plus
`HF_HUB_ENABLE_HF_TRANSFER=1`) remains as a fallback. Verify with `hf version`
and `hf env`.

## When to Use This Skill

- Download a model, dataset, or space — whole repo, specific files, or by glob
  pattern — into the shared cache or a `--local-dir`.
- Upload files/folders and publish a model or dataset; open a PR against a repo.
- Create, delete, move, or reconfigure repos; manage branches, tags, and gating.
- Inspect, verify, prune, or reclaim disk from the local Hub cache.
- Search and inspect models/datasets/spaces from the terminal (`ls` / `info`).
- Authenticate non-interactively in CI and run scripted transfers.
- Launch one-off or scheduled GPU jobs on HF infrastructure, or deploy, scale,
  and tear down Inference Endpoints.

## When NOT to Use This Skill

- You are writing Python and want programmatic control — import `huggingface_hub`
  (`snapshot_download`, `hf_hub_download`, `HfApi`, `upload_folder`) directly
  instead of shelling out to the CLI.
- You need to load weights into memory, tokenize, or run an inference/training
  loop — that is `transformers` or a framework skill; use `hf` only to fetch the
  files first.
- You are discovering curated scientific datasets/models/Spaces for a research
  domain — use `hugging-science`.
- You want heavier managed cloud training than HF Jobs offers — consider
  `modal-ml-training`.

## Setup and Authentication

Authenticate once; the token is stored under `~/.cache/huggingface/token` (or
`$HF_HOME`) and reused. In interactive shells run `hf auth login`; in CI pass a
token non-interactively.

```bash
hf auth login --token "$HF_TOKEN"                       # non-interactive
hf auth login --token "$HF_TOKEN" --add-to-git-credential  # also configure git
hf auth whoami                                          # confirm identity + orgs
```

`hf` also reads the `HF_TOKEN` environment variable automatically — most CI only
needs that variable set, no explicit `login`. Note: if you authenticated via the
`HF_TOKEN` env var, `hf auth logout` will not clear it; unset the variable in
your shell. Any command accepts `--token` to override the stored credential.
Never echo the token value; reference it only by variable name.

## Command Groups at a Glance

| Group | Purpose | Key verbs |
|-------|---------|-----------|
| `hf auth` | Manage stored tokens | `login`, `whoami`, `list`, `switch`, `logout` |
| `hf download` | Pull files from the Hub | `<repo_id> [files] [--local-dir] [--include]` |
| `hf upload` / `hf upload-large-folder` | Push files to the Hub | `<repo_id> <local> <in_repo>` |
| `hf repo` | Repo lifecycle | `create`, `delete`, `move`, `settings`, `list`, `duplicate`, `delete-files`, `branch`, `tag` |
| `hf cache` | Local cache | `ls`, `rm`, `prune`, `verify` |
| `hf models` / `hf datasets` / `hf spaces` | Browse the Hub | `ls`, `info` |
| `hf jobs` | Cloud compute | `run`, `uv run`, `ps`, `logs`, `cancel`, `scheduled …` |
| `hf endpoints` | Inference Endpoints | `deploy`, `ls`, `describe`, `update`, `pause`, `resume`, `scale-to-zero`, `delete` |
| `hf env` / `hf version` | Diagnostics | print environment / CLI version |

Every command supports `--help`. The `--repo-type` flag (`model` default,
`dataset`, or `space`) applies across download, upload, repo, and cache verbs.

### Move files

```bash
hf download meta-llama/Llama-3.2-1B-Instruct                     # whole repo → cache
hf download <repo_id> --include "*.safetensors" --exclude "*.bin"  # filter by glob
hf download <repo_id> --repo-type dataset --revision v1.1        # dataset @ revision
hf download <repo_id> --local-dir ./model                        # into a folder
hf upload <repo_id> . .                                          # cwd → repo root
hf upload <repo_id> ./out /weights --create-pr                   # folder → path, as PR
```

`hf download` prints the resolved path (use `--quiet` to capture only the path
for scripting). Prefer `hf upload-large-folder` for many-file or multi-GB
uploads — it multithreads and resumes after interruption.

### Manage repos and cache

```bash
hf repo create my-user/my-model --private
hf repo create my-user/my-space --repo-type space --space-sdk gradio  # hyphen
hf repo tag create my-user/my-model v1.0
hf cache ls --sort size:desc          # find what is eating disk
hf cache rm model/gpt2                # reclaim a repo's space
hf cache prune                        # drop detached (unreferenced) revisions
```

### Browse, run jobs, serve endpoints

```bash
hf models ls --filter "text-generation" --sort downloads --limit 10
hf models info MiniMaxAI/MiniMax-M2.1 --expand downloads,likes,pipeline_tag
hf jobs run --flavor a10g-small <image> <cmd>   # one-off GPU job
hf endpoints deploy my-ep --repo <model> --framework vllm --accelerator gpu ...  # +size/type/region/vendor (all required)
```

## Gotchas

- Creating a Space needs `--space-sdk` (hyphen; e.g. `gradio`, `docker`,
  `static`) together with `--repo-type space`. (The legacy `huggingface-cli`
  used the underscore form `--space_sdk`; the modern `hf` CLI does not.)
- `--sort downloads` is invalid for `hf spaces ls` (spaces have no download count).
- Default download timeout is 10s per request — raise `HF_HUB_DOWNLOAD_TIMEOUT`
  for slow links or large shards.
- `hf upload … --delete "*"` mirrors a local dir by deleting remote files that
  are absent locally; combine with `--exclude` so you do not wipe logs/artifacts.
- Destructive verbs (`repo delete`, `cache rm/prune`, `repo tag delete`,
  `endpoints delete`) accept `-y`/`--yes` for non-interactive scripts — and
  `--dry-run` where supported to preview first.

## References

- `references/command-reference.md` — every command group with full option
  tables, expandable properties, GPU flavor matrix, and environment variables.
- `references/workflows.md` — end-to-end recipes: publish a fine-tuned model,
  sync a Space, CI/CD publishing, quiet-mode scripting, GPU training jobs, and
  scheduled pipelines.

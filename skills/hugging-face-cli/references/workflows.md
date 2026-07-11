# `hf` CLI — End-to-End Workflows

Copy-adaptable recipes for the common Hub operations. Commands are verified
against `hf` (huggingface_hub CLI) **1.21.0**. Assume `HF_TOKEN` is exported or
`hf auth login` has run unless a step says otherwise.

## 1. Publish a fine-tuned model

```bash
# 1. Create the repo (private first; flip to public when ready)
hf repo create my-org/my-finetune --private        # verify: prints the repo URL

# 2. Push the artifacts — large-folder is resumable + multithreaded
hf upload-large-folder my-org/my-finetune ./output \
  --num-workers 16 --exclude "*.tmp" --exclude "optimizer.pt"
#    verify: hf models ls my-org/my-finetune --tree -R  lists the files

# 3. Tag a release so downstream pins a stable revision
hf repos tag create my-org/my-finetune v1.0

# 4. Publish
hf repos settings my-org/my-finetune --no-private   # or set gated in the UI
```

Use `hf upload` (single commit) only for a handful of small files; prefer
`upload-large-folder` for checkpoints/shards so an interrupted push resumes.

## 2. Download exactly what you need

```bash
# Weights only, into a self-contained folder (no shared-cache symlinks)
hf download meta-llama/Llama-3.2-1B-Instruct \
  --include "*.safetensors" "*.json" --exclude "original/*" \
  --local-dir ./llama-1b

# A dataset at a pinned revision
hf download HuggingFaceFW/fineweb --repo-type dataset --revision v1.1 \
  --local-dir ./fineweb

# Dry-run first to see the byte cost without downloading
hf download big-org/big-model --dry-run
```

Turn on faster transfers for multi-GB pulls: Xet is on by default; for the
legacy accelerator use `HF_HUB_ENABLE_HF_TRANSFER=1` after
`pip install huggingface_hub[hf_transfer]`. Raise `HF_HUB_DOWNLOAD_TIMEOUT` on
slow links.

## 3. Mirror a local directory to a repo or Space

```bash
# Push local state and delete remote files that no longer exist locally,
# but never touch server-side logs/artifacts.
hf upload my-org/my-space ./site . --repo-type space \
  --delete "*" --exclude "logs/*" --exclude ".cache/*" \
  --commit-message "Sync build $(date -u +%FT%TZ)"
```

`--delete "*"` is destructive on the remote side — always pair it with
`--exclude` guards and review with a dry `hf models ls … --tree -R` beforehand.

## 4. Non-interactive CI/CD publishing

```bash
# In CI: set HF_TOKEN as a secret; no `hf auth login` needed.
export HF_HUB_DISABLE_PROGRESS_BARS=1          # clean logs

# Publish build output as a PR so a human/gate reviews before merge
hf upload my-org/model ./dist . \
  --create-pr --commit-message "CI build ${GIT_SHA}"

# Capture the resolved path/URL for later steps (quiet = one line)
REPO_PATH=$(hf download my-org/model --quiet)
echo "fetched to $REPO_PATH"
```

`--token` on any command overrides `HF_TOKEN` if a step needs a different
identity. Reference tokens by variable name only; never echo the value.

## 5. Scripting with machine-readable output

```bash
# JSON for parsing with jq
hf models info meta-llama/Llama-3.2-1B-Instruct \
  --expand downloads,likes,pipeline_tag --json | jq '.downloads'

# Quiet mode: one id/path per line, safe for xargs
hf models ls --filter text-generation --sort downloads --limit 5 --quiet \
  | while read -r model; do echo "top model: $model"; done
```

`--format agent` is chosen automatically when output is piped; force `--json`
when you need to parse fields, or `-q/--quiet` when you only need ids/paths.

## 6. Reclaim disk from the cache

```bash
hf cache ls --sort size:desc --limit 20         # what is eating space?
hf cache ls -f "size>1GB" -f "accessed>30d"     # big + stale candidates
hf cache rm model/gpt2 --dry-run                # preview a deletion
hf cache rm model/gpt2 -y                        # delete a repo's blobs
hf cache prune -y                                # drop detached revisions
hf cache verify meta-llama/Llama-3.2-1B-Instruct # checksum an existing pull
```

`cache rm` targets whole repos (`type/name`) or specific revision hashes;
`prune` only removes revisions no longer referenced by any snapshot.

## 7. Run a GPU training job

```bash
# Detached run on an A10G, mounting a dataset read-only and forwarding the token
JOB=$(hf jobs run -d --flavor a10g-small \
  -s HF_TOKEN \
  -v hf://datasets/my-org/train-data:/data \
  --timeout 6h \
  pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime \
  bash -lc "python /data/train.py --out /tmp/out")   # verify: prints a job id

hf jobs logs "$JOB"        # stream logs
hf jobs stats "$JOB"       # GPU/mem utilisation
hf jobs cancel "$JOB"      # stop early if needed
```

Uploads back to the Hub from inside the job need the forwarded token
(`-s HF_TOKEN`). List flavors with `hf jobs hardware`.

## 8. Run a self-contained UV script job

```bash
# A PEP-723 script declares its own deps inline; no image build needed.
hf jobs uv run --flavor t4-medium https://example.com/eval.py --model my-org/model
```

Good for one-file experiments and evals where inline `# /// script` dependency
metadata beats maintaining a Docker image.

## 9. Schedule a recurring pipeline

```bash
# Nightly at 03:00 UTC; keep only one instance running at a time (default)
hf jobs scheduled run "0 3 * * *" python:3.12 \
  python -c "import subprocess; subprocess.run(['python','refresh.py'])"

hf jobs scheduled ls                 # list schedules
hf jobs scheduled suspend <id>       # pause without deleting
hf jobs scheduled resume <id>
hf jobs scheduled delete <id>
```

`SCHEDULE` accepts a CRON string or a preset (`hourly`, `daily`, `weekly`,
`monthly`, `yearly`). Add `--concurrency` to allow overlapping runs.

## 10. Deploy and manage an Inference Endpoint

```bash
# Deploy — all hardware flags are required; discover valid combos via catalog
hf endpoints catalog                              # browse presets first
hf endpoints deploy my-ep --repo my-org/model --framework vllm \
  --accelerator gpu --instance-size x1 --instance-type nvidia-a10g \
  --region us-east-1 --vendor aws \
  --min-replica 1 --max-replica 3 --scale-to-zero-timeout 15

hf endpoints describe my-ep         # poll until "running"
hf endpoints scale-to-zero my-ep    # idle to save cost
hf endpoints resume my-ep           # bring back up
hf endpoints delete my-ep -y        # tear down permanently
```

Scale-to-zero and pause both stop compute billing; `delete` is irreversible.
For a custom container use `--framework custom` with `--custom-image`,
`--port`, `--health-route`, and `--container-command`/`--container-args`.

## Failure modes to anticipate

- **10-second timeout** on slow/large downloads → raise `HF_HUB_DOWNLOAD_TIMEOUT`.
- **`--delete "*"` wiping remote artifacts** → always add `--exclude` guards.
- **Missing required deploy flags** → `hf endpoints deploy` errors unless
  `--repo/--framework/--accelerator/--instance-size/--instance-type/--region/
  --vendor` are all present.
- **Token not cleared on logout** when set via `HF_TOKEN` env → unset the var.
- **Space `ls` sort** → `--sort downloads` is rejected for Spaces; use `likes`.
- **`hf repo-files`** is deprecated → use `hf repos delete-files`.

# Authentication and Secrets

A Hugging Face token (`HF_TOKEN`) authenticates a job to the Hub. It is required
for any authenticated operation and irrelevant for purely local or
public-read-only work.

**Required for:** pushing models/datasets, creating/modifying repos, reading
private repos, mounting private volumes, any authenticated Hub API call.

**Not required for:** downloading public models/datasets, reading public repo
metadata, jobs that never touch the Hub.

## Token types

- **Read** — download models/datasets, read private repos.
- **Write** — push, create repos, modify content (needed for most jobs that produce output).
- **Fine-grained / org** — scoped access, or acting under an organization namespace.

Create and manage at https://huggingface.co/settings/tokens.

## How to provide a token to a job

Pass it via **`secrets`** (encrypted server-side), not `env` (visible in logs),
and never hardcode it.

```python
# Recommended: placeholder replaced with your logged-in token
run_uv_job(script, secrets={"HF_TOKEN": "$HF_TOKEN"})
```

- `$HF_TOKEN` resolves to the token from your current `hf auth login` session, so re-logging in updates it automatically and nothing appears in code or logs.
- Only pass a literal token string when the placeholder is unavailable (e.g. a specific org token) — and treat that as sensitive.
- `env={"HF_TOKEN": ...}` also works but is **less secure** (visible in job logs). Use it only for non-secret configuration, never for tokens.

## Using the token inside the script

Secrets arrive as environment variables. Prefer auto-detection:

```python
import os
from huggingface_hub import HfApi

assert "HF_TOKEN" in os.environ, "HF_TOKEN required for Hub operations"
api = HfApi()                       # auto-detects HF_TOKEN
# or explicitly: HfApi(token=os.environ["HF_TOKEN"])
```

`transformers` and `datasets` also auto-detect `HF_TOKEN`, so
`load_dataset("private-org/data")` and `model.push_to_hub(...)` just work when
the secret is set.

## Verifying auth

```python
from huggingface_hub import whoami
print(whoami()["name"])             # raises if not authenticated
```

In agent harnesses, `hf_whoami()` (MCP) does the same locally before submitting.

## Common token errors

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Token missing/invalid/expired | Add `secrets={"HF_TOKEN": "$HF_TOKEN"}`; re-`hf auth login`; confirm `whoami()` works |
| `403 Forbidden` | Token lacks permission (read token used for write) or no access to the repo | Use a write token; check token scope; verify repo access / org membership |
| `KeyError: 'HF_TOKEN'` | Secret not passed, wrong key, or passed via `env` | Use `secrets={"HF_TOKEN": "$HF_TOKEN"}` with the exact key `HF_TOKEN` |
| `404 / repo not found` | Private repo without access, or wrong namespace | Confirm visibility and that the namespace matches the token owner; create the repo first if needed |

## Security practices

1. Never commit or print tokens; use the `$HF_TOKEN` placeholder.
2. Always `secrets`, never `env`, for the token.
3. Use the **minimum** scope needed (read when you are not writing).
4. Rotate tokens periodically and revoke unused ones.
5. Each user uses their own token; do not share.

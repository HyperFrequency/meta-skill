# API Surface

> **Stability caveat — read first.** Adaptyv's API has run in an alpha/beta phase. The base
> URL, endpoint paths, and payload fields below reflect the shape documented by the upstream
> source and are **illustrative, not canonical**. Not every lab capability is exposed via
> API, and shapes may change without notice. Before building against these, confirm the
> current base URL, auth scheme, and request/response fields directly with the vendor
> (request access and current docs from Adaptyv). Do not treat any single hard-coded URL here
> as guaranteed to be live.

## Authentication

Bearer token in the request header. Obtain a token by requesting API access from the vendor.

```
Authorization: Bearer $ADAPTYV_API_KEY
```

Store it in an environment variable (`ADAPTYV_API_KEY`) or a git-ignored `.env`. Never commit
it or echo its value.

## Base URL

The upstream source documents an AWS Lambda function URL as the alpha endpoint:

```
https://kq5jp7qj7wdqklhsxmovkzn4l40obksv.lambda-url.eu-central-1.on.aws
```

Treat this as a stand-in. A function URL is characteristic of an early alpha and is exactly
the kind of thing that changes — resolve the real base URL with the vendor and keep it in
config, not hard-coded.

## Endpoints (representative)

### Experiments

- **`POST /experiments`** — submit sequences for testing.
  ```json
  {
    "sequences": ">protein1\nMKVLW...\n>protein2\nMATGV...",
    "experiment_type": "binding|expression|thermostability|enzyme_activity",
    "target_id": "optional_target_identifier",
    "webhook_url": "https://your-webhook.example/callback",
    "metadata": { "project": "optional", "notes": "optional" }
  }
  ```
  Returns `experiment_id`, `status: "submitted"`, `created_at`, `estimated_completion`.

- **`GET /experiments/{experiment_id}`** — status. `status ∈ {submitted, processing, completed, failed}`, plus a `progress` object (`stage ∈ {sequencing, expression, assay, analysis}`, `percentage`).

- **`GET /experiments`** — list. Query params: `status`, `limit` (default 50), `offset` (default 0). Returns `experiments[]`, `total`, `limit`, `offset`.

- **`GET /experiments/{experiment_id}/results`** — download. Returns per-sequence `measurements` + `quality_metrics`, and `download_urls` for raw data / analysis package / report. See `experiments.md` for per-assay result shapes.

### Targets

- **`GET /targets`** — search the antigen catalog. Query params: `search`, `species`, `category`. Each hit: `target_id`, `name`, `species`, `uniprot_id`, `availability` (`in_stock|custom_order`), `price_usd`.
- **`POST /targets/request`** — request a custom antigen: `target_name`, optional `uniprot_id`, `species`, `notes`.

### Organization

- **`GET /organization/credits`** — `balance`, `currency`, `usage_this_month`, `experiments_remaining`. Poll this before large submissions to avoid failures mid-batch.

## Webhooks

Register a `webhook_url` per experiment to avoid polling weeks-long jobs.

```json
{
  "event": "experiment.completed",
  "experiment_id": "exp_abc123xyz",
  "status": "completed",
  "timestamp": "2025-12-15T10:00:00Z",
  "results_url": "/experiments/exp_abc123xyz/results"
}
```

Events: `experiment.submitted`, `experiment.started`, `experiment.completed`,
`experiment.failed`. Use HTTPS only, verify webhook signatures (scheme provided at
onboarding), and respond `200 OK` to acknowledge.

## Errors

```json
{ "error": { "code": "invalid_sequence", "message": "…", "details": { "sequence_id": "protein1", "position": 45, "character": "X" } } }
```

Common codes: `authentication_failed`, `invalid_sequence`, `insufficient_credits`,
`target_not_found`, `rate_limit_exceeded`, `experiment_not_found`, `internal_error`.

## Rate limits

Documented as ~100 requests/minute per key and ~1000 experiments/day per org; batch large
submissions. On a limit you get `HTTP 429` with a `Retry-After` header — honor it with
exponential backoff (see `examples.md`).

## Working-with-the-API checklist

1. Prefer webhooks over polling for the long-running jobs.
2. Batch sequences per submission — cheaper and shares controls.
3. Validate FASTA locally before submitting.
4. Retry with exponential backoff on 429 / 5xx; do **not** retry 4xx client errors.
5. Cache downloaded results; monitor `organization/credits`.
6. Keep the base URL and key in config/env, never hard-coded — the endpoint is alpha and will move.

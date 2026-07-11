# Importing Scores from the Artificial Analysis API

[Artificial Analysis](https://artificialanalysis.ai) publishes independent
benchmark scores for hosted frontier models. Their API lets you pull those
numbers and attach them to a Hugging Face model card (typically a mirror or
derivative repo) with proper source attribution.

## Auth

Set `AA_API_KEY` in the environment (or a `.env` loaded via `python-dotenv`).
Requests authenticate with an `x-api-key` header — never put the key in a query
string or commit it.

## Endpoint and response shape

```python
import os, requests

resp = requests.get(
    "https://artificialanalysis.ai/api/v2/data/llms/models",
    headers={"x-api-key": os.environ["AA_API_KEY"]},
    timeout=30,
)
resp.raise_for_status()
models = resp.json().get("data", [])
```

Each element of `data` describes one model. The fields this workflow relies on:

- `slug` — the model identifier (e.g. `claude-sonnet-4`).
- `model_creator.slug` — the creator identifier (e.g. `anthropic`).
- `name` — display name.
- `evaluations` — an object mapping benchmark keys to numeric scores.

Select your model by matching both slugs:

```python
def find_model(models, creator_slug, model_slug):
    for m in models:
        if m.get("model_creator", {}).get("slug") == creator_slug \
           and m.get("slug") == model_slug:
            return m
    return None
```

If no match, print the creator/model slugs you searched for and stop — the slugs
must match the API's exact values, which may differ from the HF repo name.

> The exact set of keys inside `evaluations` and any nested structure can change
> between API revisions. Inspect one response before mapping, and treat any key
> whose value is `None` as absent.

## Mapping to model-index

Turn the `evaluations` object into metrics, then wrap in one result entry with
Artificial Analysis as the source:

```python
def aa_to_model_index(model_data):
    metrics = [
        {"name": key.replace("_", " ").title(), "type": key, "value": value}
        for key, value in model_data.get("evaluations", {}).items()
        if value is not None
    ]
    return [{
        "task": {"type": "evaluation"},
        "dataset": {"name": "Artificial Analysis Benchmarks",
                    "type": "artificial_analysis"},
        "metrics": metrics,
        "source": {"name": "Artificial Analysis API",
                   "url": "https://artificialanalysis.ai"},
    }]
```

Hand the returned list to the write path in
`references/model-index-format.md` (merge into the existing `model-index`, then
`push_to_hub(create_pr=...)`).

## Attribution and etiquette

- Keep `source.name` / `source.url` pointing at Artificial Analysis — these are
  third-party measurements, not your own runs, and the card should say so.
- Before opening a PR on a repo you do not own, list existing open PRs first
  (see the Safety section of `SKILL.md`) so you do not duplicate someone else's
  import.

## Failure modes

- **`AA_API_KEY not set`** — export it or add it to `.env`.
- **HTTP 401/403** — key invalid or lacking access to that dataset.
- **Model not found** — creator-slug or model-slug does not match the API's
  values; fetch the list and grep for the right slug.
- **Transient 5xx / timeouts** — retry with backoff; the endpoint occasionally
  rate-limits.

# model-index Format & huggingface_hub Write APIs

The `model-index` block lives in the YAML frontmatter of a model card's
`README.md`. It follows the Papers-with-Code model-index specification, which the
Hugging Face Hub reads to render the model page's evaluation widget.

## Schema

```yaml
model-index:
  - name: My-Model-7B          # REQUIRED, one entry per model, plain text
    results:                   # REQUIRED, a list
      - task:                  # REQUIRED
          type: text-generation      # e.g. text-generation, summarization,
                                     # question-answering, translation
          name: Text Generation      # optional human label
        dataset:               # REQUIRED
          name: MMLU
          type: mmlu                 # slug/identifier for the dataset
          config: en                 # optional
          split: test                # optional
        metrics:               # REQUIRED, a list
          - type: mmlu               # REQUIRED, metric slug
            value: 68.4              # REQUIRED, number
            name: MMLU (5-shot)      # optional display name
            verified: false          # optional; true only for Hub-verified runs
        source:                # optional but recommended
          name: lighteval
          url: https://huggingface.co/My-Model-7B
```

Rules that matter:

- **`name` (model)** must be plain text — no markdown bold/links. Use the exact
  model name.
- **`source.url`** is the only place a URL belongs; do not put URLs in `name`
  fields.
- Each `results` entry pairs one `task` + one `dataset` with one or more
  `metrics`. Group metrics that share a dataset under a single result; use
  separate result entries for different datasets.
- Only publish the **main model's** scores for its own repo. Do not add a
  comparison table's other models or training checkpoints.

## Benchmark → type mapping

Use lowercase, stable slugs for `metric.type` and `dataset.type`. A practical
baseline:

| Display   | type            | Dataset full name                     |
|-----------|-----------------|---------------------------------------|
| MMLU      | `mmlu`          | Massive Multitask Language Understanding |
| HumanEval | `humaneval`     | Code Generation (HumanEval)           |
| GSM8K     | `gsm8k`         | Grade School Math                     |
| HellaSwag | `hellaswag`     | HellaSwag Common Sense                |
| ARC-C     | `arc_challenge` | ARC Challenge                         |
| ARC-E     | `arc_easy`      | ARC Easy                              |
| Winogrande| `winogrande`    | Winogrande                            |
| TruthfulQA| `truthfulqa`    | TruthfulQA                            |
| GPQA      | `gpqa`          | Graduate-Level Google-Proof Q&A       |
| DROP      | `drop`          | Discrete Reasoning Over Paragraphs    |
| BBH       | `bbh`           | Big Bench Hard                        |
| MATH      | `math`          | MATH Dataset                          |

For anything not listed, derive a slug from the display name:
`name.lower().replace(" ", "_")`.

## Writing with `huggingface_hub`

### Direct dict approach (most control)

`ModelCard.data` is a dict-like `ModelCardData` you can read and mutate. This is
the path used for README extraction and AA import because it round-trips the
whole card safely.

```python
import os
from huggingface_hub import ModelCard

repo_id = "user/model"
token = os.environ["HF_TOKEN"]          # write scope

card = ModelCard.load(repo_id, token=token)
model_name = repo_id.split("/")[-1]

new_index = [{"name": model_name, "results": results}]  # results = list built per schema

# --- MERGE, do not overwrite ---
existing = card.data.get("model-index")
if isinstance(existing, list) and existing:
    if "name" in existing[0]:
        new_index[0]["name"] = existing[0]["name"]      # preserve declared name
    new_index[0]["results"].extend(existing[0].get("results", []))

card.data["model-index"] = new_index

card.push_to_hub(
    repo_id,
    token=token,
    commit_message=f"Add evaluation results to {model_name}",
    create_pr=True,      # False to push directly to main
)
```

`push_to_hub(..., create_pr=True)` returns/opens a pull request instead of
committing to `main` — use it whenever you do not own the repo.

### Higher-level `EvalResult` helper

`huggingface_hub` also exposes `EvalResult` (and `metadata_eval_result`) for
building one metric at a time without hand-writing the nested dict:

```python
from huggingface_hub import EvalResult

EvalResult(
    task_type="text-generation",
    dataset_type="mmlu",
    dataset_name="MMLU",
    metric_type="mmlu",
    metric_value=68.4,
    metric_name="MMLU (5-shot)",
)
```

A list of `EvalResult` can be attached via `ModelCardData(eval_results=[...])`.
Prefer this when you are generating a card from scratch; prefer the dict-merge
path when editing an existing card you must not disturb.

## Validation before pushing

Sanity-check the structure so a malformed card is never committed:

- `model-index` is a list.
- Each entry has `name` and `results`.
- Each result has `task`, `dataset`, and `metrics`.
- Each metric has `type` and a numeric `value`.

Reject and report rather than pushing partial/invalid metadata. After a push,
reload the card and print the `model-index` back to confirm the merge landed as
intended.

## Common failures

- **"Token does not have write access"** — `HF_TOKEN` lacks write scope for the
  repo; mint a write token or open a PR against a repo you cannot push to.
- **Widget not rendering** — usually a schema slip (URL in a `name`, missing
  `metrics`, non-numeric `value`). Re-validate.
- **Lost prior results** — you overwrote instead of merged; always read the
  existing `model-index` first.

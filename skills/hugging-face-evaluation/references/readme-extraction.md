# Extracting Eval Tables from a README

Many model cards already publish scores as a markdown table in the README body
but never expose them as machine-readable `model-index` metadata. This reference
covers turning such a table into model-index YAML safely — the hard part is
picking the **right** model's numbers and nothing else.

## Workflow

1. **Load the README** via `ModelCard.load(repo_id, token).content`.
2. **Parse all tables** with a GFM-aware parser (see below) — do not regex raw
   text; you will trip over code fences and example blocks.
3. **Inspect** the tables: print each table's index, detected format, columns
   (with their indices), and the first-column sample rows. Multi-table READMEs
   require you to pick one by index.
4. **Detect format** — benchmarks-as-rows vs. transposed (models-as-rows).
5. **Match the target model** by exact normalized-token comparison.
6. **Preview** the generated YAML and compare it against the source table
   cell-by-cell.
7. **Apply** only after the preview matches — push or open a PR
   (see `references/model-index-format.md`).

## Parsing tables with markdown-it-py

```python
from markdown_it import MarkdownIt

md = MarkdownIt("gfm-like", {"linkify": False})   # linkify off avoids an optional dep
tokens = md.parse(readme_content)
```

Walk the token stream: `table_open` … `table_close`, tracking `thead_open` /
`thead_close` to separate header cells from body rows, and collect each
`inline` token's `.content` per `tr`. This yields, per table,
`{"headers": [...], "rows": [[...], ...]}`. A GFM parser correctly ignores
tables that appear inside fenced code blocks, which naive regex extraction does
not.

## Format detection

- **rows** (most common): first column header is empty or one of
  `benchmark / task / dataset / metric / eval`; benchmark names run down the
  first column, scores across the columns. Exactly one score column belongs to
  the target model.
- **transposed**: first column header is model-like (`model / system / llm /
  name`), each row is a different model, and the header row is benchmark names.
- **columns**: benchmarks are the headers and a single data row holds the
  values.

Heuristic: a table is transposed when it has >=3 columns, the first-column
header looks model-like OR >=2 other headers look benchmark-like, AND more than
half the body cells (excluding the first column) parse as numbers.

## Model-name matching (the part that prevents wrong numbers)

Normalize both the target model name (from the repo id, or a user override) and
each candidate column/row header, then require an **exact token-set match**:

```python
import re

def normalize(name):
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", name)  # strip md links
    cleaned = re.sub(r"\*\*([^\*]+)\*\*", r"\1", cleaned)      # strip bold
    normalized = cleaned.strip().lower().replace("-", " ").replace("_", " ")
    return set(normalized.split())

# "OLMo-3-32B" -> {"olmo", "3", "32b"}  matches  "**Olmo 3 32B**"  or  "[Olmo-3-32B](...)"
```

- **rows format**: find the column whose header tokens equal the model tokens;
  read scores from that column only.
- **transposed format**: find the row whose first cell tokens equal the model
  tokens; read that row only.

If there is **no exact match, fail** — print the available model names and stop.
Do not fall back to a fuzzy/partial match: a partial match will happily grab a
sibling model (`...-Instruct`, `...-Base`) or an intermediate checkpoint. Let
the user disambiguate with an explicit override (the exact header text) or a
column index from the inspect step.

## Cell parsing

Strip `%` and thousands separators before `float()`. Skip cells that do not
parse (dashes, "N/A", footnote markers). For a rows-format table where you did
not pin a column, take the first numeric value per row — but pinning the column
is far safer.

## Preview then apply

Emit the assembled `model-index` as YAML to stdout **by default**. Only after
the human (or you) has checked it against the README table should you push or
open a PR. Wrong extraction silently publishes wrong benchmark numbers on
someone's model card, so treat the preview as mandatory, not optional.

Build the result entry with `source.name = "Model README"` and
`source.url = https://huggingface.co/{repo_id}`, then hand off to the write path
in `references/model-index-format.md`.

## Edge cases

- **Multiple eval tables** — abort auto-selection; require an explicit table
  index.
- **Merged/spanning header cells** — GFM does not support them; the row will be
  ragged. Inspect and pin the column by index.
- **Scores with confidence intervals** (`68.4 ±0.3`) — strip the interval before
  parsing, or the `float()` fails.
- **Transposed table, no model column given** — you cannot know which row is the
  subject; require the override.

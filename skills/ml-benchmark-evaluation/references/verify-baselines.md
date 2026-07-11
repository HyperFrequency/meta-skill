# Verify Published Baselines from the Primary Source

Never trust a baseline number that arrived second-hand — copied into a task
description, a blog post, a leaderboard row, or a survey table. Secondary
sources routinely quote the wrong cell of a table, the wrong metric, or a number
from a different configuration than the one they attribute it to. The number you
claim to beat must come from the original paper (or the benchmark's official
code), read directly.

## The discrepancies you will actually hit

- **Wrong table / wrong metric.** The quoted figure comes from a different table
  or a different metric than stated (e.g. a task spec says the baseline nRMSE is
  `5.9e-3` but the paper's own table says `9.7e-3`). You would "beat" a baseline
  that was never real.
- **Different configuration.** The number is from a larger/smaller model, a
  different resolution, more training data, or a different backbone than the one
  named.
- **Metric-name collision.** RMSE vs nRMSE vs MSE vs relative-L2 get conflated;
  they differ by orders of magnitude. (Getting the *formula* right is
  `metrics-and-formulas.md`; getting the *value* right is here.)
- **Different split.** The baseline used a different train/test partition, so the
  comparison is not on the same data even if the metric matches.

## Procedure

1. **Get the primary artifact.** Download the original paper (arXiv PDF or the
   published version) and, when it exists, the benchmark's official repository.

   ```bash
   wget -O paper.pdf "https://arxiv.org/pdf/XXXX.XXXXX"
   ```

2. **Convert to searchable text.** Use a PDF-to-text tool you trust. `pdftotext`
   from poppler is reliable and ubiquitous:

   ```bash
   pdftotext -layout paper.pdf paper.txt
   ```

   For scanned or table-heavy PDFs where layout matters, use the `pdf` or
   `markitdown` sibling skills, which handle structured extraction better than a
   flat text dump.

3. **Locate the exact number.** Search for the metric token and read the
   surrounding table caption and column header — confirm the metric, the split,
   the model configuration, and the units all match what you intend to compare
   against.

   ```bash
   grep -niE "nrmse|rmse|accuracy|f1|map" paper.txt
   ```

4. **Prefer the code's number over the paper's prose** when they disagree. A
   benchmark's official results file or `metrics.py` output is more
   authoritative than a rounded figure in running text.

5. **Record provenance.** In your results artifact, store the baseline value
   *with its source*: paper title, arXiv id, table/figure number, and the exact
   configuration string. A baseline without provenance is not verified.

## Cross-check against a factual-claim workflow

When a baseline is contested, or you need to confirm a number that is asserted
but not obviously located in any table, escalate to the `claim-verify` sibling
skill — it adversarially checks a claim against primary sources and is the right
tool when "the paper says X" is itself in question.

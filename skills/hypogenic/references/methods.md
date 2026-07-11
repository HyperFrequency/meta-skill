# Hypogenic Methods

The framework offers three families of hypothesis generation, all driven by LLMs.

## 1. HypoGeniC — Data-Driven Generation

Generate hypotheses solely from observational data through iterative in-context refinement.

**Process:**
1. Initialize with a small data subset to generate candidate hypotheses.
2. Run inference and score hypotheses against training examples.
3. Replace poorly-performing hypotheses with new ones derived from challenging (mis-predicted) examples.
4. Repeat for the configured number of update epochs.

**Best for:** Exploratory research without existing literature, pattern discovery in novel datasets.

## 2. HypoRefine — Literature + Data Integration

Synergistically combine existing literature with empirical data in an agentic loop.

**Process:**
1. Preprocess relevant research papers (typically ~10) via GROBID + s2orc-doc2json.
2. Generate theory-grounded hypotheses from the literature.
3. Generate data-driven hypotheses from observational patterns.
4. Iteratively refine both hypothesis banks.

`union_generation.py` produces **three** hypothesis banks: HypoRefine (integrated), Literature-only, and Literature∪HypoRefine.

**Best for:** Research with established theoretical foundations; validating or extending existing theories.

## 3. Union Methods

Mechanistically combine literature-only hypotheses with framework outputs.

- **Literature∪HypoGeniC** — literature hypotheses combined with data-driven generation.
- **Literature∪HypoRefine** — literature hypotheses combined with the integrated approach.

**Best for:** Comprehensive coverage, eliminating redundancy while keeping diverse perspectives.

## Reported Results (from the source papers)

These figures are reported by the upstream authors, not independently re-verified here:
- 8.97% improvement over few-shot baselines; 15.75% over literature-only approaches.
- 14.19% accuracy improvement in AI-content detection; 7.44% in deception detection.
- 80–84% of hypothesis pairs offering distinct, non-redundant insights.

## Workflow Examples

### Data-driven (HypoGeniC) — e.g. AI-generated content detection
1. Prepare a dataset of text samples and labels (human vs. AI-generated).
2. Write `config.yaml` with `observations`, `batched_generation`, and `inference` templates.
3. Run `hypogenic_generation` (or adapt `examples/generation.py`).
4. Run `hypogenic_inference` (or adapt `examples/inference.py`) on the test set.
5. Inspect surviving hypotheses for patterns (formality, grammar, tone).

### Literature-informed (HypoRefine) — e.g. deception detection in hotel reviews
1. Collect ~10 papers on linguistic deception cues; preprocess via GROBID.
2. Prepare genuine vs. fraudulent review data.
3. Run `examples/union_generation.py`.
4. Compare literature-based vs. data-driven hypothesis performance.

### Comprehensive coverage (Union) — e.g. mental-stress detection
1. Generate literature hypotheses from mental-health papers.
2. Generate data-driven hypotheses from social-media posts.
3. Run the Union path to combine and deduplicate, capturing both theoretical constructs and data patterns.

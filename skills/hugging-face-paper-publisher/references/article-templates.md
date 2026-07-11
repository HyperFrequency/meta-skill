# Research Article Templates

Section skeletons for drafting a paper that will accompany an HF release. These are structural starting points — for real prose, hand off to the `scientific-writing` / `scientific-writer` skills, and for the polished web format use the community `tfrere/research-article-template` Space (below).

All templates share a YAML frontmatter header:

```yaml
---
title: Your Paper Title
authors: Jane Doe, John Smith
affiliations: University X, Lab Y
date: 2025-01-15
arxiv: 2301.12345
tags: [machine-learning, nlp, fine-tuning]
---
```

## `standard` — traditional academic structure

```markdown
# Abstract
# 1. Introduction
# 2. Related Work
# 3. Methodology
# 4. Experiments
# 5. Results
# 6. Discussion
# 7. Conclusion
# References
```

## `modern` — Distill-like, web-friendly

Same backbone as `standard`, tuned for reading on the web:

- dynamic table of contents,
- responsive layout,
- code syntax highlighting,
- inline interactive figures/charts,
- LaTeX math rendering,
- author-affiliation linking.

Keep sections short and lead each with a takeaway; favor figures over dense tables.

## `arxiv` — arXiv/journal style

```markdown
# Abstract
# 1. Introduction
# 2. Background
# 3. Method
# 4. Experimental Setup
# 5. Results and Analysis
# 6. Related Work
# 7. Limitations
# 8. Conclusion
# Acknowledgments
# References
# Appendix
```

Include a **Limitations** section (many venues now require it) and an **Appendix** for extended derivations, hyperparameters, and ablations.

## `ml-report` — experiment report

```markdown
# Summary
# 1. Objective
# 2. Data
# 3. Model / Approach
# 4. Training Setup   (hyperparameters, compute, seeds)
# 5. Metrics & Results
# 6. Ablations
# 7. Error Analysis
# 8. Reproducibility  (code, weights, dataset links)
# 9. Next Steps
```

Best for a model-release writeup: cross-link the HF model, dataset, and Space repos directly, and record exact hyperparameters and seeds under Training Setup for reproducibility.

## LaTeX math

Inline `$...$` and display `$$...$$` render on HF cards and in the `modern` web format. Example:

```markdown
The loss is $\mathcal{L} = -\sum_i y_i \log \hat{y}_i$.

$$\hat{y} = \mathrm{softmax}(W h + b)$$
```

## Table of contents

For long documents, generate a TOC from the H1/H2 headings (many static renderers do this automatically from `#`/`##`). In the `modern` web template the TOC is dynamic and sticky.

## The `tfrere` research-article template

For a production-quality, interactive web article, use the community Space:
`https://huggingface.co/spaces/tfrere/research-article-template`.

Recommended split of labor:

- Write and design the article with the `tfrere` template (rich web layout, figures, math).
- Use this skill to **index** the resulting arXiv paper and **link** it to your HF model/dataset/Space (see `linking-and-metadata.md`).
- Use `scientific-figure` for publication figures and `citation-management` for the bibliography.

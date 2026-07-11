# Paper2Web: Interactive Academic Homepage

Converts a paper into a **layout-aware, explorable homepage** — not a flat HTML export of the PDF. It analyzes structure and produces a responsive, multi-section site through an iterative refine loop.

## Pipeline stages

1. Content extraction and structuring from LaTeX/PDF.
2. Layout generation with visual hierarchy adapted to paper type (article, review, preprint).
3. Interactive-element integration (expandable sections, figure/table viewers, embedded citations, nav menu).
4. Aesthetic refinement.
5. Automated quality assessment and validation.

## Typical invocation

```bash
python pipeline_all.py \
  --input-dir <paper_dir> \
  --output-dir <out_dir> \
  --model-choice N
```

Optional logo discovery uses a web-search API to find institution logos from author affiliations — it needs `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` configured (see `setup-and-usage.md`). The upstream flag for this (documented as `--enable-logo-search`) is **version-dependent — confirm with `python pipeline_all.py --help`.**

## Output tree (approximate)

```
<out_dir>/<paper_name>/website/
├── index.html
├── styles.css
├── script.js
├── assets/{figures,logos}/
└── data/            # structured data (optional)
```

## Sections generated

Standard: abstract, key findings/contributions, methodology overview, results & visualizations, discussion, references, author info. Extra sections are added when the paper warrants them: code repo links, dataset links, supplementary materials, related work.

## Features

- **Interactive figures**: zoom/pan, captions, multi-panel navigation.
- **Citations**: hoverable reference list, DOI/external links.
- **Design**: content-derived color scheme, readability-tuned typography, optional dark mode, mobile-responsive.

## Built-in quality signals

- *Aesthetic*: layout balance, color harmony, typography consistency, hierarchy.
- *Informativeness*: content completeness, finding clarity, method adequacy, results presentation.
- *Technical*: load time, mobile responsiveness, browser compatibility, accessibility.

These are heuristic — still review manually.

## Limitations

- Complex equations may need manual review.
- Multi-column PDF layouts hurt extraction — prefer LaTeX.
- Very long papers (>50 pp.) take longer; some specialized figure types need manual adjustment.

## Deploying the site

Static output deploys anywhere: GitHub Pages (free, custom domain), Netlify/Vercel (CI/CD), university web space, or your own server. Add links to the paper DOI, code repo, and data availability before publishing.

## Combine with

`scientific-schematics` for a concept diagram in a section; the Paper2Video/Paper2Poster components for a matching visual identity.

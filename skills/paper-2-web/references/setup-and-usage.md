# Setup and Usage

Installation, configuration, the full (version-dependent) command surface, resource/cost estimates, batch processing, and worked examples for the Paper2All pipeline (`github.com/YuhangChen1/Paper2All`).

> **License note**: Paper2All publishes no explicit LICENSE upstream as of 2026-07. Treat the code as all-rights-reserved; confirm terms before redistributing the tool or its generated assets.

## Requirements

**Software**: Python ≥3.11, Conda (dependency isolation), LibreOffice (document conversion, e.g. PDF↔PPTX), Poppler utilities (PDF processing).

**Hardware**: multi-core CPU; RAM 16 GB min, 32 GB for large papers; a large NVIDIA GPU (upstream cites an A6000-class 48 GB card) **only** for talking-head video via Hallo2 — standard outputs run CPU-only.

## Install

```bash
git clone https://github.com/YuhangChen1/Paper2All.git
cd Paper2All
conda create -n paper2all python=3.11
conda activate paper2all
pip install -r requirements.txt
```

System dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install libreoffice poppler-utils
# macOS
brew install libreoffice poppler
# Windows: install LibreOffice + Poppler-for-Windows manually, add to PATH
```

Verify: `python pipeline_all.py --help` should print the option menu. **The `--help` output is authoritative — trust it over any flag table in these docs.**

## API configuration

Create a `.env` in the project root. Do not commit it. Provide one LLM backend:

```
OPENAI_API_KEY=...
# or, alternatively
OPENROUTER_API_KEY=...
```

Optional, for automatic institution-logo discovery (Paper2Web/Paper2Poster):

```
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...
```

Supported models include the OpenAI GPT line and, via OpenRouter, Claude and others.

## Command surface (verify against `--help`)

**Corroborated across sources:**

| Entry point | Flags |
| --- | --- |
| `pipeline_all.py` | `--input-dir`, `--output-dir`, `--pdf-path`, `--model-choice`, `--poster-width-inches`, `--poster-height-inches` |
| `pipeline_light.py` (video) | `--model_name_t`, `--model_name_v`, `--result_dir`, `--paper_latex_root` |

**`--model-choice` is ambiguous across versions.** The upstream repo documents it as *component selection* (e.g. website / poster / PR materials); other docs describe it as a *model preset*. **Do not assume its meaning — read `--help`.**

**Documented but unverified / version-dependent** (present in some docs; confirm before use, do not treat as guaranteed): `--generate-website`, `--generate-poster`, `--generate-video`, `--enable-talking-head`, `--enable-logo-search`, `--enable-qr-codes`, `--video-duration`, `--slides-per-minute`, `--voice`, `--video-resolution`, `--video-fps`, `--poster-orientation`, `--poster-dpi`, `--poster-template`, `--color-scheme`, `--font-family`, `--presentation-style`.

## Input organization

Single paper — one directory:

```
input/<paper_name>/
├── main.tex   # or paper.pdf
├── figures/
├── tables/
└── bibliography.bib
```

Batch — one subdirectory per paper under a shared root; point `--input-dir` at the root.

**LaTeX beats PDF**: cleaner structure/figure/equation extraction. If PDF-only, use a high-quality PDF with selectable text (not scanned) and embedded, high-res figures. Ensure LaTeX compiles (`pdflatex main.tex`) first — most parse failures trace to a broken build or a missing referenced file.

## Output structure

```
output/<paper_name>/
├── website/   # index.html, styles.css, assets/
├── poster/    # poster_final.pdf/.png, poster_source/
└── video/     # final_video.mp4, slides/, audio/, subtitles/
```

See the per-component references for full trees.

## Resource, time, and cost estimates

Order-of-magnitude only; scale with paper length, figure count, model, and hardware.

| Component | Time/paper | Notes |
| --- | --- | --- |
| Website | ~15–30 min | fastest, most versatile |
| Poster | ~10–20 min | print-deadline friendly |
| Video (no talking-head) | ~20–60 min | slowest of the three |
| Video (talking-head) | ~60–120 min | GPU required |

Storage: ~1–5 GB/paper. API cost is model-dependent and roughly proportional to paper length — estimate on a single paper before batching, and prefer a cheaper model for drafts.

## Batch processing

```bash
for paper in paper1 paper2 paper3; do
  python pipeline_all.py \
    --input-dir input/$paper \
    --output-dir output/$paper \
    --model-choice N &
done
wait
```

Watch total cost and rate limits; process large batches overnight; review each result — automated QA does not catch content drift.

## Worked patterns

**Full package for a major submission** (website + poster + video): run `pipeline_all.py` on the LaTeX dir with the component flags your `--help` confirms, then `pipeline_light.py` for the video. Generate the website first if you are on a deadline.

**Website for a preprint** (PDF input): `pipeline_all.py --input-dir <pdf_dir> --output-dir <out>` with the website component; add DOI, code, and data-availability links before deploying.

**Short video abstract**: `pipeline_light.py` with a modest target duration and a faster/cheaper model; extract a 30-second clip and add captions for social media.

**Poster at a specific size**: `pipeline_all.py ... --poster-width-inches 48 --poster-height-inches 36`, then print a Letter-size preview before the full run.

## Troubleshooting

- **LaTeX parse errors** → confirm `pdflatex main.tex` succeeds; check custom packages and missing files.
- **Poor figures** → prefer vector (PDF/SVG/EPS) or ≥300 DPI rasters; confirm they render in the compiled PDF.
- **Video render failure** → free disk space (5 GB+); confirm LibreOffice + Poppler installed; read the run log.
- **Poster layout issues** → keep dimensions in a sane range (24"–72"); trim very long papers; size figures for the poster.
- **API errors** → check keys in `.env` (no stray quotes/spaces), credit balance, and rate limits.
- **LibreOffice/Poppler not found** → verify `libreoffice --version` and `pdftoppm -v`; add to PATH.
- **GPU/CUDA errors (talking-head)** → update NVIDIA drivers, confirm CUDA toolkit, check `nvidia-smi` memory.

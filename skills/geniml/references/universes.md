# Consensus-Peak Universes

A "universe" is a standardized reference set of consensus peaks built from many BED
files — the regions where your datasets overlap significantly. It is the shared
vocabulary every embedding model tokenizes against, so universe quality caps the
quality of Region2Vec / BEDspace / scEmbed. Build one whenever you need a
tokenization reference or want to standardize regions across experiments.

## Workflow

### 1. Combine BED files

```bash
cat /path/to/bed/*.bed > combined.bed
```

### 2. Generate coverage tracks (uniwig)

```bash
uniwig -m 25 combined.bed chrom.sizes coverage/
```

- `-m 25`: smoothing window (25 bp is typical for chromatin accessibility; it
  reduces noise and yields more robust boundaries).
- `chrom.sizes`: chromosome-size file for your assembly.
- `coverage/`: output bigWig directory.

### 3. Build the universe (pick a method)

## Methods, in order of rigor and cost

### CC — Coverage Cutoff (start here)

Fixed coverage threshold. Simple and interpretable.

```bash
geniml universe build cc \
  --coverage-folder coverage/ --output-file universe_cc.bed \
  --cutoff 5 --merge 100 --filter-size 50
```

- `--cutoff`: coverage threshold — `1` = union, `n_files` = intersection.
- `--merge`: distance (bp) to merge adjacent peaks.
- `--filter-size`: minimum peak size (bp).

### CCF — Coverage Cutoff Flexible

Adds confidence intervals around the cutoff for flexible boundaries and region
cores. Use when boundaries are noisy.

```bash
geniml universe build ccf \
  --coverage-folder coverage/ --output-file universe_ccf.bed \
  --cutoff 5 --confidence 0.95 --merge 100 --filter-size 50
```

### ML — Maximum Likelihood

Probabilistic model of region start/end positions. Use for publication-grade
statistical rigor.

```bash
geniml universe build ml \
  --coverage-folder coverage/ --output-file universe_ml.bed \
  --merge 100 --filter-size 50 --model-type gaussian
```

- `--model-type`: `gaussian` or `poisson`.

### HMM — Hidden Markov Model

Regions as hidden states, coverage as emissions. Use for complex chromatin-state
patterns. Highest compute cost.

```bash
geniml universe build hmm \
  --coverage-folder coverage/ --output-file universe_hmm.bed \
  --states 3 --merge 100 --filter-size 50
```

- `--states`: number of hidden states (typically 2–5).

## Python API

```python
from geniml.universe import build_universe

build_universe(
    coverage_folder="coverage/", method="cc",
    cutoff=5, merge_distance=100, min_size=50,
    output_file="universe.bed",
)
```

## Method comparison

| Method | Complexity | Compute cost | Best for |
|--------|-----------|--------------|----------|
| CC  | Low    | Low       | Quick reference sets |
| CCF | Medium | Medium    | Uncertain boundaries |
| ML  | High   | High      | Statistical rigor |
| HMM | High   | Very high | Complex state patterns |

## Parameter selection

- **Cutoff**: `1` = permissive union; `n_files` = stringent intersection;
  `0.5 * n_files` = moderate consensus (a common default).
- **Merge distance**: ATAC-seq 100–200 bp; narrow ChIP-seq 50–100 bp; broad ChIP-seq
  500–1000 bp.
- **Filter size**: ≥30 bp to avoid artifacts; 50–100 bp typical; larger for broad
  histone marks.

## Quality control

```python
from geniml.evaluation import assess_universe

m = assess_universe(universe_file="universe.bed",
                    coverage_folder="coverage/", bed_files="bed_files/")
print(m["n_regions"], m["mean_size"], m["coverage"])
```

- **Region count**: captures major features without over-fragmenting.
- **Size distribution**: matches expected biology (~500 bp for ATAC-seq).
- **Input coverage**: fraction of original peaks represented — aim >80%.

## Troubleshooting

- **Too few regions** → lower cutoff or filter size.
- **Too many regions** → raise cutoff, increase merge distance or filter size.
- **Noisy boundaries** → switch from CC to CCF or ML.
- **Runs too long** → prototype with CC, refine with ML/HMM only if needed.

## Output

BED with the three required columns (`chr start end`); some methods append
confidence scores or state annotations.

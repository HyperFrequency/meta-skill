# Basic GRN Inference

How to prepare inputs, run inference, and read the output of `grnboost2` /
`genie3`. See `algorithms.md` for algorithm choice and `distributed.md` for
scaling.

## Input Data

Arboreto accepts the expression matrix in one of two forms. In both, rows are
**observations** (cells, samples, conditions) and columns are **genes**.

### Pandas DataFrame (preferred)

Gene names live in the column headers, so arboreto reads them automatically.

```python
import pandas as pd

# genes as columns, numeric expression values in the cells
expression_matrix = pd.read_csv('expression_data.tsv', sep='\t')
```

### NumPy array + explicit gene names

A bare array has no column labels, so you must pass a `gene_names` list whose
order matches the columns.

```python
import numpy as np

expression_matrix = np.genfromtxt('expression_data.tsv', delimiter='\t', skip_header=1)
with open('expression_data.tsv') as f:
    gene_names = [g.strip() for g in f.readline().split('\t')]

assert expression_matrix.shape[1] == len(gene_names)   # columns must equal names
```

## Restricting Regulators (Transcription Factors)

By default (`tf_names='all'`) every gene is a candidate regulator. Passing a TF
list restricts the regulators, which both sharpens biological interpretation and
cuts compute.

```python
from arboreto.utils import load_tf_names

tf_names = load_tf_names('transcription_factors.txt')   # one TF name per line
# or inline
tf_names = ['GATA3', 'FOXP3', 'TBX21']
```

TF names must match gene identifiers in the matrix exactly (same symbol vs
Ensembl-ID convention, same case) or those regulators silently contribute no
edges.

## Full Inference Workflow

```python
import pandas as pd
from arboreto.utils import load_tf_names
from arboreto.algo import grnboost2

if __name__ == '__main__':                              # required for Dask
    expression_matrix = pd.read_csv('expression_data.tsv', sep='\t')
    tf_names = load_tf_names('tf_list.txt')             # optional

    network = grnboost2(
        expression_data=expression_matrix,
        tf_names=tf_names,
        seed=777,
    )

    network.to_csv('network_output.tsv', sep='\t', index=False, header=False)
```

For the NumPy path, add `gene_names=gene_names` to the call.

## Output Schema

Both algorithms return a pandas DataFrame sorted by descending importance:

| Column | Meaning |
|--------|---------|
| `TF` | regulator gene name |
| `target` | regulated gene name |
| `importance` | edge weight — larger means a stronger inferred regulatory link |

```
TF1    gene5    0.856
TF2    gene12   0.743
TF1    gene8    0.621
```

**Interpret importance as a ranking, not a probability.** Scores are relative
within a run (they depend on `n_estimators` and the data scale); do not compare
raw magnitudes across different runs or datasets without normalization.

## Filtering the Network

Pick one or combine:

- **Top-N per target** — keep the strongest N regulators of each target gene.
- **Global importance cutoff** — e.g. `network[network['importance'] > 0.5]`.
  The right threshold is dataset-specific; inspect the score distribution first.
- **Consensus over seeds** — run several seeds and keep edges that recur (see
  `distributed.md`); the most robust option.

```python
high_confidence = network[network['importance'] > 0.5]
top_per_target = (network.sort_values('importance', ascending=False)
                         .groupby('target').head(10))
```

## Self-Contained CLI Script

A minimal, reusable runner. Save as `run_grn.py` and call
`python run_grn.py expr.tsv out.tsv --tf-file tfs.txt --seed 777`.

```python
#!/usr/bin/env python3
"""Infer a GRN with GRNBoost2 from a TSV expression matrix (genes as columns)."""
import argparse
import pandas as pd
from arboreto.algo import grnboost2
from arboreto.utils import load_tf_names


def run(expression_file, output_file, tf_file=None, seed=777):
    expression_data = pd.read_csv(expression_file, sep='\t')
    print(f"matrix shape (obs x genes): {expression_data.shape}")

    tf_names = load_tf_names(tf_file) if tf_file else 'all'

    network = grnboost2(
        expression_data=expression_data,
        tf_names=tf_names,
        seed=seed,
        verbose=True,
    )
    network.to_csv(output_file, sep='\t', index=False, header=False)
    print(f"wrote {len(network)} edges to {output_file}")


if __name__ == '__main__':                              # required for Dask
    p = argparse.ArgumentParser(description='GRNBoost2 GRN inference')
    p.add_argument('expression_file', help='TSV matrix, genes as columns')
    p.add_argument('output_file', help='TSV output path')
    p.add_argument('--tf-file', default=None, help='TF names, one per line')
    p.add_argument('--seed', type=int, default=777)
    a = p.parse_args()
    run(a.expression_file, a.output_file, a.tf_file, a.seed)
```

## Failure Modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Run hangs or re-launches endlessly | missing `if __name__ == '__main__':` guard | wrap the entry point |
| Empty or tiny network | matrix transposed (genes as rows) or TF names don't match gene names | verify orientation; align identifier convention/case |
| `MemoryError` on large data | full-genome regulators on many cells | pass a TF list; filter low-variance genes; use a distributed client |
| Non-deterministic results | no seed | pass `seed=` (algorithms subsample stochastically) |
| Very slow | using `genie3` on large data, or no regulator restriction | switch to `grnboost2`; narrow `tf_names`; add workers |

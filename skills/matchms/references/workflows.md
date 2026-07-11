# Workflows

Complete recipes. Two invariants across all of them: **filter references and
queries identically**, and **guard against `None`** after any rejecting filter.
For how to read the `Scores` object, see
[similarity.md](similarity.md).

## 1. Library matching (identify unknowns)

```python
from matchms.importing import load_from_mgf
from matchms.filtering import (default_filters, normalize_intensities,
    select_by_relative_intensity, require_minimum_number_of_peaks)
from matchms import calculate_scores
from matchms.similarity import CosineGreedy

def clean(s):
    s = default_filters(s)
    s = normalize_intensities(s)
    s = select_by_relative_intensity(s, intensity_from=0.01)
    return require_minimum_number_of_peaks(s, n_required=5)

library = [s for s in map(clean, load_from_mgf("reference_library.mgf")) if s]
queries = [s for s in map(clean, load_from_mgf("unknowns.mgf")) if s]

scores = calculate_scores(library, queries, CosineGreedy(tolerance=0.1))

for query in queries:
    top = scores.scores_by_query(query, name="CosineGreedy_score", sort=True)[:5]
    print(query.get("compound_name", "unknown"))
    for reference, (score, n_matches) in top:
        print(f"  {reference.get('compound_name')}: {float(score):.4f} ({int(n_matches)} peaks)")
```

## 2. Quality control / cleaning

```python
from matchms.importing import load_from_mgf
from matchms.exporting import save_as_mgf
from matchms.filtering import (default_filters, normalize_intensities,
    require_precursor_mz, require_minimum_number_of_peaks,
    require_minimum_number_of_high_peaks, select_by_relative_intensity,
    remove_peaks_around_precursor_mz)

raw = list(load_from_mgf("raw_data.mgf"))
clean = []
for s in raw:
    s = default_filters(s)
    s = require_precursor_mz(s, minimum_accepted_mz=50.0)
    if s is None: continue
    s = require_minimum_number_of_peaks(s, n_required=10)
    if s is None: continue
    s = normalize_intensities(s)
    s = remove_peaks_around_precursor_mz(s, mz_tolerance=17)
    s = select_by_relative_intensity(s, intensity_from=0.01)
    s = require_minimum_number_of_high_peaks(s, n_required=5, intensity_threshold=0.05)
    if s is None: continue
    clean.append(s)

print(f"kept {len(clean)} / {len(raw)}")
save_as_mgf(clean, "cleaned_data.mgf")
```

## 3. Precursor-filtered library search

Prune by precursor mass (cheap) before cosine (expensive).

```python
from matchms import calculate_scores
from matchms.similarity import PrecursorMzMatch, CosineGreedy

mass_ok = calculate_scores(library, queries,
    PrecursorMzMatch(tolerance=0.1, tolerance_type="Dalton")).to_array()["PrecursorMzMatch"]
cos = calculate_scores(library, queries, CosineGreedy(tolerance=0.1))
cos_arr = cos.to_array()["CosineGreedy_score"]

import numpy as np
for i, query in enumerate(queries):
    candidate_scores = np.where(mass_ok[:, i], cos_arr[:, i], -1.0)
    order = np.argsort(candidate_scores)[::-1]
    print(query.get("compound_name", f"query_{i}"))
    for j in order[:5]:
        if candidate_scores[j] < 0: break
        print(f"  {library[j].get('compound_name')}: {candidate_scores[j]:.4f}")
```

> The exact column name for a metadata gate (e.g. `"PrecursorMzMatch"`) can vary
> by version; check `scores.to_array().dtype.names` if the key raises.

## 4. All-vs-all spectral network

Score one set against itself, keep edges above a threshold, hand the graph to
`networkx` for community detection or layout.

```python
from matchms import calculate_scores
from matchms.similarity import ModifiedCosine
import networkx as nx

scores = calculate_scores(spectra, spectra, ModifiedCosine(tolerance=0.1),
                          is_symmetric=True)
mat = scores.to_array()["ModifiedCosine_score"]

threshold = 0.7
graph = nx.Graph()
for i in range(len(spectra)):
    for j in range(i + 1, len(spectra)):
        if mat[i, j] >= threshold:
            graph.add_edge(i, j, weight=float(mat[i, j]))

print(f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
```

## 5. Multi-metric consensus

Combine spectral + structural evidence (needs RDKit fingerprints and losses).

```python
from matchms.filtering import (default_filters, normalize_intensities,
    derive_inchi_from_smiles, add_fingerprint, add_losses)
from matchms import calculate_scores
from matchms.similarity import (CosineGreedy, ModifiedCosine,
    NeutralLossesCosine, FingerprintSimilarity)

def prep(s):
    s = default_filters(s)
    s = normalize_intensities(s)
    s = derive_inchi_from_smiles(s)
    s = add_fingerprint(s, fingerprint_type="morgan2", nbits=2048)
    return add_losses(s, loss_mz_from=5.0, loss_mz_to=200.0)

refs = [prep(s) for s in library if s]
qs = [prep(s) for s in queries if s]

cos = calculate_scores(refs, qs, CosineGreedy()).to_array()["CosineGreedy_score"]
mod = calculate_scores(refs, qs, ModifiedCosine()).to_array()["ModifiedCosine_score"]
nl  = calculate_scores(refs, qs, NeutralLossesCosine()).to_array()["NeutralLossesCosine_score"]
fp  = calculate_scores(refs, qs, FingerprintSimilarity()).to_array()["FingerprintSimilarity_score"]

consensus = 0.4 * cos + 0.3 * mod + 0.2 * nl + 0.1 * fp
```

## 6. Split by ion mode

```python
from matchms.filtering import default_filters, normalize_intensities, derive_ionmode

pos, neg = [], []
for s in load_from_mgf("mixed_modes.mgf"):
    s = derive_ionmode(default_filters(s))
    mode = s.get("ionmode")
    if mode == "positive":  pos.append(normalize_intensities(s))
    elif mode == "negative": neg.append(normalize_intensities(s))

print(f"positive={len(pos)} negative={len(neg)}")
```

Always analyze modes separately — cross-mode spectral comparison is not
meaningful without a mass-shift-aware metric.

## 7. Metadata enrichment & validation

```python
from matchms.filtering import (default_filters, derive_inchi_from_smiles,
    derive_inchikey_from_inchi, derive_smiles_from_inchi,
    add_fingerprint, repair_not_matching_annotation, require_valid_annotation)

enriched, failed = [], []
for i, s in enumerate(load_from_mgf("spectra.mgf")):
    s = default_filters(s)
    s = derive_inchi_from_smiles(s)
    s = derive_inchikey_from_inchi(s)
    s = derive_smiles_from_inchi(s)
    s = repair_not_matching_annotation(s)
    s = add_fingerprint(s, fingerprint_type="morgan2", nbits=2048)
    s = require_valid_annotation(s)
    (enriched if s is not None else failed).append(s if s is not None else i)

print(f"enriched={len(enriched)} failed={len(failed)}")
```

## 8. Identification report (to CSV)

```python
import pandas as pd
from matchms import calculate_scores
from matchms.similarity import CosineGreedy, ModifiedCosine

cos = calculate_scores(refs, qs, CosineGreedy())
mod = calculate_scores(refs, qs, ModifiedCosine()).to_array()["ModifiedCosine_score"]

rows = []
for i, query in enumerate(qs):
    top = cos.scores_by_query(query, name="CosineGreedy_score", sort=True)[:5]
    for rank, (reference, (score, _)) in enumerate(top, 1):
        rows.append({
            "query": query.get("compound_name", f"unknown_{i}"),
            "query_mz": query.get("precursor_mz"),
            "rank": rank,
            "match": reference.get("compound_name"),
            "inchikey": reference.get("inchikey"),
            "cosine": round(float(score), 4),
        })
pd.DataFrame(rows).to_csv("identification_report.csv", index=False)
```

## Best practices

1. One shared filter function for references and queries.
2. Cache preprocessed spectra as pickle for fast reruns; share as MGF/MSP/JSON.
3. Stream large files with generators; do not materialize unnecessarily.
4. QC before scoring — drop low-quality spectra early.
5. `CosineGreedy` for speed, `ModifiedCosine` for analogs, `PrecursorMzMatch`
   as a pre-filter, fingerprints/losses only when you need them.
6. Record filter parameters and matchms version for reproducibility.

Resources: `https://matchms.readthedocs.io` · `https://github.com/matchms/matchms`
· GNPS `https://gnps.ucsd.edu`.

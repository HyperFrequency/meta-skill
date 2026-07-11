# Similarity Scoring

A similarity function compares two spectra. `calculate_scores` applies one across
every reference/query pair and returns a `Scores` object.

```python
from matchms import calculate_scores
from matchms.similarity import CosineGreedy

scores = calculate_scores(references=library, queries=queries,
                          similarity_function=CosineGreedy(tolerance=0.1))
```

For a self-comparison (all-vs-all within one set), pass the same list twice and
set `is_symmetric=True` to roughly halve the work:

```python
scores = calculate_scores(spectra, spectra, CosineGreedy(), is_symmetric=True)
```

## Peak-based similarity

Compare fragmentation patterns (m/z + intensity). Shared parameters:
`tolerance` (max m/z difference to call two peaks a match, in Da),
`mz_power` (m/z weighting exponent, default `0.0` = off), and
`intensity_power` (intensity weighting exponent, default `1.0`).

### `CosineGreedy(tolerance=0.1, mz_power=0.0, intensity_power=1.0)`
Fast greedy peak matching. Default workhorse for large-scale library search when
speed matters more than perfectly optimal peak assignment. Returns a score in
`[0, 1]` and a matched-peak count.

### `CosineHungarian(tolerance=0.1, mz_power=0.0, intensity_power=1.0)`
Optimal peak matching via the Hungarian algorithm — more rigorous but slower.
Use for smaller sets or when reproducible, mathematically optimal assignment
matters.

### `ModifiedCosine(tolerance=0.1, mz_power=0.0, intensity_power=1.0)`
Cosine that also matches peaks **after a precursor-mass shift**, so it scores
structurally related compounds (analogs, adducts, derivatives) that a plain
cosine misses. Both spectra need valid `precursor_mz`.

### `NeutralLossesCosine(tolerance=0.1, mz_power=0.0, intensity_power=1.0)`
Scores on **neutral-loss** patterns (`precursor_mz - fragment_mz`) instead of raw
fragment m/z — good for shared fragmentation behavior across different precursor
masses. Run `add_losses(spectrum)` on both sets first, and both need valid
`precursor_mz`.

## Structure-based similarity

### `FingerprintSimilarity(similarity_measure="jaccard")`
Compares molecular fingerprints derived from SMILES/InChI — independent of the
peaks. Use to combine structural + spectral evidence, pre-filter candidates, or
score structure similarity directly. Compute fingerprints first with
`add_fingerprint(spectrum, fingerprint_type="morgan2", nbits=2048)` (requires
RDKit). `similarity_measure` ∈ `{"jaccard", "dice", "cosine"}`.

## Metadata gates (fast pre-filters)

These return 1.0 (match) / 0.0 (no match) and are cheap — use them to prune a
library before an expensive peak metric.

### `PrecursorMzMatch(tolerance=0.1, tolerance_type="Dalton")`
Match on precursor m/z. `tolerance_type` ∈ `{"Dalton", "ppm"}`. Both spectra need
`precursor_mz`.

### `ParentMassMatch(tolerance=0.1, tolerance_type="Dalton")`
Like `PrecursorMzMatch` but on neutral parent mass — adduct/ionization-mode
independent. Both spectra need `parent_mass` (run `add_parent_mass` first).

### `MetadataMatch(field, matching_type="exact", tolerance=None)`
Compare an arbitrary metadata field. `matching_type` ∈ `{"exact",
"difference", "relative_difference"}`; `tolerance` applies to the numeric modes.
Example: match retention time within 0.5 min →
`MetadataMatch(field="retention_time", matching_type="difference", tolerance=0.5)`.

## Reading the `Scores` object

This is the most common source of confusion. A `Scores` entry is a **structured**
value (score plus, for cosine-family metrics, a matched-peak count), and sorting
needs the score-column name `"<FunctionClassName>_score"` (e.g.
`"CosineGreedy_score"`, `"ModifiedCosine_score"`).

Best matches for one query:
```python
best = scores.scores_by_query(query, name="CosineGreedy_score", sort=True)
for reference, (score, n_matches) in best[:10]:
    print(reference.get("compound_name"), float(score), int(n_matches))
```

Full matrix as NumPy (structured array; index by the score column):
```python
arr = scores.to_array()                 # structured 2-D array
numeric = arr["CosineGreedy_score"]     # plain float matrix, shape (n_ref, n_query)
```

Persist:
```python
scores.to_json("scores.json")
scores.to_pickle("scores.pkl")
```

Exact field names, the `array_type` option, and helper methods vary a little by
matchms version — if `name=` or a field key raises, inspect
`scores.to_array().dtype.names` to see the available columns.

## Choosing a metric

| Situation | Metric |
| --- | --- |
| Large library, speed first | `CosineGreedy` (often after `PrecursorMzMatch`) |
| Optimal matching, small set | `CosineHungarian` |
| Find analogs / mass-shifted relatives | `ModifiedCosine` |
| Shared fragmentation across masses | `NeutralLossesCosine` (+ `add_losses`) |
| Structure similarity / combine with spectra | `FingerprintSimilarity` (+ `add_fingerprint`) |
| Cheap pre-filter | `PrecursorMzMatch` / `ParentMassMatch` / `MetadataMatch` |

## Multi-metric consensus

Compute several score matrices and combine with weights. Use `to_array()` and the
score columns so you are combining plain floats:

```python
from matchms.similarity import CosineGreedy, ModifiedCosine, FingerprintSimilarity

cos = calculate_scores(refs, qs, CosineGreedy()).to_array()["CosineGreedy_score"]
mod = calculate_scores(refs, qs, ModifiedCosine()).to_array()["ModifiedCosine_score"]
fp  = calculate_scores(refs, qs, FingerprintSimilarity()).to_array()["FingerprintSimilarity_score"]

consensus = 0.5 * cos + 0.3 * mod + 0.2 * fp   # shape (n_ref, n_query)
```

## Performance

- Fast: `CosineGreedy`, `PrecursorMzMatch`, `ParentMassMatch`.
- Slower: `CosineHungarian`, `ModifiedCosine`, `NeutralLossesCosine`,
  `FingerprintSimilarity` (fingerprint computation).
- Large searches: pre-filter with `PrecursorMzMatch`, then run the expensive
  metric only on candidates that pass.

Official docs:
`https://matchms.readthedocs.io/en/latest/api/matchms.similarity.html`.

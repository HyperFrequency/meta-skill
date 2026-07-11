# Combined Glycoprotein Analysis, CLI, and UniProt Validation

This reference ties the N- and O-glycosylation predictors together into a single
report, exposes them as a command-line script, and shows how to score predictions
against experimentally annotated sites.

## `analyze_glycoprotein` — one-call roll-up

```python
def analyze_glycoprotein(sequence, protein_name="protein", uniprot_sites=None):
    """Run N- and O-glyc prediction and (optionally) compare to known sites.

    Args:
        sequence: protein sequence string.
        protein_name: label for the report.
        uniprot_sites: {"N_glyc": [positions], "O_glyc": [positions]} of
            experimentally annotated sites, if available.

    Returns: dict with `n_glyc_sites`, `o_glyc_sites`, `o_glyc_regions`, and (if
    `uniprot_sites` given) a `validation` sub-dict of TP/FP/FN sets.
    """
    seq = str(sequence).upper()
    n_sites = find_n_glycosylation_sites(seq)                 # see n-glycosylation.md
    o_sites = predict_o_glyc_hotspots(seq)                    # see o-glycosylation.md
    o_regions = merge_hotspot_regions(o_sites)

    result = {
        "n_glyc_sites": n_sites,
        "o_glyc_sites": o_sites,
        "o_glyc_regions": o_regions,
    }

    if uniprot_sites:
        known = set(uniprot_sites.get("N_glyc", []))
        predicted = {s["position"] for s in n_sites}
        result["validation"] = {
            "true_positives": sorted(known & predicted),
            "false_positives": sorted(predicted - known),   # sequon, not annotated
            "false_negatives": sorted(known - predicted),   # annotated, no sequon
        }
    return result
```

A **false negative** (annotated site with no canonical sequon) is the interesting
case: inspect its context — it is often an `N-P-S/T` (excluded by the default
rule), a non-canonical `N-X-C`, or an annotation numbered on a different chain.

## Command-line script

The bundled `scripts/predict_glycosylation.py` wraps both predictors for shell
use. It accepts a raw sequence or a FASTA path and writes two artifacts to an
output directory.

```bash
# Inline sequence
python scripts/predict_glycosylation.py \
    --sequence "MKNSTLYNRTSGQPN" --output-dir ./glyc_out

# FASTA file, tuned O-glyc density threshold and window
python scripts/predict_glycosylation.py \
    --sequence myprotein.fasta --output-dir ./glyc_out \
    --threshold 0.25 --window-size 15
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--sequence` | *(required)* | Amino-acid string **or** path to a single-record FASTA |
| `--output-dir` | *(required)* | Directory for outputs (created if absent) |
| `--threshold` | `0.3` | O-glyc sliding-window S/T density cutoff |
| `--window-size` | `11` | O-glyc sliding-window length |

Outputs:

- `glycosylation_predictions.csv` — one row per site: `position`, `type`,
  `motif`, `flanking_sequence`, `confidence_note`.
- `annotated_sequence.txt` — the sequence wrapped at 60 columns with a marker
  track underneath (`^` = N-sequon, `o` = O-hotspot, `*` = both).

The script validates input (rejects non-amino-acid characters, requires ≥3
residues) and exits non-zero with a stderr message on bad input.

## Coordinate systems — the offset trap

Glycosylation happens in the ER/Golgi **after** signal-peptide cleavage, so
databases usually number sites on the **mature** chain. If you scan the full
precursor (signal peptide included), every predicted position is shifted by the
signal-peptide length relative to UniProt's `CARBOHYD` features. Before comparing:

1. Decide one coordinate frame (precursor vs mature) and use it everywhere.
2. If mixing, offset predictions by the signal-peptide length (UniProt `SIGNAL`
   feature gives the cleavage position).
3. Isoform choice matters too — confirm you and the database annotate the same
   isoform.

## Best practices

1. **Sequon ≠ occupancy.** Present sequon hits as candidates; use NetNGlyc for
   N-glyc and NetOGlyc for O-glyc probabilities before making claims.
2. **Filter by localization first.** N-glycosylation requires the secretory
   pathway; sequons in cytoplasmic/nuclear proteins are biological false
   positives. Check subcellular localization (UniProt) up front.
3. **Validate against UniProt.** Always cross-reference the `CARBOHYD`
   annotations; use the `bioservices` sibling skill to pull them programmatically.
4. **Check accessibility.** A buried sequon may never be glycosylated — inspect a
   structure (AlphaFold DB / PDB) for surface exposure.
5. **Biotherapeutics.** For antibody/Fc engineering, the conserved IgG **N297**
   glycan drives effector function; do not silently mutate it away.
6. **O-glyc is hard.** Report regions, not confident residue calls; the heuristic
   false-positive rate is high.

## Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Sequons found in a cytoplasmic protein | Prediction is topology-blind | Filter by subcellular localization; N-glyc is secretory-pathway only |
| A known N-site is missed | It is `N-P-S/T` (excluded) or non-canonical `N-X-C` | Re-scan with `exclude_proline=False` and the `find_nxc_sequons` scan; inspect flanks |
| Predicted positions off by a constant | Scanned precursor; DB numbers the mature chain | Offset by the signal-peptide length (UniProt `SIGNAL`) |
| Too many O-glyc hotspots | Threshold too permissive | Raise `--threshold` to 0.4–0.5; focus on extracellular domains |
| No O-glyc hotspots at all | Genuinely S/T-poor, or window > sequence length | Correct answer if S/T-poor; shrink `--window-size` for short proteins |
| Script errors on the sequence | Non-amino-acid characters or <3 residues | Clean the sequence (upper-case, strip gaps/whitespace); check the FASTA |
| Predictions disagree with a paper | Different isoform or coordinate frame | Align isoform accession and numbering convention before comparing |

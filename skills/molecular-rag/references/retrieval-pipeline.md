# Retrieval Pipeline

The retrieval stack for molecular RAG: how a query SMILES becomes a
similarity-ranked set of analogs with measured data, and how to feed that back
into a model to ground a prediction. Method after MolRAG (Xian et al., 2025).

## 1. Fingerprints and similarity

Structural similarity is measured with **ECFP4** (Extended-Connectivity
FingerPrint, diameter 4 = Morgan radius 2), the de-facto standard for analog
search:

```python
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs

def ecfp4(smiles, n_bits=2048):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=n_bits)

query_fp  = ecfp4("O=C(Nc1ccccc1)c1ccccc1Cl")
analog_fp = ecfp4("O=C(Nc1ccccc1)c1ccccc1F")
tanimoto  = DataStructs.TanimotoSimilarity(query_fp, analog_fp)   # 0..1
```

**Tanimoto similarity** on ECFP4 bit vectors is the ranking metric. Rough
interpretation for drug-like molecules:

| Tanimoto | Meaning |
|----------|---------|
| ≥ 0.85   | near-identical scaffold (often the same series / a known compound) |
| 0.6–0.85 | close analog — usually meaningful SAR transfer |
| 0.4–0.6  | weakly related — same rough chemotype, treat conclusions cautiously |
| < 0.4    | essentially unrelated — grounds nothing |

## 2. Threshold semantics

The skill exposes `--similarity-threshold` as a **Tanimoto fraction** in
`[0.4, 1.0]`. ChEMBL's similarity endpoint wants an **integer percentage** with a
hard floor of **40**, so the fraction is multiplied by 100 and clamped:

```python
chembl_pct = max(40, min(100, int(threshold * 100)))
```

Requesting below 0.4 (40%) is rejected by the service — clamp and warn rather than
error. A high threshold (≥ 0.8) returns few, tight analogs; a low threshold widens
recall at the cost of relevance. Start at 0.6 for optimization work, 0.85+ for a
novelty / known-compound check.

## 3. Retrieval modes

**Property mode (default).** Similarity search → for each hit, keep
`molecule_chembl_id`, canonical SMILES, `pref_name`, and physchem properties (MW,
ALogP, HBA, HBD, PSA). Re-score Tanimoto locally so the ranking is self-consistent.

**SAR-context mode (`--include-activities`).** After property mode, fetch each
analog's `activity` records and attach normalized bioactivities (type, value,
units, target, `pchembl_value`). This is the payload for structure-activity
reasoning: "the 4-F analog reported IC50 12 nM vs the 4-Cl at 45 nM."

**Target mode (`--target CHEMBL…`).** Retrieve similar compounds, then keep only
those with recorded activity **against that target**, returning the target-specific
activity range. Use to estimate a plausible potency window before making a compound.

## 4. Grounding a prediction (the RAG pattern)

Retrieval is only half of RAG — the analogs must be injected into the reasoning
step. The pattern:

1. **Retrieve** k analogs (k ≈ 5–20) with measured values for the property in
   question.
2. **Filter** to comparable measurements (same `standard_type`, same `units`;
   prefer `pchembl_value` for potency; drop censored `standard_relation` values
   unless a bound is what you want).
3. **Inject** the analog table into the model prompt as evidence, e.g.:

   > Predict hERG risk for `<query SMILES>`. Ground your answer in these measured
   > analogs (Tanimoto, structure, measured value): `<retrieved table>`. Cite which
   > analog(s) drive your estimate and note where the query diverges structurally.

4. **Require attribution.** A grounded answer names the analogs it leaned on, so a
   reviewer can check the evidence and see when the query is actually far from all
   of them (the honest "no good analog" case).

The win over ungrounded prediction is falsifiability: the claim is tied to
retrievable rows, and an out-of-domain query surfaces as "nearest analog is only
0.42 similar" instead of a confident hallucination.

## 5. Practical notes

- **De-duplicate** near-identical hits (Tanimoto ≈ 1.0 among retrieved analogs are
  often salt forms / stereo variants of one compound) before counting evidence.
- **Cap activity fan-out.** Fetching activities for every analog is the slow,
  rate-limited path; retrieve properties for all, activities for the top-k only.
- **Multiple sources.** ChEMBL covers assay bioactivity; for purchasable-space
  novelty or larger analog sets, extend the same fingerprint/Tanimoto flow to
  PubChem or ZINC (see `references/chembl-api.md` for endpoints and alternatives).

## Citation

- Xian et al. (2025). *MolRAG: Retrieval-Augmented Generation for Molecular
  Property Prediction.* ACL 2025. Retrieve structurally similar compounds with
  known properties to ground LLM property predictions.

# Assay Menu, Workflows, and Result Schemas

Adaptyv exposes four assay families. Each expresses and purifies your sequence first, then
runs the measurement. Result JSON below is representative of the upstream schema — field
names may drift; confirm against a live `GET /experiments/{id}/results` payload.

## Binding assays (biolayer interferometry, BLI)

Label-free, real-time measurement of protein–target interaction. A biosensor tip carries an
immobilized partner; as the analyte binds, optical thickness increases and shifts the
reflected wavelength proportionally to bound mass. Works in crude samples, needs little
material, and yields full kinetics rather than a single endpoint.

**Use for:** antibody–antigen characterization, receptor–ligand analysis, affinity-maturation
screening, epitope binning.

**Measured:** `KD` (equilibrium dissociation constant / affinity), `kon` (association rate),
`koff` (dissociation rate). Rough affinity bands: strong `KD < 1 nM`, moderate `1–100 nM`,
weak `> 100 nM`.

**Needs:** sequence(s) in FASTA, a target (catalog or custom request), buffer conditions,
optionally an expected concentration range (improves assay design).

```json
{
  "sequence_id": "antibody_variant_1",
  "target": "Human PD-L1",
  "measurements": {
    "kd": 2.5e-9, "kd_error": 0.3e-9,
    "kon": 1.8e5, "kon_error": 0.2e5,
    "koff": 4.5e-4, "koff_error": 0.5e-4
  },
  "quality_metrics": { "confidence": "high", "r_squared": 0.97, "chi_squared": 0.02, "flags": [] },
  "raw_data_url": "https://…"
}
```

## Expression testing

Quantifies how much protein you can actually make, and how much of it is soluble — the first
gate on manufacturability.

**Use for:** ranking variants by expression, spotting expression bottlenecks, selecting
scale-up candidates, comparing host systems.

**Host systems:** E. coli (fast, cheap, prokaryotic), mammalian (native PTMs), yeast
(eukaryotic, simpler growth), insect cells.

**Measured:** total yield (mg/L culture), soluble fraction (%), purity after initial
purification, optionally an expression time course.

```json
{
  "sequence_id": "variant_1",
  "host_system": "E. coli",
  "measurements": { "total_yield_mg_per_l": 25.5, "soluble_fraction_percent": 78, "purity_percent": 92 },
  "ranking": { "percentile": 85, "notes": "High expression, good solubility" }
}
```

## Thermostability testing

Thermal stability as a proxy for structural integrity, shelf-life, and the effect of
stabilizing mutations.

**Techniques:** differential scanning fluorimetry (DSF, dye-based unfolding → Tm,
high-throughput) and circular dichroism (CD, secondary structure + reversibility).

**Measured:** `Tm` (melting temperature, unfolding midpoint), ΔH (unfolding enthalpy),
`Tagg` (aggregation temperature), reversibility (% refolding after heating).

```json
{
  "sequence_id": "variant_1",
  "measurements": { "tm_celsius": 68.5, "tm_error": 0.5, "tagg_celsius": 72.0, "reversibility_percent": 85 },
  "quality_metrics": { "curve_quality": "excellent", "cooperativity": "two-state" }
}
```

## Enzyme activity assays

Catalytic function: turnover, efficiency, inhibitor sensitivity.

**Assay styles:** continuous (chromogenic/fluorogenic substrate, real-time) or endpoint
(HPLC, mass spec, colorimetric).

**Measured:** `kcat` (turnover number), `KM` (substrate affinity), `kcat/KM` (catalytic
efficiency), `IC50` (inhibitor potency), specific activity (units/mg), relative activity vs a
reference.

```json
{
  "sequence_id": "enzyme_variant_1",
  "substrate": "substrate_name",
  "measurements": { "kcat_per_second": 125, "km_micromolar": 45, "kcat_km": 2.8, "specific_activity": 180 },
  "quality_metrics": { "confidence": "high", "r_squared": 0.99 },
  "ranking": { "relative_activity": 1.8, "improvement_vs_wildtype": "80%" }
}
```

## Experiment design

- **Name sequences descriptively** and **always include a control** (wild-type or a known-good reference) so results are interpretable relative to a baseline.
- **Batch related variants** in one submission — lower per-sequence cost, shared controls.
- **Validate FASTA locally** before submitting (see `examples.md`).
- **Sample size, rough guide:** pilot 5–10, focused optimization 10–50, library screen 50–500, ML-driven campaign 500+.
- Adaptyv runs automated QC: expression verification before the assay, replicate measurements, positive/negative controls per batch, statistical validation.

## Timeline

Standard turnaround is ~21 days end to end. Indicative breakdown:

| Stage | Days |
| --- | --- |
| Construct generation | 3–5 |
| Expression | 5–7 |
| Purification | 2–3 |
| Assay execution | 3–5 |
| Analysis & QC | 2–3 |

Custom targets add ~1–2 weeks; novel assay development ~2–4 weeks; very large batches may add
~1 week.

## Combining assays

Characterize a candidate along more than one axis, and choose the ordering:

- **Therapeutic antibody:** binding → expression → thermostability.
- **Enzyme engineering:** activity → expression → thermostability.
- **Sequential** uses early cheap assays to filter before the expensive ones; **parallel**
  runs everything at once for the fastest total time. Sequential saves money, parallel saves
  calendar.

## Data integration

Download raw data via the API, parse into a standard tabular form (see `examples.md`), feed
the measurements into the next round of your design model, and tag each experiment with
metadata so rounds stay traceable. This closed loop is the whole point — the assays are the
verifiable-reward signal for a protein-design search.

# Interpreting Results

`workflow.data` is a dict whose keys depend on the workflow type. Always confirm the
job finished before reading, and treat every field as possibly absent.

## Access pattern

```python
wf.wait_for_result()
wf.fetch_latest(in_place=True)          # data is lazy — this is required
if wf.status == "completed":
    energy = wf.data.get("energy")      # .get() guards missing keys
elif wf.status == "failed":
    print(wf.error_message)
print(wf.credits_charged)               # credits actually spent
```

Status values: `pending` (queued), `running`, `completed`, `failed`, `stopped`.

## Property results and how to read them

**pKa** — `strongest_acid`, `strongest_base`, `microscopic_pkas` (each with
`atom_index`, `pka`), `tautomer_populations`. Guide: pKa < 0 strong acid; 0–7 acidic;
7–14 basic; > 14 very weak acid. A pKa off by > 2 usually means the wrong tautomer or
protonation state was used.

**Redox** — `oxidation_potential`, `reduction_potential` (V vs SHE). Higher oxidation
potential = harder to oxidize; interpret relative to reference compounds.

**Solubility** — `aqueous_solubility` (log S), `solubility_class`. Guide: log S > −1
high (> 0.1 M); −1 to −3 medium; < −3 low.

**Fukui** — `fukui_plus` (nucleophilic-attack sites), `fukui_minus`
(electrophilic-attack sites), `fukui_dual` (> 0 electrophilic, < 0 nucleophilic
character), per atom.

## Modeling results

**Optimization** — `final_molecule`, `energy` (Hartree), `convergence`.

**Frequency** — `frequencies` (cm⁻¹), `ir_intensities`, `zpe`, `gibbs_free_energy`.
Count negative frequencies: 0 = minimum, 1 = transition state, > 1 = higher-order
saddle point. Convert to kcal/mol with the factor `627.509`.

**Conformer search** — `conformers` (with `energy`), `lowest_energy_conformer`,
`boltzmann_weights`. Conformers within ~3 kcal/mol are thermally accessible at room
temperature; the global minimum is not necessarily the most populated in solution, so
prefer ensemble averaging for properties.

**Dihedral scan** — `angles`, `energies`; barrier = `(max − min) × 627.509` kcal/mol.

## Docking

`docking_score` (kcal/mol, more negative = stronger predicted binding), `poses` (each
with `score`), `ligand_strain`, `pose_sdf`. Guide: drug-like Vina scores fall roughly
−12 to −6; a **positive** score means the ligand does not fit the pocket, and ligand
strain > ~3 kcal/mol suggests an unrealistic bound conformation. Batch docking returns
`results` (per ligand) and `rankings`; sort by `best_score`. Vinardo scoring often
tracks experiment better than the original Vina function.

```python
wf.download_sdf_file("docked_poses.sdf")   # export poses
```

## Cofolding

`ptm_score` (predicted TM, 0–1), `interface_ptm`, `aggregate_score`, `structure_pdb`,
optional `ligand_rmsd`.

| Score | Confidence | Action |
|---|---|---|
| > 0.8 | high | likely accurate |
| 0.5–0.8 | moderate | use with caution |
| < 0.5 | low | validate experimentally |

Low confidence points to a novel fold, disordered regions, an unusual ligand, or
multiple binding modes. Mitigations: run more than one model (`chai_1r`, `boltz_1x`,
`boltz_2`) and compare; refine the pose with docking; check against experimental data.

## Validation habits

- **Cross-method** — rerun an optimization at `gfn2_xtb` and `aimnet2`; large energy
  disagreement flags a shaky result.
- **Sanity bounds** — pKa outside roughly −5 to 20, or a positive docking score,
  deserve scrutiny before you trust them.
- **Experimental anchors** — pKa (potentiometric titration/UV), solubility
  (shake-flask), pose (X-ray/cryo-EM), affinity (SPR/ITC), cofold (X-ray/NMR/HDX-MS).

## Common failures

- **Workflow `failed`** — inspect `wf.error_message`; usual causes are invalid SMILES,
  an oversized molecule, convergence failure, or exceeding `max_credits`.
- **Missing keys** — always `data.get(key)`; output sets vary by method and version.
- **Optimization not converged** — retry from a different starting geometry.

## Export

```python
import pandas as pd
rows = []
for wf in workflows:
    wf.fetch_latest(in_place=True)
    if wf.status == "completed":
        rows.append({"name": wf.name,
                     "pka": wf.data.get("strongest_acid"),
                     "credits": wf.credits_charged})
pd.DataFrame(rows).to_csv("results.csv", index=False)

wf.download_dcd_files(output_dir="trajectories/")  # MD trajectories
```

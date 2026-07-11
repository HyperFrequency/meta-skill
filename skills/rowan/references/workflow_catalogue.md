# Rowan Workflow Catalogue

One entry per workflow type: how to submit it and the keys it writes into
`workflow.data`. Common kwargs `name`, `folder_uuid`, `max_credits` are omitted for
brevity. Read results only after `wait_for_result()` then `fetch_latest(in_place=True)`.

## Property prediction

### pKa — `submit_pka_workflow(initial_molecule=mol)`
Output: `strongest_acid`, `strongest_base`, `microscopic_pkas` (site-specific list),
`tautomer_populations` (relative populations near pH 7).

### Redox potential — `submit_redox_potential_workflow(...)`
Output: `oxidation_potential`, `reduction_potential` (V vs SHE).

### Solubility — `submit_solubility_workflow(...)`
Output: `aqueous_solubility` (log S), `solubility_class` (`High`/`Medium`/`Low`).

### H-bond basicity — `submit_workflow(..., workflow_type="hydrogen_bond_basicity")`
Output: `hb_basicity` (pKBHX).

### Bond dissociation energy — `submit_bde_workflow(..., bond_indices=(i, j))`
Output: `bde` (kcal/mol), `radical_stability`.

### Fukui indices — `submit_fukui_workflow(...)`
Output: `fukui_plus`, `fukui_minus`, `fukui_dual` (per-atom reactivity descriptors).

### Spin states — `submit_workflow(..., workflow_type="spin_states")`
Output: `spin_state_energies` (per multiplicity), `ground_state`.

### ADME-Tox — `submit_workflow(..., workflow_type="admet")`
Output: descriptor set incl. `logP`, `logD`, `herg_inhibition`, `cyp_inhibition`,
`bioavailability`, `bbb_permeability`.

## Molecular modeling

Optimization / single-point / frequency share one helper:
`submit_basic_calculation_workflow(initial_molecule=mol, workflow_type=…)`.

### Single-point (`"single_point"`)
Output: `energy` (Hartree), `dipole`, `mulliken_charges`.

### Optimization (`"optimization"`)
Output: `final_molecule` (stjames.Molecule), `energy`, `convergence`.

### Frequency (`"frequency"`)
Output: `frequencies` (cm⁻¹), `ir_intensities`, `zpe`, `thermal_corrections`
(enthalpy/entropy/Gibbs), `imaginary_frequencies` (count).

### Conformer search — `submit_conformer_search_workflow(...)`
Output: `conformers` (structures + energies), `lowest_energy_conformer`,
`boltzmann_weights` (298 K populations).

### Tautomer search — `submit_tautomer_search_workflow(...)`
Output: `tautomers`, `energies` (relative), `populations`.

### Dihedral scan — `submit_dihedral_scan_workflow(..., dihedral_indices=(a,b,c,d))`
Output: `angles` (deg), `energies`, `barrier_height` (kcal/mol).

### Multistage optimization — `submit_workflow(..., workflow_type="multistage_optimization", workflow_data={"stages": ["gfn2_xtb", "aimnet2", "dft"]})`
Progressive refinement across methods. Output: `final_molecule`, `stage_energies`.

### Transition-state search — `submit_ts_search_workflow(initial_molecule=guess)`
Give a geometry near the TS. Output: `ts_structure`, `imaginary_frequency` (single),
`barrier_height`.

### Strain — `submit_workflow(..., workflow_type="strain")`
Output: `strain_energy`, `reference_energy` (lowest-conformer energy).

### Orbitals — `submit_workflow(..., workflow_type="orbitals")`
Output: `homo_energy`, `lumo_energy`, `homo_lumo_gap` (eV), `orbital_coefficients`.

## Protein-ligand

### Docking — `submit_docking_workflow(protein, pocket, initial_molecule, ...)`
`pocket = {"center": [x,y,z], "size": [dx,dy,dz]}`. Toggles: `executable`
(`vina`/`qvina2`), `scoring_function` (`vina`/`vinardo`), `exhaustiveness`,
`do_csearch`, `do_optimization`, `do_pose_refinement`.
Output: `docking_score` (kcal/mol, more negative = better), `poses`, `ligand_strain`,
`pose_sdf`.

### Batch docking — `submit_batch_docking_workflow(protein, pocket, smiles_list, ...)`
Screen many ligands against one target. Output: `results` (per ligand), `rankings`.

### Cofolding — `submit_protein_cofolding_workflow(initial_protein_sequences=[...], initial_smiles_list=[...], model=...)`
Models: `chai_1r` (~2 min), `boltz_1x` (~2 min), `boltz_2` (latest, recommended).
Flags: `use_msa_server`, `use_potentials`, `compute_strain`, `do_pose_refinement`.
Output: `structure_pdb`, `ptm_score` (0-1), `interface_ptm`, `aggregate_score`,
`ligand_rmsd` (if a reference is supplied).

### Pose-analysis MD — `submit_workflow(..., workflow_type="pose_analysis_md", workflow_data={"protein_uuid": …, "pose_sdf": …})`
Output: `trajectory`, `rmsd_over_time`, `interactions`. This is the only MD surface —
it analyzes a docked pose, not a general simulation.

### Binder design — `submit_workflow(..., workflow_type="protein_binder_design", workflow_data={"target_sequence": …, "target_hotspots": [...]})`
Output: `designed_sequences`, `confidence_scores`.

## Spectroscopy & descriptors

### NMR — `submit_nmr_workflow(...)`
Output: `h_shifts`, `c_shifts` (ppm), `coupling_constants`.

### Ion mobility — `submit_ion_mobility_workflow(...)`
Output: `ccs` (collision cross-section, Å²), `conformer_ccs`.

### Descriptors — `submit_descriptors_workflow(...)`
Output: 2D (RDKit-based), 3D (xTB-based), and electronic descriptors.

### MSA — `submit_msa_workflow(sequences=[...])`
Output: `msa`, `coverage`.

## Method / level-of-theory selection

For basic calculations, pass a method (and basis set for DFT) in `workflow_data`:

```python
rowan.submit_basic_calculation_workflow(
    initial_molecule=mol, workflow_type="optimization",
    workflow_data={"method": "gfn2_xtb", "basis_set": "def2-SVP"},
)
```

- **Neural-network potentials:** `aimnet2`, `egret` — fast, broadly accurate.
- **Semiempirical:** `gfn1_xtb`, `gfn2_xtb` — cheap, good for large systems.
- **DFT:** `b3lyp`, `pbe`, `wb97x` (+ a basis set) — most accurate, most expensive.

Omit `method` to accept Rowan's default for the workflow type.

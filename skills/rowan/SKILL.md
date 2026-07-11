---
name: rowan
version: 0.1.0
description: >-
  Cloud quantum-chemistry and molecular structure-prediction platform driven from
  Python via the `rowan` client and `stjames` molecules. Use WHEN a task needs
  computational chemistry without a local HPC/QM stack: pKa, redox potential,
  solubility, ADMET, Fukui/BDE, geometry optimization, conformer and tautomer
  search, dihedral and transition-state scans, NMR/ion-mobility, protein-ligand
  docking (AutoDock Vina / QVina2), or AI cofolding (Chai-1, Boltz-1x/2). Covers
  job submission and polling, batch jobs, RDKit-native one-call helpers, folder and
  project organization, and result interpretation. Do NOT use for local/offline QM
  where you run your own engine (PySCF, Psi4, ORCA, xtb), for pure cheminformatics
  with no quantum calculation (use `rdkit` directly), for classical MD you host
  yourself, or when a paid cloud API key (ROWAN_API_KEY) is unavailable — Rowan is a
  metered cloud service.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: Rowan (rowansci.com) — proprietary cloud service, API key required
---

# Rowan: Cloud Quantum Chemistry and Structure Prediction

## Overview

Rowan runs quantum-chemistry and AI structure-prediction jobs on managed cloud
compute, exposed through the `rowan` Python client. You never install or configure
a QM engine locally — you describe a molecule, submit a *workflow*, and read a
results dictionary when it finishes.

The mental model is a four-step loop that every workflow follows:

1. **Build** a molecule (`stjames.Molecule` from SMILES/XYZ/RDKit, or a raw SMILES
   string for the RDKit-native helpers).
2. **Submit** a typed workflow (`rowan.submit_*_workflow(...)`) — returns a
   `Workflow` handle immediately; compute happens server-side.
3. **Wait / poll** until the job leaves the `pending`/`running` state.
4. **Fetch and read** results into `workflow.data` (a dict keyed by property).

Two API surfaces sit on top of that loop:

- **Full workflow API** — `stjames.Molecule` in, `Workflow` object out. You control
  waiting, folders, method selection, and every parameter. Use for pipelines and
  anything non-trivial.
- **RDKit-native helpers** — `rowan.run_pka(mol)` / `rowan.batch_pka(mols)` take
  RDKit `Mol` objects, block until done, and return typed result objects. Use for
  quick, one-call cheminformatics integration.

Underlying methods span neural-network potentials (AIMNet2, Egret), semiempirical
tight-binding (GFN1/2-xTB), and DFT (B3LYP, PBE, ωB97X). Rowan picks a sensible
level of theory per workflow type; you can override it via `workflow_data`.

## When to Use This Skill

- You need a computed molecular property — pKa, redox potential, solubility, ADMET,
  Fukui indices, bond-dissociation energy — and don't want to stand up a QM stack.
- You need geometry optimization, single-point energy, frequencies/thermochemistry,
  conformer or tautomer ensembles, a dihedral scan, or a transition-state search.
- You need protein-ligand **docking** (AutoDock Vina / QVina2) or AI **cofolding**
  (Chai-1, Boltz-1x, Boltz-2) for a complex-structure prediction.
- You are screening a compound library and want batched, parallel cloud jobs with
  folder/project organization and credit limits.
- You want predicted NMR shifts, IR frequencies, or ion-mobility (CCS) values.

## When NOT to Use This Skill

- **Offline / self-hosted QM.** If the requirement is to run your own engine
  (PySCF, Psi4, ORCA, Gaussian, xtb) locally or on your own cluster, use that engine
  directly — Rowan is a remote service, not a local library.
- **Pure cheminformatics with no quantum step** (descriptors, substructure search,
  fingerprints, SMILES munging) — use `rdkit` directly; do not spend cloud credits.
- **Classical MD you host yourself** (OpenMM/GROMACS trajectories) — Rowan exposes
  only pose-analysis MD tied to a docking result, not a general MD engine.
- **No API key / no budget.** Every job consumes metered credits and requires
  `ROWAN_API_KEY`. If neither is available, this skill cannot run.
- **Hard real-time latency needs** — jobs queue and run asynchronously (seconds to
  minutes), so this is unsuitable for synchronous, sub-second calls.

## Setup and Authentication

```bash
uv pip install rowan-python   # provides the `rowan` and `stjames` packages
export ROWAN_API_KEY="…"      # read automatically on import (preferred over inline)
```

Generate a key at `labs.rowansci.com/account/api-keys`. Prefer the environment
variable; assign `rowan.api_key = "…"` inline only for throwaway scripts. Confirm
auth and check your balance before submitting expensive batches:

```python
import rowan
user = rowan.whoami()
print(user.username, user.credits)   # fail fast if credits are exhausted
```

## The Core Loop

```python
import rowan, stjames

mol = stjames.Molecule.from_smiles("c1ccccc1O")          # phenol
wf = rowan.submit_pka_workflow(initial_molecule=mol, name="phenol pKa")

wf.wait_for_result(timeout=3600)                          # block, with a ceiling
wf.fetch_latest(in_place=True)                            # results are NOT auto-loaded

if wf.status == "completed":
    print(wf.data["strongest_acid"])                     # ~10 for phenol
else:
    print("failed:", wf.error_message)
```

Two things bite newcomers: `workflow.data` is **lazy** — you must call
`fetch_latest()` after `wait_for_result()` — and a returned `Workflow` means
*submitted*, not *done*. Always branch on `wf.status` before reading `data`.

## Capability Map

Pick the workflow family, then open the reference for exact signatures, parameters,
and output keys.

| Family | Representative workflows | Reference |
|---|---|---|
| Property prediction | pKa, redox, solubility, ADMET, Fukui, BDE, H-bond basicity, spin states | [workflow_catalogue.md](references/workflow_catalogue.md) |
| Molecular modeling | optimization, single-point, frequency, conformer/tautomer search, dihedral scan, TS search, multistage opt, orbitals, strain | [workflow_catalogue.md](references/workflow_catalogue.md) |
| Protein-ligand | docking, batch docking, cofolding (Chai-1/Boltz), pose-analysis MD, binder design | [workflow_catalogue.md](references/workflow_catalogue.md) |
| Spectroscopy | NMR shifts, ion mobility (CCS), descriptors | [workflow_catalogue.md](references/workflow_catalogue.md) |
| Client API (classes, submit/retrieve/batch, errors) | `Workflow`, `User`, submission + retrieval functions | [api_reference.md](references/api_reference.md) |
| Molecule I/O | `stjames.Molecule` from SMILES/XYZ/EXTXYZ/RDKit, geometry, charge/spin | [molecules.md](references/molecules.md) |
| RDKit-native helpers | `run_*` / `batch_*` for pKa, tautomers, conformers, energy, optimization | [rdkit_native.md](references/rdkit_native.md) |
| Proteins & organization | protein upload/sanitize, folders, projects, campaign layout | [proteins_and_organization.md](references/proteins_and_organization.md) |
| Reading results | per-workflow output keys, confidence scores, validation, export | [results_interpretation.md](references/results_interpretation.md) |

## Batch, Folders, and Credits

For many similar jobs, submit as a batch and poll collectively rather than looping
one-at-a-time; group related runs in a folder or project for organization and
retrieval. Cap spend per job with `max_credits`. See
[api_reference.md](references/api_reference.md) for `batch_submit_workflow` /
`batch_poll_status` and [proteins_and_organization.md](references/proteins_and_organization.md)
for `create_folder` / `create_project`.

## Failure Modes and Edge Cases

- **Invalid SMILES** — `stjames.Molecule.from_smiles` / `Chem.MolFromSmiles` may
  raise or return `None`; validate before submitting. RDKit-native `batch_*`
  functions return `None` per failed molecule, so guard every element.
- **Wrong charge/multiplicity** — `stjames.Molecule` runs an electron sanity check
  and raises `ValueError` on inconsistent spin (e.g. singlet O₂). Set `charge` and
  `multiplicity` explicitly for ions and radicals.
- **Timeouts** — pass a `timeout` to `wait_for_result`; on `TimeoutError` the job
  may still be running server-side (retrieve later by UUID), it is not cancelled.
- **API/auth/rate errors** — wrap submission in `try/except` for
  `rowan.RowanAPIError`, `AuthenticationError`, and `RateLimitError`
  (`.retry_after`); see [api_reference.md](references/api_reference.md).
- **Low-confidence predictions** — cofolding `ptm_score`/`interface_ptm` below ~0.5
  are unreliable; docking scores > 0 or ligand strain > ~3 kcal/mol signal a poor
  pose. Interpretation thresholds live in
  [results_interpretation.md](references/results_interpretation.md).
- **Credit exhaustion** — check `rowan.whoami().credits` before large batches and
  set `max_credits` so a runaway job fails instead of draining the account.

## Related Tools

For the cheminformatics steps around Rowan (SMILES parsing, descriptors, 3D
embedding, filtering) use the `rdkit` library directly — it is the input/output
currency for the RDKit-native helpers and complements every workflow here.

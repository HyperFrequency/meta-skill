# Rowan Client API Reference

The `rowan` client exposes typed classes plus submission, retrieval, batch, and
utility functions. Signatures below reflect the documented v2 Python API; treat
defaults as the shipped behavior and override via keyword arguments.

## `Workflow` — a submitted job handle

Returned by every `submit_*` function. Compute runs server-side; the object is a
handle, not the result.

| Attribute | Type | Meaning |
|---|---|---|
| `uuid` | str | Unique job id |
| `name` | str | User label |
| `status` | str | `pending` / `running` / `completed` / `failed` / `stopped` |
| `created_at` / `completed_at` | datetime | Timestamps (`completed_at` is `None` until done) |
| `credits_charged` | float | Credits consumed |
| `workflow_type` | str | Calculation type |
| `folder_uuid` | str | Parent folder |
| `data` | dict | Results — **lazy**, empty until `fetch_latest()` |

### Lifecycle methods

```python
wf.get_status()                 # refresh status only
wf.is_finished()                # bool
wf.wait_for_result(timeout=3600)  # block until terminal state (seconds)
wf.fetch_latest(in_place=True)  # load results into wf.data
wf.stop()                       # cancel a running job
```

`data` is not downloaded automatically (results can be large). The canonical order
is `wait_for_result()` → `fetch_latest(in_place=True)` → read `wf.data`.

### Metadata, deletion, downloads

```python
wf.update(name="…", notes="…", starred=True)
wf.delete()                              # remove workflow entirely
wf.delete_data()                         # drop results, keep metadata
wf.download_sdf_file("poses.sdf")        # structures/poses
wf.download_dcd_files(output_dir="traj/")  # MD trajectories
```

## Submission functions

### Generic

```python
rowan.submit_workflow(
    name: str,
    initial_molecule: stjames.Molecule,
    workflow_type: str,        # "pka", "optimization", "conformer_search", …
    workflow_data: dict = {},  # workflow-specific parameters
    folder_uuid: str = None,
    max_credits: float = None,
) -> Workflow
```

Use `submit_workflow` for types without a dedicated helper (`hydrogen_bond_basicity`,
`spin_states`, `admet`, `multistage_optimization`, `strain`, `orbitals`,
`pose_analysis_md`, `protein_binder_design`). See
[workflow_catalogue.md](workflow_catalogue.md) for each type's `workflow_data`.

### Typed helpers

Every helper accepts the common trio `name=None, folder_uuid=None, max_credits=None`
and returns a `Workflow`. Property and modeling helpers additionally take
`initial_molecule`:

- **Property:** `submit_pka_workflow`, `submit_redox_potential_workflow`,
  `submit_solubility_workflow`, `submit_fukui_workflow`,
  `submit_bde_workflow(..., bond_indices=(i, j))`.
- **Modeling:** `submit_basic_calculation_workflow(..., workflow_type="optimization"
  | "single_point" | "frequency")`, `submit_conformer_search_workflow`,
  `submit_tautomer_search_workflow`,
  `submit_dihedral_scan_workflow(..., dihedral_indices=(a,b,c,d))`,
  `submit_ts_search_workflow`.
- **Spectroscopy:** `submit_nmr_workflow`, `submit_ion_mobility_workflow`,
  `submit_descriptors_workflow`.

### Protein-ligand helpers

```python
rowan.submit_docking_workflow(
    protein: str,            # protein UUID
    pocket: dict,            # {"center": [x,y,z], "size": [dx,dy,dz]}
    initial_molecule: stjames.Molecule,
    executable="vina",       # "vina" | "qvina2"
    scoring_function="vinardo",  # "vina" | "vinardo"
    exhaustiveness=8,
    do_csearch=True, do_optimization=True, do_pose_refinement=True,
    name=None, folder_uuid=None, max_credits=None,
) -> Workflow

rowan.submit_batch_docking_workflow(
    protein, pocket, smiles_list,          # list[str] of SMILES
    executable="qvina2", scoring_function="vina", …
) -> Workflow

rowan.submit_protein_cofolding_workflow(
    initial_protein_sequences: list,       # amino-acid sequences
    initial_smiles_list: list = None,      # optional ligands
    ligand_binding_affinity_index=None,
    use_msa_server=False, use_potentials=True,
    compute_strain=False, do_pose_refinement=False,
    model="boltz_2",                       # "boltz_1x" | "boltz_2" | "chai_1r"
    name=None, folder_uuid=None, max_credits=None,
) -> Workflow
```

## Retrieval

```python
rowan.retrieve_workflow(uuid) -> Workflow
rowan.retrieve_workflows(uuids: list) -> list[Workflow]
rowan.list_workflows(
    name=None, status=None, workflow_type=None,
    starred=None, folder_uuid=None, page=1, size=20,
) -> list[Workflow]
```

## Batch operations

```python
rowan.batch_submit_workflow(
    molecules: list, workflow_type: str,
    workflow_data={}, folder_uuid=None, max_credits=None,
) -> list[Workflow]

rowan.batch_poll_status(uuids: list) -> dict   # {uuid: status}
```

Poll-until-done pattern:

```python
import time
wfs = rowan.batch_submit_workflow(molecules, "pka")
while not all(s in ("completed", "failed")
              for s in rowan.batch_poll_status([w.uuid for w in wfs]).values()):
    time.sleep(10)
for w in wfs:
    w.fetch_latest(in_place=True)
```

## Utilities

```python
rowan.whoami() -> User                     # .username .email .credits .weekly_credits
rowan.smiles_to_stjames(smiles) -> stjames.Molecule
rowan.molecule_lookup("aspirin") -> str    # common name → SMILES
rowan.get_api_key() -> str
rowan.api_client() -> httpx.Client         # low-level escape hatch
```

## Error handling

```python
try:
    wf = rowan.submit_pka_workflow(mol, name="test")
    wf.wait_for_result(timeout=3600)
except rowan.AuthenticationError as e:   # bad/missing key
    ...
except rowan.RateLimitError as e:        # e.retry_after seconds
    ...
except rowan.RowanAPIError as e:         # generic API failure
    ...
except TimeoutError:                     # job may still run server-side
    ...
```

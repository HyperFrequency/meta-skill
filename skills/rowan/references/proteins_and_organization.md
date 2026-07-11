# Proteins, Folders, and Projects

Docking and cofolding need a protein on the server; large campaigns need folders and
projects to stay navigable. This covers both.

## Proteins

A `Protein` has `uuid`, `name`, `data` (PDB text, lazy-loaded), `sanitized` (bool),
`public`, and `created_at`.

### Get a protein onto Rowan

```python
import rowan
protein = rowan.upload_protein(name="EGFR Kinase", file_path="protein.pdb")
protein = rowan.create_protein_from_pdb_id(name="EGFR (1M17)", code="1M17")  # fetch from RCSB
```

### Retrieve, list, download

```python
rowan.retrieve_protein(uuid)
rowan.list_proteins(name="EGFR")     # name filter optional
protein.refresh()                    # load PDB text if not present
protein.download_pdb_file("out.pdb")
pdb_text = protein.data
```

### Sanitize before docking

```python
protein.sanitize()   # then check protein.sanitized
```

Sanitization removes non-protein molecules (waters, ligands, ions), fills missing
residue atoms, resolves alternate conformations, and standardizes residue names.
Dock against a sanitized structure — raw crystallographic PDBs often contain
artifacts that distort the pocket.

### Metadata, pocket, deletion

```python
protein.update(name="EGFR Kinase Domain")
protein.update(pocket={"center": [10.0, 20.0, 30.0], "size": [20.0, 20.0, 20.0]})
protein.delete()
```

Upload a protein **once** and reuse its `uuid` across every ligand in a screen —
re-uploading per ligand wastes time and clutters the workspace.

## Folders

`Folder`: `uuid`, `name`, `parent_uuid` (`None` at root), `starred`, `public`,
`created_at`.

```python
folder = rowan.create_folder(name="Drug Discovery Project")
sub    = rowan.create_folder(name="Lead Compounds", parent_uuid=folder.uuid)

rowan.retrieve_folder(uuid)
rowan.list_folders(name="Project", starred=True)
folder.update(name="…", parent_uuid="…", starred=True)   # rename / move / star
rowan.print_folder_tree(root_uuid=folder.uuid)           # visualize hierarchy
folder.delete()   # WARNING: removes all workflows inside
```

Attach a workflow to a folder at submission time and list a folder's contents:

```python
rowan.submit_pka_workflow(mol, name="Ethanol pKa", folder_uuid=folder.uuid)
rowan.list_workflows(folder_uuid=folder.uuid)
```

## Projects

Top-level containers holding folders and workflows: `uuid`, `name`, `created_at`.

```python
project = rowan.create_project(name="Cancer Drug Discovery")
rowan.retrieve_project(uuid); rowan.list_projects(); rowan.default_project()
project.update(name="…")
project.delete()   # WARNING: deletes all folders and workflows within
folder = rowan.create_folder(name="Phase 1", project_uuid=project.uuid)
```

## Campaign layout example

```python
project = rowan.create_project("EGFR Inhibitor Campaign")
hits = rowan.create_folder("Hit Finding", project_uuid=project.uuid)

protein = rowan.create_protein_from_pdb_id("EGFR", "1M17")
protein.sanitize()
pocket = {"center": [10.0, 20.0, 30.0], "size": [20.0, 20.0, 20.0]}

for smi in hit_compounds:
    rowan.submit_docking_workflow(
        protein=protein.uuid, pocket=pocket,
        initial_molecule=stjames.Molecule.from_smiles(smi),
        name=f"Dock: {smi[:20]}", folder_uuid=hits.uuid,
    )
```

## Housekeeping

- **Credits:** check `rowan.whoami().credits` before large batches; pass
  `max_credits=…` per job so overruns fail instead of draining the account.
- **Naming:** encode date/phase/target in folder names
  (`20260710_Lead_Optimization`, `EGFR_Conformer_Search`) for later filtering.
- **Cleanup:** `wf.delete_data()` frees result storage while keeping metadata;
  `wf.delete()` removes the workflow entirely.

# DiffDock Workflows and Examples

Practical recipes. For every flag, see `parameters.md`; for confidence and scope,
see `confidence-and-limitations.md`.

## Installation

**Conda (recommended):**

```bash
git clone https://github.com/gcorso/DiffDock.git
cd DiffDock
conda env create --file environment.yml
conda activate diffdock
```

**Docker:**

```bash
docker pull rbgcsail/diffdock
docker run -it --gpus all --entrypoint /bin/bash rbgcsail/diffdock
micromamba activate diffdock
```

Notes: a GPU gives a 10–100× speedup over CPU and is effectively required for
real use. The first run pre-computes SO(2)/SO(3) lookup tables (~2–5 min);
later runs start immediately. Model checkpoints (~500 MB) download automatically.

## 1. Single protein–ligand docking

```bash
python -m inference \
  --config default_inference_args.yaml \
  --protein_path protein.pdb \
  --ligand "COc1ccc(C(=O)Nc2ccccc2)cc1" \
  --out_dir results/single/
```

Output: `results/single/rank1.sdf … rank10.sdf`, ordered by descending
confidence with the confidence value in each filename. `rank1` is the best guess.

## 2. Dock from a sequence (no PDB) via ESMFold

```bash
python -m inference \
  --config default_inference_args.yaml \
  --protein_sequence "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQ..." \
  --ligand "CC(C)Cc1ccc(cc1)C(C)C(=O)O" \
  --out_dir results/seq/
```

Use when no experimental structure exists, or to model a mutant/variant. ESMFold
folding adds ~30 s–5 min depending on sequence length.

## 3. Batch docking

Build a CSV with columns `complex_name,protein_path,ligand_description,protein_sequence`
(see `parameters.md` for the schema), then:

```bash
python -m inference \
  --config default_inference_args.yaml \
  --protein_ligand_csv complexes.csv \
  --out_dir results/batch/ \
  --batch_size 10
```

Each complex gets its own subdirectory `results/batch/<complex_name>/rank1.sdf …`.
Validate the CSV before launching a long run: confirm every `protein_path` exists,
every SMILES parses in RDKit (`Chem.MolFromSmiles`), and each row uses exactly
one of `protein_path` / `protein_sequence`.

## 4. High-throughput virtual screening

For one target against many ligands, reuse the protein embedding to avoid
re-embedding it per ligand.

Build the screening CSV (one target PDB repeated, one row per ligand SMILES):

```python
import pandas as pd
ligands = pd.read_csv("ligand_library.csv")  # column: smiles
pd.DataFrame({
    "complex_name": [f"screen_{i}" for i in range(len(ligands))],
    "protein_path": ["target.pdb"] * len(ligands),
    "ligand_description": ligands["smiles"].tolist(),
    "protein_sequence": [""] * len(ligands),
}).to_csv("screening_input.csv", index=False)
```

Pre-compute embeddings once, then dock the whole library:

```bash
python datasets/esm_embedding_preparation.py \
  --protein_ligand_csv screening_input.csv \
  --out_file protein_embeddings.pt

python -m inference \
  --config default_inference_args.yaml \
  --protein_ligand_csv screening_input.csv \
  --esm_embeddings_path protein_embeddings.pt \
  --out_dir results/screen/ \
  --batch_size 32
```

Rank hits by each complex's best pose confidence:

```python
import os, pandas as pd, glob, re
rows = []
for d in glob.glob("results/screen/*/"):
    # confidence is encoded in each pose filename, e.g. rank1_confidence-0.42.sdf
    scores = [float(re.search(r"confidence(-?[\d.]+)", os.path.basename(f)).group(1))
              for f in glob.glob(os.path.join(d, "rank*_confidence*"))]
    if scores:
        rows.append({"complex": os.path.basename(d.rstrip("/")), "top_confidence": max(scores)})
pd.DataFrame(rows).sort_values("top_confidence", ascending=False).to_csv("top_hits.csv", index=False)
```

Confidence ranks pose *certainty*, not affinity — carry the top N hits into an
affinity rescore (see section 6 and `binding-affinity`).

## 5. Ensemble docking (protein flexibility)

Dock the same ligand into several protein conformations (crystal structures or MD
snapshots) to account for receptor flexibility. Put each conformation on its own
CSV row with the same ligand, then run with more samples per conformation:

```bash
python -m inference \
  --config default_inference_args.yaml \
  --protein_ligand_csv ensemble_input.csv \
  --samples_per_complex 20 \
  --out_dir results/ensemble/
```

## 6. Rescore poses for affinity

DiffDock gives poses; affinity needs a scoring step.

```bash
# GNINA (fast NN scoring) over every DiffDock pose
for pose in results/single/rank*.sdf; do
  gnina -r protein.pdb -l "$pose" --score_only
done
```

Then, in increasing accuracy/cost: MM/GBSA (MMPBSA.py, gmx_MMPBSA after a short
energy minimization) and alchemical free-energy methods (FEP/TI via OpenMM+OpenFE
or GROMACS). Recommended chain: DiffDock poses → visual check → GNINA/MM-GBSA
rescore → experimental assay. The `binding-affinity` skill packages the rescoring
step.

## 7. Run on a cloud GPU (optional, via Modal)

When no local GPU is available, run inference on an on-demand cloud GPU. This uses
the public `rbgcsail/diffdock` image; it needs a Modal account and credentials in
your own environment. **Always estimate and confirm cost before launching a GPU
job.**

```python
import modal

app = modal.App("diffdock")
image = modal.Image.from_registry("rbgcsail/diffdock").pip_install("rdkit-pypi", "pandas", "biopython")
vol = modal.Volume.from_name("diffdock-results", create_if_missing=True)

@app.function(image=image, gpu="A10G", timeout=3600, volumes={"/results": vol})
def dock(protein_path: str, ligand_smiles: str, samples: int = 10):
    import subprocess
    r = subprocess.run(
        ["python", "-m", "inference", "--config", "default_inference_args.yaml",
         "--protein_path", protein_path, "--ligand", ligand_smiles,
         "--samples_per_complex", str(samples), "--out_dir", "/results/out/"],
        capture_output=True, text=True)
    vol.commit()
    return {"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}
```

GPU sizing and rough cost (order-of-magnitude, verify against current pricing):

| Scenario | GPU | Approx. time / cost |
|----------|-----|---------------------|
| 1 complex | T4 / A10G (16–24 GB) | ~2–5 min |
| Batch < 50 | A10G (24 GB) | ~30–60 min |
| Screen ~1000 | A100 40 GB | several hours |
| Very large + embeddings | A100 80 GB | scales with library size |

## 8. Interactive GUI

```bash
python app/main.py     # then open http://localhost:7860
```

Or the hosted demo (no install): https://huggingface.co/spaces/reginabarzilaygroup/DiffDock-Web

## Best-practice checklist

1. Test one complex before launching a batch.
2. Use a GPU; pre-compute ESM embeddings when reusing a protein.
3. Generate 10–40 samples; raise for hard cases.
4. Prepare the protein (fill missing residues, drop distant waters, set
   protonation) and pass canonical SMILES (`rdkit`) for ligands.
5. Rank by confidence for triage only — visually inspect and rescore before
   committing to a pose.
6. Record the parameters used for reproducibility.
</content>

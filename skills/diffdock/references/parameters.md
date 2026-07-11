# DiffDock Parameter Reference

Full command-line / config reference for `python -m inference`. Every flag below
can also be set in a YAML config (typically `default_inference_args.yaml`);
command-line arguments override config-file values. Defaults reflect the
DiffDock-L (`v1.1`) model, which is the current default checkpoint.

```bash
python -m inference --config default_inference_args.yaml --samples_per_complex 20
```

## Input specification

| Flag | Meaning |
|------|---------|
| `--protein_path FILE` | Protein structure as a PDB file. Mutually exclusive with `--protein_sequence`. |
| `--protein_sequence SEQ` | Amino-acid sequence; folded with ESMFold before docking (adds ~30 s–5 min). |
| `--ligand SPEC` | Ligand as a SMILES string (`"COc1ccc(C#N)cc1"`) or a structure file (`.sdf`, `.mol2`, anything RDKit reads). |
| `--protein_ligand_csv FILE` | Batch input CSV (see below). Overrides the single-complex flags. |

### Batch CSV columns

Required columns (leave the unused side empty per row):

| Column | Meaning |
|--------|---------|
| `complex_name` | Unique identifier; names the per-complex output subdirectory. |
| `protein_path` | Path to a PDB file. Empty when using a sequence. |
| `ligand_description` | SMILES string or path to a ligand file. |
| `protein_sequence` | Amino-acid sequence. Empty when using a PDB file. |

```csv
complex_name,protein_path,ligand_description,protein_sequence
cplx1,protein1.pdb,CC(=O)Oc1ccccc1C(=O)O,
cplx2,,COc1ccc(C#N)cc1,MSKGEELFTGVVPILVELDGDVNGHKF...
cplx3,protein3.pdb,ligand3.sdf,
```

## Output control

| Flag | Meaning |
|------|---------|
| `--out_dir DIR` | Output directory. Poses are written per complex as ranked SDFs `rank1.sdf`, `rank2.sdf`, … ordered by descending confidence, with the confidence value encoded in each filename. `rank1` is the model's best guess. |
| `--save_visualisation` | Also export reverse-diffusion trajectory frames for visualization. |

## Sampling

| Flag | Default | Meaning |
|------|---------|---------|
| `--samples_per_complex` | 10 | Poses generated per complex. Raise to 20–40 for hard cases (large/flexible ligands, ambiguous pockets); more samples = better coverage, longer runtime. |
| `--inference_steps` | 20 | Planned reverse-diffusion steps. 25–30 can improve accuracy at higher cost. |
| `--actual_steps` | 19 | Steps actually executed. |
| `--no_final_step_noise` | true | Omit noise injection on the final denoising step. |
| `--sigma_schedule` | expbeta | Noise schedule (exponential-beta). |
| `--initial_noise_std_proportion` | 1.46 | Initial noise standard-deviation scaling. |

## Temperature parameters (diversity control)

Three coupled degrees of freedom — translation (`tr`), rotation (`rot`), torsion
(`tor`) — each with a sampling temperature, a psi temperature, and a data-sigma
scale. Higher temperature = more diverse poses.

| Flag | Default | Flag | Default | Flag | Default |
|------|---------|------|---------|------|---------|
| `--temp_sampling_tr` | 1.17 | `--temp_psi_tr` | 0.73 | `--temp_sigma_data_tr` | 0.93 |
| `--temp_sampling_rot` | 2.06 | `--temp_psi_rot` | 0.90 | `--temp_sigma_data_rot` | 0.75 |
| `--temp_sampling_tor` | 7.04 | `--temp_psi_tor` | 0.59 | `--temp_sigma_data_tor` | 0.69 |

Practical knob: `--temp_sampling_tor` governs conformational spread. Raise it
(8–10) for flexible ligands with many rotatable bonds; lower it (5–6) for rigid
ligands.

## Performance

| Flag | Default | Meaning |
|------|---------|---------|
| `--batch_size` | 10 | Complexes processed together. Lower it (e.g. 2) on GPU out-of-memory; raise it (e.g. 32) for throughput on large-VRAM GPUs. |
| `--esm_embeddings_path FILE` | — | Pre-computed ESM2 protein embeddings; skips re-embedding when reusing a protein across many ligands (see `workflows.md`). |
| `--chain_cutoff N` | — | Cap on protein chains processed; useful for large multi-chain complexes. |
| `--tqdm` | — | Progress bar for long jobs. |
| `--limit_failures N` | 5 | Abort after this many per-complex failures in a batch. |

## Model / checkpoint selection

| Flag | Default | Meaning |
|------|---------|---------|
| `--model_dir DIR` | `./workdir/v1.1/score_model` | Score-model checkpoint directory. |
| `--confidence_model_dir DIR` | `./workdir/v1.1/confidence_model` | Confidence-model checkpoint directory. |
| `--ckpt NAME` | `best_ema_inference_epoch_model.pt` | Score-model checkpoint file. |
| `--confidence_ckpt NAME` | `best_model_epoch75.pt` | Confidence-model checkpoint file. |
| `--old_score_model` | false | Use the original DiffDock score model instead of DiffDock-L. |

Checkpoints (~500 MB) download automatically on first run if absent.

## Alternative sampling / debugging

| Flag | Default | Meaning |
|------|---------|---------|
| `--ode` | false | Deterministic ODE solver instead of the stochastic (SDE) sampler. |
| `--different_schedules` | false | Use distinct noise schedules per degree of freedom. |
| `--no_random` | false | Disable randomization for reproducibility testing. |
| `--no_model` | false | Skip model inference (plumbing/debug). |
</content>
</invoke>

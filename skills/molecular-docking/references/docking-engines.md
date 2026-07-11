# Docking Engines: AutoDock Vina and DiffDock

Two complementary engines. **Vina** is fast, physics-based, and needs a search
box; **DiffDock** is a diffusion model that docks blind (no box) but returns a
pose plus a confidence score rather than an energy.

## AutoDock Vina (Python API)

```python
from vina import Vina

v = Vina(sf_name="vina")                 # scoring: "vina" | "vinardo" | "ad4"
v.set_receptor("receptor.pdbqt")         # rigid receptor
# optional flexible side chains: v.set_receptor("rigid.pdbqt", "flex.pdbqt")
v.set_ligand_from_file("ligand.pdbqt")   # or set_ligand_from_string(pdbqt_str)

v.compute_vina_maps(center=[cx, cy, cz], box_size=[sx, sy, sz], spacing=0.375)
v.dock(exhaustiveness=32, n_poses=20)
v.write_poses("poses.pdbqt", n_poses=10, overwrite=True, energy_range=3.0)

energies = v.energies()   # ndarray, one row per pose: [total, inter, intra, ...] kcal/mol
```

Useful single-pose operations (for rescoring / refinement, not full search):

- `v.score()` — score the currently loaded pose without searching.
- `v.optimize()` — local energy minimization of the current pose.
- `v.randomize()` — random valid starting pose.

**AD4 scoring** requires precomputed affinity maps (`autogrid4`) rather than
`compute_vina_maps`; `vina` and `vinardo` compute maps on the fly.

### CLI equivalent

```bash
vina --receptor receptor.pdbqt --ligand ligand.pdbqt \
     --center_x 10 --center_y 20 --center_z 15 \
     --size_x 20 --size_y 20 --size_z 20 \
     --exhaustiveness 32 --num_modes 20 --out poses.pdbqt
```

### Search box placement

- **Center** on the pocket: co-crystal ligand centroid (best), cavity-detection
  center, or the centroid of known active-site residues. See
  `references/pocket-detection.md`.
- **Size**: cover the ligand's longest dimension plus ~8–10 Å of padding. Keep
  the box reasonably tight — very large boxes dilute the search and degrade
  ranking. Vina warns above ~27,000 Å³ (e.g. 30×30×30); split or raise
  exhaustiveness if you must go larger.
- **Blind docking** (site unknown): a whole-protein box with high exhaustiveness
  works but is slow and less accurate — prefer DiffDock for truly blind cases.

### Exhaustiveness

Search effort, roughly linear in runtime:

| Value | Use |
|---|---|
| 8 (default) | Quick look, well-defined small pocket |
| 16–32 | Production single docking and virtual screening |
| 32–64 | Large box, flexible ligand, blind/hard target |

Run 2–3 replicates on important targets; Vina is stochastic and top-pose energy
varies run to run.

### Flexible side chains

Vina can treat chosen receptor residues as flexible via a separate flex PDBQT
(Meeko `mk_prepare_receptor.py -f <resnums>`). This helps induced-fit pockets but
multiplies cost and can over-fit — flex only 1–4 well-motivated residues.

### Scoring function choice

- **vina** — general default, empirical + knowledge-based terms.
- **vinardo** — reparameterized, often better pose ranking on diverse sets.
- **ad4** — classic AutoDock4 forcefield; needs autogrid maps.

None of these is a true binding free energy; treat scores as a **ranking** signal
(see `references/interaction-analysis.md`). For ΔG use sibling `binding-affinity`.

## DiffDock (deep-learning, blind)

Diffusion generative model over ligand pose (translation, rotation, torsions).
No box required — it takes the receptor and a ligand and proposes poses ranked by
a learned **confidence model**. Separate repo (`gcorso/DiffDock`, MIT); needs
PyTorch, PyTorch Geometric, and a GPU for reasonable throughput.

Typical invocation (flags mirror the repo's inference script — confirm against the
version you installed):

```bash
python -m inference \
  --config default_inference_args.yaml \
  --protein_path receptor.pdb \
  --ligand "CC(=O)Oc1ccccc1C(=O)O" \
  --out_dir diffdock_out \
  --samples_per_complex 40
```

Inputs: protein as PDB (no PDBQT / no box), ligand as SMILES or SDF. Output:
ranked pose SDFs plus a confidence score per pose.

**Confidence bands** (guidance, not calibrated affinity):

| Confidence | Interpretation |
|---|---|
| > 0 | Confident pose |
| 0 to −1.5 | Moderate — inspect and rescore |
| < −1.5 | Low confidence — treat skeptically |

DiffDock does not output an interaction energy, so **rescore** its top poses with
Vina `score()` or a ProLIF fingerprint before ranking across compounds. For the
full DiffDock configuration surface, use sibling `diffdock`.

## Choosing and combining engines

| Situation | Engine |
|---|---|
| Known pocket, need a comparable energy score | Vina |
| Unknown / cryptic site, or no reliable box | DiffDock (blind) |
| Large virtual screen, CPU only | Vina |
| Best of both | DiffDock pose → Vina `score`/`optimize` rescore |

**Sort direction matters:** Vina energies are better when **more negative**;
DiffDock confidence is better when **higher**. When merging results into one
ranking, normalize each engine's score separately before combining.

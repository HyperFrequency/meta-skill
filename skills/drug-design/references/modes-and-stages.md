# Modes, Stages, and I/O Contracts

Full reference for the five workflow modes: the stage chain each one runs, the
sibling skill that owns each stage, the file that crosses each stage boundary,
and the JSON schemas the orchestrator validates between stages.

Each row lists the **owning sibling skill** rather than a hardcoded script name —
call that skill for the stage. The "output" column is the artifact the next stage
consumes.

---

## Mode: `full` — target → drug candidates

The complete SBDD campaign. Input is either a PDB structure or a bare sequence
(which triggers structure prediction first).

| # | Stage | Owning skill | Input | Output |
|---|-------|--------------|-------|--------|
| 1 | Structure prediction (only if `--sequence`) | `structure-prediction` | sequence | `predicted_structure.pdb` |
| 2 | Pocket detection | `pocket-detection` | PDB | `pockets.json` |
| 3 | Druggability | `pocket-detection` | PDB + `pockets.json` | `druggability.json` |
| 4 | De novo design (SBDD) | `denovo-design` | PDB + `pockets.json` | `candidates.sdf` |
| 5 | Drug-likeness filter | `denovo-design` | `candidates.sdf` | `filtered.sdf` |
| 6 | Docking | `molecular-docking` | PDB + `filtered.sdf` | `docking/poses.sdf` |
| 7 | Interaction scoring | `molecular-docking` | PDB + poses | `interactions.json` |
| 8 | Affinity prediction | `binding-affinity` | PDB + poses | `affinity.json` |
| 9 | MM/GBSA rescore | `binding-affinity` | PDB + poses | `mmgbsa.json` |
| 10 | Consensus ranking | `binding-affinity` | all score files | `consensus.json` |
| 11 | 3D visualization *(non-fatal)* | `molecule-visualization` | PDB + poses | `complex_3d.html` |

Filter stage typically applies `lipinski,pains,brenk`. Carry `--top-n × 5`
candidates into generation so the filter has room to cut.

---

## Mode: `lead-opt` — improve an existing hit

Requires `--protein` **and** `--ligand` (the hit). Generates analogs of the hit
and re-ranks them against the target.

| # | Stage | Owning skill | Input | Output |
|---|-------|--------------|-------|--------|
| 1 | Analog generation | `denovo-design` | hit `.sdf` | `analogs.sdf` |
| 2 | Drug-likeness filter | `denovo-design` | `analogs.sdf` | `filtered.sdf` |
| 3 | Docking | `molecular-docking` | PDB + `filtered.sdf` | `docking/poses.sdf` |
| 4 | Affinity prediction | `binding-affinity` | PDB + poses | `affinity.json` |
| 5 | Consensus ranking | `binding-affinity` | `affinity.json` | `consensus.json` |

Filter here is usually lighter (`lipinski,pains`) to keep close analogs of the
parent hit.

---

## Mode: `screen` — rank a compound library

Requires `--protein` **and** `--library`. Fast batch score first, then dock only
the top hits (docking is the expensive stage — never dock the whole library).

| # | Stage | Owning skill | Input | Output |
|---|-------|--------------|-------|--------|
| 1 | Pocket detection | `pocket-detection` | PDB | `pockets.json` |
| 2 | Batch scoring | `binding-affinity` | PDB + library | `screening_hits.csv` |
| 3 | Docking (top hits) | `molecular-docking` | PDB + hits | `docking/poses.sdf` |
| 4 | Affinity prediction | `binding-affinity` | PDB + poses | `affinity.json` |
| 5 | Consensus ranking | `binding-affinity` | `affinity.json` | `consensus.json` |

`--top-n` controls how many library compounds survive batch scoring into docking.

---

## Mode: `assess` — is this target druggable?

Requires `--protein` **or** `--sequence`. No molecules — just a druggability
verdict plus a visual report. Visualization stages are non-fatal.

| # | Stage | Owning skill | Input | Output |
|---|-------|--------------|-------|--------|
| 1 | Structure prediction (if `--sequence`) | `structure-prediction` | sequence | `predicted_structure.pdb` |
| 2 | Pocket detection | `pocket-detection` | PDB | `pockets.json` |
| 3 | Druggability | `pocket-detection` | PDB + `pockets.json` | `druggability.json` |
| 4 | Pocket summary plot *(non-fatal)* | `pocket-detection` | PDB + `druggability.json` | `pocket_summary.png` |
| 5 | Druggability radar *(non-fatal)* | `pocket-detection` | PDB + `druggability.json` | `druggability_radar.png` |
| 6 | 3D view *(non-fatal)* | `molecule-visualization` | PDB | `protein_3d.html` |

---

## Mode: `denovo` — generate novel molecules for a pocket

Requires `--protein` (or a pre-computed `--pocket`). Runs two complementary
generators (structure-based and fragment-growing), then docks and ranks.

| # | Stage | Owning skill | Input | Output |
|---|-------|--------------|-------|--------|
| 1 | Pocket detection | `pocket-detection` | PDB | `pockets.json` |
| 2 | SBDD generation | `denovo-design` | PDB + `pockets.json` | `candidates_sbdd.sdf` |
| 3 | Fragment generation (grow) | `denovo-design` | PDB + `pockets.json` | `candidates_frag.sdf` |
| 4 | Drug-likeness filter | `denovo-design` | candidates | `filtered.sdf` |
| 5 | Docking | `molecular-docking` | PDB + `filtered.sdf` | `docking/poses.sdf` |
| 6 | Affinity prediction | `binding-affinity` | PDB + poses | `affinity.json` |
| 7 | Consensus ranking | `binding-affinity` | `affinity.json` | `consensus.json` |

---

## Inter-stage I/O Contracts

Validate these shapes **before** passing a file downstream. A malformed field
here is the most common silent pipeline failure. Treat the schemas below as the
contract the orchestrator enforces between stages; if a sibling skill emits extra
fields that is fine, but the required fields must be present and well-typed.

### `pockets.json` — pocket-detection → docking / druggability / de novo

```json
{
  "pockets": [
    {
      "center": [10.5, 22.3, 15.0],
      "volume_A3": 542.8,
      "residues": ["ASP189", "SER195"]
    }
  ]
}
```

**Critical:** `pockets[0].center` must be exactly `[float, float, float]` — the
docking stage reads it as the search-box center. Reject an empty `pockets` array
or a `center` that is not length-3.

### `druggability.json` — pocket-detection druggability → assess report

Same `pockets` array, each pocket additionally carrying a `druggability_score`.
Reject if the first pocket is missing that field.

### `affinity.json` — binding-affinity → consensus

```json
{
  "predictions": [
    {
      "pose_id": 1,
      "predicted_pKd": 7.2,
      "predicted_dG_kcal": -9.8,
      "confidence": "moderate"
    }
  ]
}
```

Require the `predictions` array. Downstream ranking keys on `pose_id`.

### `consensus.json` — final ranked output

```json
{
  "rankings": [
    {
      "pose_id": 1,
      "consensus_score": 0.85,
      "consensus_rank": 1,
      "individual_ranks": {"affinity": 1, "rescore": 2}
    }
  ]
}
```

Require the `rankings` array. This is the artifact the campaign delivers.

---

## Output Directory Layout (`full` mode)

```
pipeline_results/
├── pockets.json              # detected binding pockets
├── druggability.json         # pocket druggability scores
├── candidates.sdf            # generated molecules (pre-filter)
├── filtered.sdf              # drug-like molecules (post-filter)
├── docking/
│   ├── poses.sdf             # docked poses
│   └── scores.csv            # per-pose docking scores
├── interactions.json         # protein-ligand interactions
├── affinity.json             # binding-affinity predictions
├── mmgbsa.json               # MM/GBSA rescoring
├── consensus.json            # FINAL consensus ranking
├── complex_3d.html           # interactive 3D viewer
├── pipeline_report.json      # per-stage status + timings
└── _manifest.jsonl           # full invocation log (for review/replay)
```

Other modes write the subset of files their stages produce. Always place outputs
under a single run directory so the manifest and report describe one coherent run.

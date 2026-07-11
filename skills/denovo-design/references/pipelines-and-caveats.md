# Pipelines & Caveats

End-to-end recipes, method limitations, and troubleshooting for the de novo
design scripts. See [cli-reference.md](cli-reference.md) for exact flags.

## Recommended end-to-end pipeline

Generate broadly, triage hard, then optimize the survivors.

```bash
# 1. Generate analogs of a lead across all strategies
python scripts/generate_analogs.py \
  --smiles "c1ccc(NC(=O)c2ccccc2)cc1" \
  --output analogs.csv --num 200 --strategy all

# 2. Annotate with medchem filters
python scripts/filter.py --input analogs.csv --output annotated.csv \
  --filters lipinski,veber,qed,pains,brenk,sa

# 3. Keep only rows that pass every filter (filter.py does NOT drop rows)
#    e.g. with pandas:
python -c "import pandas as pd; d=pd.read_csv('annotated.csv'); \
  d[d.pass_all=='pass'].to_csv('survivors.csv', index=False); \
  print(len(d), '->', (d.pass_all=='pass').sum())"

# 4. Optimize survivors toward property targets under hard constraints
python scripts/optimize.py --input survivors.csv \
  --objectives qed,logp,sa --constraints "mw<500,logp<5,qed>0.5" \
  --output optimized.csv --num-iterations 4 --top-k 25
```

## Fragment-based drug discovery (FBDD)

If you have several fragment hits, **merge** often produces stronger leads than
grow/link because it retains pharmacophoric features from both fragments.

```bash
# Merge pharmacophores of two fragment hits
python scripts/generate_fragments.py \
  --fragments "hits.smi" --mode merge --output merged.csv --num 100

# Then filter and optimize as in the pipeline above
```

`--fragments` accepts a file: one SMILES per line, `#` comments allowed, and the
first column of a CSV-like line is taken as the SMILES.

## Structure-based design → medchem

SBDD output is a starting pool, not final leads. Always pass it through filtering
and optimization, and confirm hits with real docking / `binding-affinity`.

```bash
python scripts/generate_sbdd.py --protein target.pdb \
  --pocket-residues "ASP189,SER195,HIS57" --method pharmacophore \
  --output sbdd_hits.csv --num 150

python scripts/filter.py --input sbdd_hits.csv --output sbdd_clean.csv \
  --filters lipinski,pains,brenk,sa
```

`--pocket-residues auto` estimates the pocket from the structure centroid; prefer
naming the catalytic/binding residues explicitly for a meaningful pharmacophore.

## Method limitations (read before trusting output)

- **These are heuristics, not generative ML.** Molecules are built by bonding a
  library group onto a matched atom, then RDKit re-sanitizes valence. Products are
  valid SMILES but can be strained, non-synthesizable, or medicinally odd. Manual
  review is mandatory.
- **`sa_score` is a proxy**, not a synthesis planner or the standard
  Ertl–Schuffenhauer SAscore. Use it only for coarse ranking; do not report it as
  a synthesizability guarantee.
- **SBDD `binding_score` is not docking.** It combines a pocket-fill shape ratio
  with pharmacophore feature complementarity. It has no pose, no scoring function,
  no free energy. Rank with it, then dock the top slice.
- **`filter.py` retains every input molecule.** Nothing is removed — every row is
  flagged. Downstream steps must select on `pass_all`.
- **`optimize.py` outputs everything it explored**, ranked, and **silently ignores
  constraint properties it does not compute** (only `mw, logp, qed, hba, hbd, tpsa,
  rotbonds, sa, num_rings, num_aromatic_rings, heavy_atoms` exist). A typo like
  `mwt<500` is a no-op, not an error.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ERROR: Could not parse SMILES` | Invalid/unsanitizable input | Canonicalize first with `rdkit`/`datamol` |
| Far fewer analogs than `--num` | Few matching attachment sites, or dedup collapse | Raise `--num`, add `mutate`, or try more fragments |
| Empty output / `No valid molecules` | All candidates failed sanitize or MW bounds | Widen inputs; check the lead is drug-sized |
| SBDD errors on numpy | numpy missing | `pip install numpy` (hard requirement for SBDD) |
| SBDD ignores your residues | Residue label mismatch vs. PDB | Use exact `RESNAME+resid` (e.g. `HIS57`); install `biopython` |
| SBDD very slow | 3D embedding per candidate under `--method shape` | Use `--method pharmacophore`, or lower `--num` |
| `optimize.py` output empty of passing rows | Constraints too strict / unsatisfiable | Loosen constraints or add more `--num-iterations` |
| Filter "passes" everything | `filter.py` annotates, not drops | Post-filter on `pass_all == "pass"` |

## Where this fits among sibling skills

- `rdkit`, `datamol` — canonicalization, standardization, descriptor calculation
  for inputs/outputs of these scripts.
- `deepchem` — learned generative models (VAE/diffusion/RL) when heuristics are
  not enough.
- `binding-affinity` — real scoring of SBDD candidates.
- `admet-prediction` — downstream ADMET triage of generated compounds.
- `molecular-optimization` — heavier multi-objective optimization than the
  built-in `optimize.py` loop.

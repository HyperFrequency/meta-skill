# CLI Reference

Exact flags, defaults, output-column schemas, and built-in chemical libraries for
each script. All scripts canonicalize and deduplicate by canonical SMILES, apply
sanity molecular-weight bounds, and print a property-distribution summary. RDKit
error logging is suppressed to `ERROR` level.

---

## `generate_analogs.py`

Scaffold-based analog generation from one lead compound.

| Flag | Type | Default | Meaning |
|------|------|---------|---------|
| `--smiles` | str | required | SMILES of the lead compound |
| `--output` | path | required | Output CSV path (dirs auto-created) |
| `--num` | int | 50 | Target number of analogs (final output trimmed to this) |
| `--strategy` | choice | `all` | `all` \| `rgroup` \| `bioisostere` \| `mutate` |

With `--strategy all`, each strategy targets `max(num//3, 10)` analogs, then the
pooled set is deduped and trimmed to `--num`.

**Strategies**

- **rgroup** — finds aromatic C–H, terminal CH3, and CH2 positions and attaches
  each substituent from the R-group library via reaction SMARTS, with a direct
  substructure-combination fallback.
- **bioisostere** — matches known functional groups by SMARTS and swaps them via
  `AllChem.ReplaceSubstructs`.
- **mutate** — seeded random graph edits (atom-type swap among C/N/O/S/F/Cl, add
  atom, remove terminal atom, add bond); keeps only sanitizable products with
  100 ≤ MW ≤ 1000.

**Output columns:** `id, smiles, mw, logp, qed, tanimoto_to_parent, strategy`
(Tanimoto = Morgan radius 2, 2048 bits, vs. the parent).

**Built-in R-group library:** methyl, ethyl, isopropyl, cyclopropyl, CF3, F, Cl,
Br, OMe, OEt, OH, NH2, NMe2, NO2, CN, acetyl, carboxyl, methylsulfonyl, OCF3,
phenyl, pyridyl.

**Built-in bioisostere map (target → replacement):** COOH→tetrazole,
COOH→acylsulfonamide, phenyl→{thienyl, pyrrolyl, furyl}, amide→sulfonamide,
ester→amide, OH→amine, ether→thioether, C–H→C–F scan.

---

## `generate_fragments.py`

Fragment-based design: grow one fragment, or link/merge two.

| Flag | Type | Default | Meaning |
|------|------|---------|---------|
| `--fragments` | str | required | Comma-separated SMILES, **or** a file path (one SMILES per line; `#` comments and CSV first-column allowed) |
| `--mode` | choice | required | `grow` \| `link` \| `merge` |
| `--output` | path | required | Output CSV path |
| `--num` | int | 50 | Target molecule count |

`link` and `merge` require ≥2 fragments and operate over each fragment pair.

**Modes**

- **grow** — attaches each growth substituent at aromatic C–H, aliphatic CH2/CH3,
  and NH positions.
- **link** — connects two fragments through a two-attachment-point linker from the
  linker library; keeps 150 ≤ MW ≤ 800.
- **merge** — Strategy A: MCS-based scaffold merge (`rdFMCS.FindMCS`, ring-matches-
  ring-only, complete-rings-only, 10 s timeout); Strategy B: direct bonds at
  donor/acceptor and aromatic positions; keeps 100 ≤ MW ≤ 700.

**Output columns:** `id, smiles, mw, logp, qed, hba, hbd, rotbonds, tpsa,
max_frag_similarity, strategy` (`max_frag_similarity` = max Tanimoto to any input
fragment).

**Growth substituents include:** alkyls, phenyl/pyridyl, halogens, CF3, OMe, OH,
amines, CN, amides, sulfonamide, morpholino, piperidyl, piperazinyl, azoles,
tetrazolyl, ethanol, propargyl.

**Linkers include:** methylene→butylene chains, amide/reverse-amide, urea, ether,
thioether, amine, piperazine, piperidine, sulfonamide, ester, hydrazide, triazole,
oxadiazole, glycine, β-alanine.

---

## `generate_sbdd.py`

Structure-based design from a protein pocket. **Requires numpy.** BioPython is
optional (falls back to a plain-text PDB `ATOM`/`HETATM` parser).

| Flag | Type | Default | Meaning |
|------|------|---------|---------|
| `--protein` | path | required | Protein PDB file |
| `--pocket-residues` | str | required | Comma-separated residue IDs (e.g. `ASP189,SER195`) or `auto` |
| `--output` | path | required | Output CSV path |
| `--num` | int | 100 | Number of molecules to generate |
| `--method` | choice | `shape` | `shape` \| `pharmacophore` |
| `--seed` | int | 42 | RNG seed |

**How it works.** Pocket residues are mapped to pharmacophore feature counts
(HBD, HBA, hydrophobic, charged, aromatic) via a built-in amino-acid property
table; the pocket center/radius come from atom coordinates. Molecules are built
by growing seed fragments (benzene, pyridine, azoles, saturated rings, fused
bicyclics) with feature-appropriate substituents.

- **shape** — scores by molecular volume vs. pocket volume (ideal fill ratio
  0.3–0.7), embedding a 3D conformer per candidate (ETKDGv3 + MMFF). This makes it
  the **slowest** script. `binding_score = 0.6·shape + 0.4·pharmacophore`.
- **pharmacophore** — biases seed fragments and substituents toward pocket
  features and scores feature complementarity. `binding_score = 0.3·shape +
  0.7·pharmacophore`.

**Output columns:** `rank, id, smiles, binding_score, shape_score,
pharmacophore_score, mw, logp, qed, hba, hbd, rotbonds, tpsa, sa_score`, sorted by
`binding_score` desc. `binding_score` is a heuristic, **not docking**.

---

## `optimize.py`

Iterative multi-objective optimization by property-guided mutation.

| Flag | Type | Default | Meaning |
|------|------|---------|---------|
| `--input` | path | required | CSV with a `smiles` column, or plain SMILES file |
| `--objectives` | str | required | Comma list: `qed, logp, sa, mw, tpsa, hbd, hba` |
| `--constraints` | str | `""` | e.g. `mw<500,logp<5,qed>0.5` (ops `< <= > >= == !=`) |
| `--output` | path | required | Output CSV path |
| `--num-iterations` | int | 3 | Optimization rounds |
| `--top-k` | int | 20 | Parents carried forward per round |
| `--analogs-per-mol` | int | 15 | Analogs generated per parent per round |
| `--seed` | int | 42 | RNG seed |

Each round: generate analogs (mutations biased by which objectives lag) → compute
properties → evaluate constraints → merge and re-rank by `(passes_constraints,
obj_score)` → cap population at `top_k × 5`. Objective scores are 0–1 with fixed
ideal windows (e.g. LogP peaks at 2, MW 200–500, TPSA 40–120, SA lower-is-better).
**Constraint properties not present in the computed set are silently skipped.**

**Output columns:** `rank, id, smiles, obj_score, passes_constraints,
iteration_found, mw, logp, qed, hba, hbd, tpsa, rotbonds, sa, heavy_atoms`. Output
is **every unique molecule explored across all rounds**, ranked — not just the
final population.

---

## `filter.py`

Drug-likeness annotation for a compound library. **Annotates; it does not remove
rows.** To get a passing subset, filter downstream on `pass_all == "pass"`.

| Flag | Type | Default | Meaning |
|------|------|---------|---------|
| `--input` | path | required | CSV with SMILES column (tries `smiles/SMILES/smi/canonical_smiles`, else first column), or plain SMILES file |
| `--output` | path | required | Output CSV path |
| `--filters` | str | required | Comma list from the table below |
| `--qed-threshold` | float | 0.5 | QED pass threshold |
| `--sa-threshold` | float | 6.0 | SA pass threshold (scale 1–10) |

**Filter definitions**

| Name | Rule |
|------|------|
| `lipinski` | Ro5: MW≤500, LogP≤5, HBD≤5, HBA≤10 — **≤1 violation allowed** |
| `veber` | RotBonds≤10 and TPSA≤140 |
| `qed` | QED ≥ `--qed-threshold` |
| `pains` | No PAINS match (RDKit `FilterCatalog` PAINS catalog) |
| `brenk` | No match against a built-in Brenk SMARTS alert set |
| `leadlike` | MW 200–350, LogP −1…3, RotBonds≤7 |
| `fragmentlike` | Ro3: MW≤300, LogP≤3, HBD≤3, HBA≤3 |
| `bro5` | MW 500–1000, LogP −2…10, HBD≤6, RotBonds≤20 |
| `sa` | `sa_score` ≤ `--sa-threshold` |

**Output columns:** `id, smiles, mw, logp, hbd, hba, rotbonds, tpsa, qed,
sa_score, num_rings, heavy_atoms`, then one `pass_<filter>` column per requested
filter, then `pass_all`. A per-filter pass-rate table and a passing-set property
distribution are printed to stdout.

---

## Shared implementation notes

- **`sa_score`** is a complexity proxy, not the Ertl–Schuffenhauer SAscore.
  `filter.py` and `optimize.py` share one formula:
  `1 + 0.25·rings + 0.5·stereocenters + 0.002·MW + 0.1·rotbonds + 0.3·fused_ring_pairs`,
  clamped to [1, 10]. `generate_sbdd.py` uses a close variant
  (`1 + 0.3·rings + 0.5·stereocenters + 0.003·MW + 0.1·rotbonds`, no fused-ring term,
  upper-clamped at 10 only), so SA values are not bit-identical across all three scripts.
- **Similarity** is Morgan/ECFP4-style: `GetMorganFingerprintAsBitVect(radius=2,
  nBits=2048)` with Tanimoto.
- **Determinism**: `mutate`, `optimize`, and `sbdd` are seeded; rerunning with the
  same `--seed` reproduces output. `rgroup`, `bioisostere`, `grow`, `link`, and
  `merge` are deterministic library enumerations.

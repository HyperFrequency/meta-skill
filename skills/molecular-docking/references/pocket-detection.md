# Binding Pocket Detection and Druggability

The binding site is the cavity where a ligand docks. For Vina it becomes the
search box (center + size); for DiffDock it is informative but not required.
Getting the site right dominates downstream pose quality.

## Detection methods

### 1. Ligand-based (highest confidence)

When the PDB contains a co-crystallized ligand (`HETATM` records), define the
pocket as the protein residues within a distance cutoff (~6–8 Å) of the ligand
atoms. This is the gold standard for a known site.

```python
from Bio.PDB import PDBParser, NeighborSearch
structure = PDBParser(QUIET=True).get_structure("x", "protein.pdb")
atoms = list(structure.get_atoms())
ns = NeighborSearch(atoms)
ligand_atoms = [a for a in atoms if a.get_parent().id[0].startswith("H")
                and a.get_parent().resname not in ("HOH",)]
pocket_residues = {res for lig in ligand_atoms
                   for res in ns.search(lig.coord, 8.0, level="R")}
```

The box center is the mean coordinate of the ligand (or of the pocket-residue
atoms). Limitations: only works with a bound ligand, may miss allosteric sites,
and pocket shape is biased by the specific ligand present.

### 2. Grid / geometric cavity detection (apo structures)

Place a ~1 Å grid around the protein and classify each point as protein interior
(within van der Waals radius of an atom), bulk solvent (no atoms within an outer
cutoff), or **cavity** (between inner and outer cutoffs, buried — atoms present in
several directional octants). Cluster cavity points into pockets and rank by point
count (a volume proxy). General-purpose for structures without a bound ligand;
more expensive and can flag non-functional cavities (crystal contacts, channels).

### 3. Alpha-sphere and ML methods (external tools)

- **fpocket** (alpha spheres): `fpocket -f protein.pdb` — fast, open source.
- **P2Rank** (machine learning): high-accuracy site + ranking prediction.
- **DoGSiteScorer / DeepSite / CavityPlus**: free web servers, add druggability
  or deep-learning scoring.
- **SiteMap** (Schrödinger, commercial): energy-based, detailed druggability.

Prefer one of these for production site-finding; the built-in grid method is a
dependency-free fallback.

## Druggability assessment

Not every cavity binds a drug-like molecule. Rough criteria:

| Property | Druggable | Difficult | Undruggable |
|---|---|---|---|
| Volume (Å³) | 300–1500 | 150–300 or >1500 | <150 |
| Enclosure | >0.5 | 0.3–0.5 | <0.3 |
| Hydrophobicity | 0.3–0.7 | <0.3 or >0.7 | — |
| H-bond sites | 2–8 | >8 or <2 | 0 |
| Depth (Å) | >5 | 3–5 | <3 |

**Volume:** <150 Å³ fits only fragments/ions; 150–300 Å³ suits fragment-based
design; 300–800 Å³ is the sweet spot for most approved drugs; 800–1500 Å³ needs
extended molecules or PROTACs; >1500 Å³ is usually a flat protein-protein
interface (consider peptides/macrocycles).

**Hydrophobicity balance:** the best pockets pair a hydrophobic floor/walls (drive
binding via desolvation) with a polar rim (directional H-bonds for specificity).
Fully hydrophobic pockets are hard to target selectively; fully polar pockets
bind weakly against water competition.

**Shape:** deep enclosed (tunnel-like) pockets are highly druggable; shallow
exposed ones need larger contact area; sub-pockets enable selectivity; flat
surfaces need specialized approaches.

## Turning a pocket into a docking box

- **Center**: geometric mean of cavity grid points or ligand-proximal residue
  atoms → pass as Vina `center=[cx, cy, cz]`.
- **Volume estimate**: convex-hull volume of cavity points (SciPy
  `ConvexHull`) tends to overestimate; `n_points × spacing³` underestimates —
  the true cavity volume sits between them.
- **Residues to note**: catalytic residues (e.g. Ser/His/Asp), charged residues
  (Lys/Arg/Glu/Asp) for salt bridges, aromatics (Phe/Tyr/Trp) for π-stacking, and
  backbone amides lining the pocket.

### Multiple pockets

1. Pocket from a co-crystal ligand → standard docking campaign.
2. Additional cavity-detected pockets → possible allosteric sites.
3. Dock to each independently and compare scores.
4. Prioritize pockets near known functional/catalytic residues.

## Manual specification

If detection fails or you want a specific site, set the box directly:

```bash
# center on known functional residues, box ~25 Å per side
vina --receptor rec.pdbqt --ligand lig.pdbqt \
     --center_x 25 --center_y 30 --center_z 15 \
     --size_x 25 --size_y 25 --size_z 25 --exhaustiveness 32 --out poses.pdbqt
```

Use PyMOL/ChimeraX to read off coordinates, center on the residue(s) of interest,
and pad the box 5–10 Å beyond the expected ligand diameter. For truly blind
docking, prefer DiffDock over a whole-protein Vina box.

## Key references

- Le Guilloux et al. "Fpocket." *BMC Bioinformatics* 10, 168 (2009).
- Halgren. "Identifying and characterizing binding sites and assessing
  druggability." *J. Chem. Inf. Model.* 49, 377–389 (2009).
- Krivák & Hoksza. "P2Rank." *J. Cheminform.* 10, 39 (2018).
- Volkamer et al. "DoGSiteScorer." *Bioinformatics* 28, 2074–2075 (2012).

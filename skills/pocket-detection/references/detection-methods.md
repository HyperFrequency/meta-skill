# Detection Methods

Three complementary detectors, when to use each, how to run them, and how to
reconcile their output. Normalize all three to the single pocket record shown in
`SKILL.md` so the rest of the pipeline stays method-agnostic.

## Method 1 — Grid cavity scan (BioPython + SciPy, no external binary)

A deterministic geometric scan you can run anywhere the Python stack is present.

**Algorithm**

1. Build a 3D grid (default ~1.0 Å spacing) around the protein with a ~6 Å margin.
2. Classify each grid point against protein atoms:
   - **interior** — within ~2.2 Å of any atom (vdW + margin),
   - **bulk solvent** — no atom within ~5 Å,
   - **cavity candidate** — between the two cutoffs **and** buried, i.e. atoms
     present in ≥ 3 directional octants around the point.
3. Cluster cavity points (DBSCAN-style, eps ~3.5 Å).
4. Drop clusters below a minimum size (~30 points) and below `min-volume`.
5. Per cluster compute center, convex-hull volume, bounding box, depth, and the
   set of nearby residues.

**Strengths**: no dependencies, reproducible, good on clear deep cavities.
**Limits**: O(grid_points × atoms) so slow past ~3000-5000 residues; grid
resolution bounds the smallest detectable pocket; can flag crystal-contact
cavities; cannot tell functional from non-functional cavities.

**Tuning**

- `grid spacing` — smaller = higher resolution but slower. ~0.5 Å for small
  pockets, ~1.5 Å to speed up large proteins.
- `min volume` — raise toward 200-300 Å³ to filter fragment-sized noise.
- `max pockets` — ~10 is enough for almost any single protein.

## Method 2 — fpocket (alpha spheres)

Voronoi-tessellation alpha-sphere detector. Fast and well validated.

**Run** (produces a `<name>_out/` directory next to the input):

```bash
fpocket -f protein.pdb
# results:
#   protein_out/protein_info.txt        per-pocket scores/descriptors
#   protein_out/pockets/pocket0_atm.pdb  lining atoms of pocket 0
#   protein_out/pockets/pocket0_vert.pqr alpha-sphere vertices (use for center)
```

Compute a pocket center as the centroid of its alpha-sphere vertices
(`pocket*_vert.pqr`). fpocket also emits its own druggability descriptor in
`*_info.txt`; treat it as a second opinion alongside this skill's 6-axis score.
Confirm exact filenames against the fpocket version you installed.

**Strengths**: seconds even on large proteins; handles flexible/partially open
pockets. **Limits**: needs the binary; sensitive to hydrogens (add/remove
consistently); can over-segment one large cavity into several.

**Install**

```bash
sudo apt-get install fpocket        # Debian/Ubuntu
brew install fpocket                # macOS
# from source: https://github.com/Discngine/fpocket  (make && sudo make install)
```

## Method 3 — P2Rank (machine learning)

Random-forest classifier over Connolly-surface points; best benchmark accuracy.

**Run**:

```bash
prank predict -f protein.pdb -o p2rank_out/
# p2rank_out/protein.pdb_predictions.csv  ranked pockets with center_x/y/z + score
# p2rank_out/protein.pdb_residues.csv     per-residue binding probabilities
```

Read the predicted center columns directly into the pocket record's `center`.
Verify the exact CSV column names against your P2Rank release.

**Strengths**: learns known binding-site patterns, well-calibrated scores,
handles unusual geometries. **Limits**: needs Java + a larger install; quality
depends on training-data coverage.

**Install**:

```bash
# download a release tarball from https://github.com/rdk/p2rank/releases
tar -xzf p2rank_2.4.2.tar.gz
export P2RANK_HOME="$PWD/p2rank_2.4.2"   # and/or put prank on PATH
```

## Auto order

When you do not specify a method, try in descending accuracy and fall back on
availability: **P2Rank** (if `P2RANK_HOME` set or `prank` on `PATH`) →
**fpocket** (if `fpocket` on `PATH`) → **grid** (always available).

## Method selection

| Scenario                          | Method                        | Why                              |
| --------------------------------- | ----------------------------- | -------------------------------- |
| Quick analysis, no external tools | grid                          | zero setup                       |
| Large protein (> ~3000 residues)  | fpocket or P2Rank             | grid too slow                    |
| Highest accuracy needed           | P2Rank                        | best benchmark performance       |
| Novel / unusual target            | P2Rank then grid              | ML + geometry consensus          |
| Apo structure (no ligand)         | auto                          | best available detector          |
| Holo structure (has ligand)       | grid + include ligand sites   | co-crystal ligand = ground truth |
| Several structures to compare     | grid (same method for all)    | consistency across structures    |

## Consensus strategy

For a high-confidence site, run every available detector and match pockets whose
centers agree within ~5 Å:

```bash
# grid, fpocket, P2Rank on the same prepared structure, then
# cluster the three sets of centers; pockets found by all three are strongest.
```

Report agreement explicitly. Disagreement means the pocket is borderline or
method-dependent — say so rather than silently picking one detector's answer.

## Cross-structure comparison

To compare the same protein across structures (apo/holo, WT/mutant, conformers):

1. **Superimpose** the structures on shared, well-ordered backbone atoms so
   coordinates are in one frame.
2. **Detect with one method** (use grid for consistency) on each structure.
3. **Match** pockets across structures within a matching radius (~5 Å center-to-
   center).
4. Report pockets that appear/disappear or shift — e.g. cryptic pockets that open
   only in the holo state, or a site abolished by a mutation.

Restrict to the biologically relevant chain to avoid matching pockets that sit at
crystal-symmetry contacts.

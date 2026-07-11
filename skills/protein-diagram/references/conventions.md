# Setup, Conventions, and Failure Modes

## Dependencies

```bash
pip install biopython matplotlib numpy pymsaviz
```

- **BioPython** — PDB parsing, DSSP wrapper, phi/psi via `PPBuilder`.
- **matplotlib** — all rendering (scripts force the non-interactive `Agg`
  backend, so they work headless / over SSH / in CI).
- **NumPy** — C-alpha distance matrices.
- **pyMSAviz** — MSA panels only.

### DSSP (secondary structure only)

`draw_secondary_structure.py` shells out to an external DSSP binary. It tries
`mkdssp` first, then `dssp`. Install one of:

```bash
conda install -c salilab dssp     # provides `mkdssp`
# or (Debian/Ubuntu):
apt-get install dssp
```

If neither binary is found the script prints the install hint and exits
non-zero. DSSP needs a well-formed PDB with a complete backbone; minimized or
predicted models usually work, fragments may not.

### Converting mmCIF → PDB

The scripts parse PDB only. To use an mmCIF file:

```python
from Bio.PDB import MMCIFParser, PDBIO
s = MMCIFParser(QUIET=True).get_structure("x", "in.cif")
io = PDBIO(); io.set_structure(s); io.save("out.pdb")
```

Very large assemblies can exceed the fixed-column PDB format (chain-ID and
atom-count limits); keep a single chain/model when converting.

## Publication conventions

- **Resolution / format**: 300 DPI for print; prefer **SVG** or **PDF** for
  vector output in papers, PNG for slides.
- **Figure sizes** (script defaults): domain map `12x3`, secondary structure
  `14x2`, Ramachandran `8x8` (square), contact map `8x8`, feature tracks `14x6`.
  MSA sizing is controlled by pyMSAviz, not a flag.
- **Domain colors**: a 15-entry colorblind-safe palette fills domains that omit
  an explicit `color`; reuse the same hex per domain family across a figure set
  for consistency.
- **Secondary-structure colors**: helix red `#e74c3c`, sheet blue `#3498db`,
  coil grey `#bdc3c7`.
- **Contact colormaps**: `viridis_r` or `Blues` read well for distance matrices;
  binary contacts default to `Greys` (black/white).
- **Ramachandran regions**: the standard convention is favored (blue), allowed
  (green), generously allowed (yellow), outliers (red) per Lovell et al. (2003).
  The `--show-regions` overlay here is a **schematic approximation**, not true
  density contours (see limitations).

## Known limitations

- **`--show-regions` (Ramachandran)** draws a few hand-placed ellipses at the
  alpha, beta, and left-handed-alpha basins. Do **not** treat them as validation
  contours or use them to classify outliers; for real MolProbity-style
  favored/allowed classification use a dedicated validation tool.
- **`--show-residue-numbers` (secondary structure)** is accepted by the CLI but
  the current renderer does not draw per-residue numbers on the track; the x-axis
  residue range is still shown. Treat it as a no-op for now.
- **UniProt / InterPro fetch** (`--uniprot`) hits the live EBI InterPro and
  UniProt REST APIs. It needs network access and can return **many overlapping**
  domain/family/homologous-superfamily entries, cluttering the map — curate the
  JSON manually for a clean figure.
- **mmCIF is unsupported** by the bundled scripts; convert to PDB first.
- **Clustal input** to `draw_alignment.py` relies on pyMSAviz auto-detection;
  aligned FASTA is the tested path. Confirm the panel parsed the expected number
  of sequences.

## Failure modes and how to react

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No phi/psi angles found` | Wrong `--chain`, or non-protein/insufficient backbone | Check chain IDs; ensure a real polypeptide |
| `No C-alpha atoms found for chain X` | Chain ID absent, or only heteroatoms/CA-less residues | Verify chain ID matches the PDB |
| `Error running DSSP` | DSSP binary missing or PDB malformed | Install `mkdssp`/`dssp`; clean the PDB |
| Empty / one-sequence MSA panel | Input not actually aligned, or format misdetected | Ensure equal-length aligned records; force FASTA |
| InterPro/UniProt fetch hangs or errors | Network down or bad accession | Retry, check the accession, or supply JSON directly |
| Cluttered domain/feature map | Too many overlapping annotations | Curate JSON; use `--max-features` for feature tracks |

## Performance / scale

- `draw_contact_map.py` builds the distance matrix with an **O(n²) pure-Python**
  double loop. It is fine up to a few thousand residues but gets slow for very
  large chains; vectorize with NumPy broadcasting
  (`np.linalg.norm(coords[:,None,:] - coords[None,:,:], axis=-1)`) if you need
  full-proteome throughput.
- MSA panels scale with sequences × columns; use `--start/--end` to slice a
  region and `--wrap` to keep the figure readable for long alignments.

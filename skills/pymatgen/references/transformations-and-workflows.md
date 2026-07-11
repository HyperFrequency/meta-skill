# Transformations and Workflows

The transformations framework applies systematic, reproducible edits to structures and (via
`TransformedStructure`) records their history. Below: the transformation catalog, then end-to-end
recipes that chain them with I/O and analysis.

## Standard transformations

From `pymatgen.transformations.standard_transformations`. Every transformation exposes
`apply_transformation(struct)`.

```python
from pymatgen.transformations.standard_transformations import (
    SupercellTransformation, SubstitutionTransformation, RemoveSpeciesTransformation,
    PrimitiveCellTransformation, ConventionalCellTransformation, RotationTransformation,
    OrderDisorderedStructureTransformation,
)

SupercellTransformation([[2,0,0],[0,2,0],[0,0,2]]).apply_transformation(struct)   # 2x2x2 cell
SubstitutionTransformation({"Fe": "Mn"}).apply_transformation(struct)             # swap species
SubstitutionTransformation({"Fe": {"Mn": 0.5, "Fe": 0.5}}).apply_transformation(struct)  # partial
RemoveSpeciesTransformation(["H"]).apply_transformation(struct)                   # strip element
PrimitiveCellTransformation().apply_transformation(struct)
ConventionalCellTransformation().apply_transformation(struct)
RotationTransformation([0, 0, 1], 45).apply_transformation(struct)               # 45° about z
OrderDisorderedStructureTransformation().apply_transformation(disordered_struct)  # pick an ordering
```

## Advanced transformations

From `pymatgen.transformations.advanced_transformations`. Many return a ranked list when called
with `return_ranked_list=True`.

```python
from pymatgen.transformations.advanced_transformations import (
    EnumerateStructureTransformation, MagOrderingTransformation,
    DopingTransformation, ChargeBalanceTransformation, SlabTransformation,
)

# Enumerate symmetrically distinct orderings of a disordered structure
ordered = EnumerateStructureTransformation(max_cell_size=8).apply_transformation(
    struct, return_ranked_list=True)          # [{"structure": ..., "energy": ...}, ...]

# Enumerate magnetic orderings (moments in μB)
MagOrderingTransformation({"Fe": 5.0}).apply_transformation(struct, return_ranked_list=True)

# Systematic doping
DopingTransformation("Mn", min_length=10).apply_transformation(struct, return_ranked_list=True)

# Generate a slab as a transformation
SlabTransformation(miller_index=[1,0,0], min_slab_size=10, min_vacuum_size=10).apply_transformation(struct)
```

## Chaining with history

`TransformedStructure` (in `pymatgen.alchemy.materials`) applies a sequence and keeps the
provenance, so you can write a VASP input directory with the full recipe attached.

```python
from pymatgen.alchemy.materials import TransformedStructure

ts = TransformedStructure(struct, [])
ts.append_transformation(SupercellTransformation([[2,0,0],[0,2,0],[0,0,2]]))
ts.append_transformation(SubstitutionTransformation({"Fe": "Mn"}))
final = ts.final_structure
ts.history                        # inspect the applied steps
ts.write_vasp_input("./calc")     # writes inputs + provenance
```

For applying one recipe across many files, use `CifTransmuter` / `PoscarTransmuter` from
`pymatgen.alchemy.transmuters`.

---

# Workflow recipes

These stitch transformations, I/O, and analysis into common tasks. Pymatgen prepares and parses;
you run the DFT/MD engine between the write and read steps.

## High-throughput doped-structure generation

```python
from pymatgen.core import Structure
from pymatgen.transformations.standard_transformations import SubstitutionTransformation
from pymatgen.io.vasp.sets import MPRelaxSet

base = Structure.from_file("POSCAR")
for dopant in ["Mn", "Co", "Ni", "Cu"]:
    doped = SubstitutionTransformation({"Fe": dopant}).apply_transformation(base)
    MPRelaxSet(doped).write_input(f"./calcs/Fe_{dopant}")
```

## Phase-diagram stability check

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition

with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys("Li-Fe-O")
pd = PhaseDiagram(entries)
comp = Composition("LiFeO2")
decomposition = pd.get_decomposition(comp)     # {} if it is itself stable
```

See [characterization.md](characterization.md) for the full phase-diagram API and
[materials-project-api.md](materials-project-api.md) for entry retrieval.

## Band-structure calculation (3-stage)

```python
from pymatgen.core import Structure
from pymatgen.io.vasp.sets import MPRelaxSet, MPStaticSet, MPNonSCFSet
from pymatgen.io.vasp import Vasprun

# 1. Relax
MPRelaxSet(Structure.from_file("initial_POSCAR")).write_input("./1_relax")
# ... run VASP ...
relaxed = Structure.from_file("1_relax/CONTCAR")

# 2. Static (SCF density)
MPStaticSet(relaxed).write_input("./2_static")
# ... run VASP ...

# 3. Non-SCF along a high-symmetry k-path
MPNonSCFSet(relaxed, mode="line").write_input("./3_bands")
# ... run VASP ...

bs = Vasprun("3_bands/vasprun.xml").get_band_structure(line_mode=True)
bs.get_band_gap()
```

## Surface-energy setup

```python
from pymatgen.core import Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.vasp.sets import MPRelaxSet

bulk = Structure.from_file("bulk_POSCAR")
for miller in [(1,0,0), (1,1,0), (1,1,1)]:
    slab = SlabGenerator(bulk, miller, min_slab_size=10, min_vacuum_size=15,
                         center_slab=True).get_slabs()[0]
    MPRelaxSet(slab).write_input(f"./slab_{''.join(map(str, miller))}")
# After DFT, per slab:
#   surf_energy = (E_slab - n_atoms * E_bulk_per_atom) / (2 * slab.surface_area)  # eV/Å^2
#   surf_energy *= 16.0218                                                        # -> J/m^2
```

## Order a disordered structure by enumeration

```python
from pymatgen.core import Structure, Lattice, Species
from pymatgen.transformations.advanced_transformations import EnumerateStructureTransformation

struct = Structure.from_spacegroup("Fm-3m", Lattice.cubic(4.2),
                                   ["Li", "O"], [[0,0,0], [0.5,0.5,0.5]])
struct[0] = {Species("Li"): 0.5, Species("Na"): 0.5}   # mixed occupancy on the Li site
ordered = EnumerateStructureTransformation(max_cell_size=4).apply_transformation(
    struct, return_ranked_list=True)
for i, s in enumerate(ordered[:10]):
    s["structure"].to(filename=f"ordered_{i}.cif")
```

## Diffusion from an AIMD trajectory

```python
from pymatgen.io.vasp import Xdatcar
from pymatgen.analysis.diffusion.analyzer import DiffusionAnalyzer

da = DiffusionAnalyzer.from_structures(
    Xdatcar("XDATCAR").structures, specie="Li",
    temperature=300, time_step=2, step_skip=10)
da.diffusivity, da.conductivity     # cm^2/s, mS/cm
```

## Guidance

1. Keep workflows modular — discrete, restartable steps.
2. Between a `write_input` and its paired output parse, check that the DFT/MD job converged.
3. Track provenance with `TransformedStructure` for reproducibility.
4. For production pipelines, hand orchestration to a workflow manager (atomate2, FireWorks, AiiDA,
   custodian for error correction) rather than driving each step by hand.
5. Validate intermediate structures (no overlapping atoms, sane bond lengths) before proceeding.

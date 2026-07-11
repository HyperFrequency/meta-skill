# Characterization Modules (`pymatgen.analysis.*`, `pymatgen.symmetry.*`, `pymatgen.electronic_structure.*`)

Structure characterization and property analysis. Each section is independent — jump to the one you need.

## Symmetry

```python
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

sga = SpacegroupAnalyzer(struct)                 # tune with symprec=... for noisy structures
sga.get_space_group_symbol()                      # "Fm-3m"
sga.get_space_group_number()                      # 225
sga.get_crystal_system()                          # "cubic"
sga.get_conventional_standard_structure()
sga.get_primitive_standard_structure()
sga.get_symmetrized_structure().equivalent_sites  # symmetry-equivalent site groups
sga.get_symmetry_operations()
```

If symmetry comes back as P1 on a structure you expect to be symmetric, raise the tolerance:
`SpacegroupAnalyzer(struct, symprec=0.1)`. Lower it to avoid over-symmetrizing a near-symmetric cell.

## Local environment / coordination

```python
from pymatgen.analysis.local_env import (
    CrystalNN, VoronoiNN, MinimumDistanceNN, BrunnerNN_real,
)

cnn = CrystalNN()                          # robust default for crystals
neighbors = cnn.get_nn_info(struct, n=0)   # neighbors of site index 0
cn = len(neighbors)                        # coordination number
for nb in neighbors:
    site = struct[nb["site_index"]]        # neighbor site; nb["weight"] scores the bond
```

Deeper coordination-geometry identification lives in `pymatgen.analysis.chemenv`
(`LocalGeometryFinder` + a chemenv strategy). Oxidation states from bond geometry:

```python
from pymatgen.analysis.bond_valence import BVAnalyzer
struct_oxi = BVAnalyzer().get_oxi_state_decorated_structure(struct)
```

## Structure comparison

```python
from pymatgen.analysis.structure_matcher import StructureMatcher

sm = StructureMatcher()
sm.fit(struct1, struct2)                     # True if equivalent within tolerance
sm.get_mapping(struct1, struct2)             # site mapping
sm.group_structures([s1, s2, s3, ...])       # cluster equivalent structures
```

## Phase diagrams and thermodynamics

```python
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
from pymatgen.entries.computed_entries import ComputedEntry

entries = [ComputedEntry("Fe", -8.4), ComputedEntry("O2", -4.9),
           ComputedEntry("Fe2O3", -8.3), ComputedEntry("Fe3O4", -9.1)]
pd = PhaseDiagram(entries)

pd.stable_entries                            # phases on the convex hull
pd.get_e_above_hull(entry)                   # eV/atom; 0 == stable
pd.get_decomposition(comp)                   # {entry: fraction, ...} for an unstable comp
pd.get_equilibrium_reaction_energy(entry)

PDPlotter(pd).show()                         # quick check; extract data for publication plots
```

Typically the entries come straight from the Materials Project — see
[materials-project-api.md](materials-project-api.md).

**Pourbaix (E–pH) diagrams** and **chemical-potential diagrams**:

```python
from pymatgen.analysis.pourbaix_diagram import PourbaixDiagram, PourbaixPlotter
pb = PourbaixDiagram(entries)                # entries from mpr.get_pourbaix_entries([...])
pb.get_stable_entry(pH=7, V=0)

from pymatgen.analysis.phase_diagram import ChemicalPotentialDiagram
cpd = ChemicalPotentialDiagram(entries, limits={"O": (-10, 0)})
cpd.domains
```

## Electronic structure

```python
from pymatgen.io.vasp import Vasprun
from pymatgen.electronic_structure.plotter import BSPlotter, DosPlotter

vr = Vasprun("vasprun.xml")

# Band structure
bs = vr.get_band_structure()
bs.get_band_gap()      # {"energy": float, "direct": bool, "transition": str}
bs.is_metal()
bs.get_vbm(); bs.get_cbm()
BSPlotter(bs).save_plot("bands.png")

# Density of states
dos = vr.complete_dos
dos.get_element_dos()          # projected by element
dos.get_spd_dos()              # projected by s/p/d orbital
dos.get_site_dos(struct[0])    # projected onto one site
DosPlotter().add_dos("Total", dos)
```

## Surfaces and interfaces

```python
from pymatgen.core.surface import SlabGenerator, generate_all_slabs

slabgen = SlabGenerator(struct, miller_index=(1, 1, 1),
                        min_slab_size=10.0, min_vacuum_size=10.0, center_slab=True)
slabs = slabgen.get_slabs()
all_slabs = generate_all_slabs(struct, max_index=2, min_slab_size=10, min_vacuum_size=10)
```

**Wulff shape** (equilibrium crystal morphology from surface energies in J/m²):

```python
from pymatgen.analysis.wulff import WulffShape
wulff = WulffShape(struct.lattice, {(1,0,0): 1.0, (1,1,0): 1.1, (1,1,1): 0.9})
wulff.surface_area; wulff.volume; wulff.effective_radius
```

**Adsorption sites** on a slab:

```python
from pymatgen.analysis.adsorption import AdsorbateSiteFinder
from pymatgen.core import Molecule

asf = AdsorbateSiteFinder(slab)
sites = asf.find_adsorption_sites()          # {"ontop": [...], "bridge": [...], "hollow": [...]}
ads_structs = asf.generate_adsorption_structures(Molecule("O", [[0, 0, 0]]), repeat=[2, 2, 1])
```

**Coherent interfaces** between a substrate and film: `CoherentInterfaceBuilder` in
`pymatgen.analysis.interfaces.coherent_interfaces`.

## Diffraction

```python
from pymatgen.analysis.diffraction.xrd import XRDCalculator

pattern = XRDCalculator().get_pattern(struct, two_theta_range=(0, 90))
pattern.x     # 2θ positions (degrees)
pattern.y     # relative intensities
pattern.hkls  # Miller indices contributing to each peak
```

Neutron analog: `pymatgen.analysis.diffraction.neutron.NDCalculator`.

## Elasticity

```python
from pymatgen.analysis.elasticity import ElasticTensor

et = ElasticTensor.from_voigt(voigt_6x6_matrix)
et.k_voigt    # bulk modulus (GPa)
et.g_voigt    # shear modulus (GPa)
et.y_mod      # Young's modulus (GPa)
```

## Magnetism

```python
from pymatgen.analysis.magnetism import CollinearMagneticStructureAnalyzer
CollinearMagneticStructureAnalyzer(struct).ordering    # "FM", "AFM", "FiM", ...

from pymatgen.transformations.advanced_transformations import MagOrderingTransformation
orders = MagOrderingTransformation({"Fe": 5.0}).apply_transformation(struct, return_ranked_list=True)
```

## Diffusion (from AIMD trajectories)

```python
from pymatgen.io.vasp import Xdatcar
from pymatgen.analysis.diffusion.analyzer import DiffusionAnalyzer

structures = Xdatcar("XDATCAR").structures
da = DiffusionAnalyzer.from_structures(structures, specie="Li",
                                       temperature=300, time_step=2, step_skip=10)
da.diffusivity      # cm^2/s
da.conductivity     # mS/cm
da.msd              # mean squared displacement
```

## Reactions

```python
from pymatgen.analysis.reaction_calculator import ComputedReaction
rxn = ComputedReaction([ComputedEntry("Fe", -8.4), ComputedEntry("O2", -4.9)],
                       [ComputedEntry("Fe2O3", -8.3)])
rxn.normalized_repr               # balanced equation string
rxn.calculated_reaction_energy    # eV per formula unit
```

## Guidance

1. Reduce to the primitive cell (via `SpacegroupAnalyzer`) before expensive analyses.
2. Cross-check coordination with more than one `local_env` strategy when it matters.
3. Validate that input structures are well-converged before deriving properties.
4. Use built-in plotters for quick sanity checks; extract arrays for publication figures.
5. Different tools trade speed against accuracy — pick deliberately.

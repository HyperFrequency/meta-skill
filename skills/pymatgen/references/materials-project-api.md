# Materials Project API (`mp_api.client.MPRester`)

The Materials Project holds computed properties for hundreds of thousands of inorganic crystals
and molecules. Access it through the standalone `mp-api` package. The legacy
`pymatgen.ext.matproj.MPRester` targets a retired endpoint — do not use it.

## Setup

```bash
uv pip install mp-api
export MP_API_KEY="your_key_here"     # from https://next-gen.materialsproject.org/
```

Never hardcode the key in source or notebooks; read it from the environment. `MPRester()` picks
up `MP_API_KEY` automatically.

## Always use the context manager

```python
from mp_api.client import MPRester

with MPRester() as mpr:
    ...        # session is opened and cleanly closed
```

## Search summaries

`mpr.materials.summary.search(...)` returns lightweight documents. Filter by formula, chemical
system, elements, or property ranges.

```python
with MPRester() as mpr:
    mats = mpr.materials.summary.search(formula="Fe2O3")
    mats = mpr.materials.summary.search(chemsys="Li-Fe-O")
    mats = mpr.materials.summary.search(elements=["Fe", "O"])
    mats = mpr.materials.summary.search(material_ids=["mp-149"])

    for m in mats:
        m.material_id           # "mp-19770"
        m.formula_pretty        # "Fe2O3"
        m.energy_above_hull     # eV/atom
        m.band_gap              # eV
        m.formation_energy_per_atom
        m.density
        m.symmetry.symbol       # space group
```

### Property-range filters

Ranges are `(low, high)` tuples:

```python
with MPRester() as mpr:
    mats = mpr.materials.summary.search(
        chemsys="Li-Fe-O",
        energy_above_hull=(0, 0.05),   # stable / near-stable
        band_gap=(1.0, 3.0),           # semiconducting
    )
    mats = mpr.materials.summary.search(elements=["Fe"], is_magnetic=True)
    mats = mpr.materials.summary.search(chemsys="Fe-Ni", is_metal=True)
```

### Limit returned fields

Request only what you need to cut transfer:

```python
with MPRester() as mpr:
    mats = mpr.materials.summary.search(
        material_ids=["mp-149"],
        fields=["material_id", "formula_pretty", "structure",
                "energy_above_hull", "band_gap", "symmetry"],
    )
```

## Fetch structures

```python
with MPRester() as mpr:
    struct  = mpr.get_structure_by_material_id("mp-149")
    structs = mpr.get_structures(["mp-149", "mp-510", "mp-19017"])   # one batched call
```

## Fetch electronic structure

```python
with MPRester() as mpr:
    bs  = mpr.get_bandstructure_by_material_id("mp-149")
    dos = mpr.get_dos_by_material_id("mp-149")
    if bs:
        bs.get_band_gap(); bs.is_metal()
```

## Fetch entries for thermodynamics

`ComputedEntry` objects feed directly into `PhaseDiagram` and `PourbaixDiagram`.

```python
from pymatgen.analysis.phase_diagram import PhaseDiagram

with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys("Li-Fe-O")
pd = PhaseDiagram(entries)

with MPRester() as mpr:
    pbx_entries = mpr.get_pourbaix_entries(["Fe"])
```

## Specialized property endpoints

Beyond `summary`, dedicated collections expose richer data:

```python
with MPRester() as mpr:
    mpr.materials.elasticity.search(chemsys="Fe-O", bulk_modulus_vrh=(100, 300))  # GPa
    mpr.materials.dielectric.search(material_ids=["mp-149"])
    mpr.materials.piezoelectric.search(piezoelectric_modulus=(1, 100))
    mpr.materials.surface_properties.search(material_ids=["mp-149"])
    mpr.molecules.summary.search(formula="H2O")
```

## Errors and rate limits

```python
from mp_api.client.core.client import MPRestError

try:
    with MPRester() as mpr:
        mats = mpr.materials.summary.search(material_ids=["invalid-id"])
except MPRestError as e:
    ...   # handle API errors (bad key, unknown id, rate limit)
```

The API is rate-limited. Batch requests (`get_structures` over `get_structure_by_material_id` in
a loop), and cache results you reuse:

```python
import json
with MPRester() as mpr:
    mats = mpr.materials.summary.search(chemsys="Li-Fe-O")
    with open("li_fe_o.json", "w") as f:
        json.dump([m.model_dump() for m in mats], f, default=str)
```

## Screening pattern

```python
with MPRester() as mpr:
    candidates = mpr.materials.summary.search(
        elements=["Li"], energy_above_hull=(0, 0.05),
        fields=["material_id", "formula_pretty", "band_gap", "energy_above_hull"],
    )
    hits = [m for m in candidates if m.band_gap < 0.5]   # e.g. conductive Li compounds
```

## Guidance

1. Always use `with MPRester() as mpr:`.
2. Read the key from `MP_API_KEY`; never hardcode it.
3. Batch queries and cache results; respect rate limits.
4. Restrict `fields=[...]` to what you need.
5. Not every property exists for every material — guard against `None`.
6. Anything you retrieve plugs straight into pymatgen's analysis tools (symmetry, slabs, phase
   diagrams) — see [characterization.md](characterization.md).

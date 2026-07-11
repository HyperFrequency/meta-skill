# Domain databases — astropy, Materials Project, PDG, OEIS, NIST WebBook

Each domain source has its own access pattern, authentication, and citation
requirement. Fetch the value, keep its uncertainty and provenance, and cite.

---

## Astronomical constants (astropy)

`astropy.constants` (BSD-3-Clause) is the authoritative source for solar-system
and astronomical constants. Each constant is an object carrying value, unit,
uncertainty, and a literature reference — richer than a bare float.

```python
from astropy import constants as ac

ac.M_sun        # solar mass       (Quantity, kg)
ac.R_sun        # solar radius     (m)
ac.L_sun        # solar luminosity (W)
ac.M_earth      # Earth mass       (kg)
ac.R_earth      # Earth radius     (m)
ac.au           # astronomical unit (m)
ac.G, ac.c, ac.h, ac.k_B   # astropy's own copies of fundamental constants

ac.M_sun.value        # -> 1.988...e30 (float)
ac.M_sun.unit         # -> Unit("kg")
ac.M_sun.uncertainty  # standard uncertainty
ac.M_sun.reference    # citation string, e.g. "IAU 2015 Resolution B3"
```

Convert to other units with astropy's unit machinery:

```python
import astropy.units as u
ac.au.to(u.km)        # 1 AU in kilometres
```

For anything beyond constants (coordinates, ephemerides, time systems, table
I/O), delegate to the `astropy` skill. Only quick constant lookups belong here.

---

## Materials Project (mp-api)

Formation energies, band gaps, densities, elastic tensors, and crystal symmetry
for computed inorganic materials.

**Setup:** `pip install mp-api`; get a free key at materialsproject.org/api and
set `MP_API_KEY` (do not hardcode it).

```python
import os
from mp_api.client import MPRester

with MPRester(os.environ["MP_API_KEY"]) as mpr:
    # NOTE: the method path is version-sensitive. Newer mp-api:
    #   mpr.materials.summary.search(...)
    # Older mp-api:
    #   mpr.summary.search(...)
    docs = mpr.materials.summary.search(
        formula="Si",
        fields=["material_id", "formula_pretty", "band_gap",
                "energy_above_hull", "density", "symmetry"],
    )
    for d in docs[:5]:
        print(d.material_id, d.formula_pretty,
              f"gap={d.band_gap:.3f} eV",
              f"E_hull={d.energy_above_hull:.4f} eV/atom",
              f"ρ={d.density:.3f} g/cm³")
```

Caveats:
- **Verify method path and field names against your installed mp-api version** —
  the client API has been reorganized across releases. If `mpr.materials.summary`
  raises, try `mpr.summary`, and inspect available fields with the client's
  `available_fields` helper on the endpoint.
- Filter with keyword args like `formula=`, `chemsys=`, `material_ids=`,
  `band_gap=(min, max)`, `is_stable=True`.
- Cite the material-id (e.g. `mp-149`) and the Materials Project in results.

`pymatgen` (a sibling library) parses/manipulates the returned structures if you
need to go beyond property lookup.

---

## Particle Data Group (PDG)

Masses, charges, spins, lifetimes/widths, and branching ratios for every known
particle. The PDG is the standard-of-record; cite the review year.

### Programmatic access
The official `pdg` package exposes the full database:

```python
# pip install pdg
import pdg
api = pdg.connect()            # opens the bundled/downloaded PDG database
# Query methods (e.g. lookup by name or PDG identifier) — consult the pdg
# package documentation for exact signatures, which vary by version.
```

Use the package for programmatic work; **check its docs for the current query
API** rather than guessing method names.

### Curated reference values (common particles)
Convenient for quick use; for precision or rare states go to pdg.lbl.gov.

| Particle | Mass | Charge | Spin | Lifetime |
|---|---|---|---|---|
| electron | 0.51099895 MeV | −1 | ½ | stable |
| proton   | 938.27208816 MeV | +1 | ½ | stable (> 10³⁴ yr) |
| neutron  | 939.56542052 MeV | 0 | ½ | 878.4 s (free) |
| muon     | 105.6583755 MeV | −1 | ½ | 2.1969811×10⁻⁶ s |
| π± (charged pion) | 139.57039 MeV | ±1 | 0 | 2.6033×10⁻⁸ s |
| W boson  | 80.3692 GeV | ±1 | 1 | — (Γ ≈ 2.08 GeV) |
| Z boson  | 91.1876 GeV | 0 | 1 | — (Γ ≈ 2.495 GeV) |
| Higgs    | 125.20 GeV | 0 | 0 | — |

Convert particle masses to energy/kg with scipy factors, e.g.
`mass_kg = mass_MeV * 1e6 * const.eV / const.c**2`.

Citation: "Particle Data Group, R. L. Workman et al., Phys. Rev. D 110, 030001
(2024)". Update the reference to match the review edition you quote.

---

## OEIS (integer sequences)

Identify a sequence from its first terms, or fetch a known A-number. The JSON
endpoint is stable and needs no key.

```python
import requests

# Identify by leading terms (comma-separated)
r = requests.get("https://oeis.org/search",
                 params={"q": "1,1,2,3,5,8,13", "fmt": "json"}, timeout=30)
data = r.json()
first = data["results"][0]
print(first["number"], first["name"])   # e.g. 45  Fibonacci numbers

# Fetch a specific sequence by A-number
requests.get("https://oeis.org/search",
             params={"q": "id:A000045", "fmt": "json"}, timeout=30).json()
```

Each result includes fields like `number` (the A-number as int), `name`,
`data` (comma-separated terms), `formula`, and `keyword`. Be gentle with request
rate; cache results when scanning many sequences.

---

## NIST Chemistry WebBook

Thermochemical data (ΔfH, S°, Cp), phase-change properties, ion energetics, and
IR/mass/UV spectra for chemical species, at https://webbook.nist.gov/chemistry/.

There is **no stable official REST/JSON API**; the WebBook is a web resource
queried through its HTML forms (by name, formula, CAS number, or InChI). For
programmatic compound data prefer `pubchem-database`; scrape the WebBook only
when a property is unique to NIST, and cite the WebBook (NIST Standard Reference
Database 69) with the access date.

---

## Choosing a source

| Need | Source |
|---|---|
| Fundamental constant, unit factor, uncertainty | `scipy.constants` (see `references/scipy-constants.md`) |
| Solar/planetary constants with references | `astropy.constants` |
| Material band gap / formation energy / symmetry | Materials Project (mp-api) |
| Particle mass / lifetime / quantum numbers | PDG (`pdg` package or curated table) |
| Integer-sequence identification | OEIS JSON endpoint |
| Thermochemistry / spectra of a species | NIST Chemistry WebBook (web) or `pubchem-database` |

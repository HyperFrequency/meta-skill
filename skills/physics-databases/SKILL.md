---
name: physics-databases
version: 0.1.0
description: >-
  Fetch physical constants, unit-conversion factors, and reference data from
  authoritative databases instead of hardcoding numbers. Covers CODATA
  fundamental constants and unit conversions via scipy.constants (with
  uncertainties), constant search/lookup by keyword, astronomical constants via
  astropy, materials properties via the Materials Project (mp-api), particle
  masses/lifetimes/quantum numbers from the Particle Data Group, and integer
  sequences from OEIS. Use whenever code needs a physical constant, a conversion
  factor, a particle property, a material property, or any cited reference value
  — always query the database rather than typing a number from memory. Not for
  symbolic algebra or dimensional bookkeeping (use `sympy` / `dimensional-analysis`),
  full astronomy pipelines (use `astropy`), chemical compound/structure lookups
  (use `pubchem-database` / `rdkit`), or general web search of non-numeric facts.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "scipy: BSD-3-Clause; astropy: BSD-3-Clause"
---

# Physics Databases

## Overview

Physical constants, unit conversions, and reference values are versioned data —
they change between CODATA editions, PDG releases, and Materials Project builds.
Typing them from memory silently bakes in stale or mistyped numbers. This skill
routes you to the authoritative source for each class of value and shows the
exact API to pull it, with its published uncertainty and a citable provenance.

The workhorse is `scipy.constants` (bundling a specific CODATA edition), extended
by `astropy` for astronomy, `mp-api` for materials, the Particle Data Group for
particles, and OEIS for integer sequences.

## When to Use This Skill

- You need a fundamental constant (c, h, k_B, G, e, mₑ, Nₐ, α, …) in code.
- You need a unit-conversion factor (eV→J, Å→m, atm→Pa, ly→m) and want it exact.
- You need a constant's **uncertainty** or the CODATA edition it came from.
- You want to search for a constant by keyword ("Bohr", "magnetic moment").
- You need a particle's mass, charge, spin, or lifetime with a PDG citation.
- You need a material's band gap, formation energy, density, or space group.
- You need astronomical constants (solar mass, AU, parsec) with references.
- You need to identify or look up an integer sequence (OEIS).

## When NOT to Use This Skill

- Symbolic manipulation of physical formulas → use `sympy`.
- Tracking/checking units and dimensions of an expression → use `dimensional-analysis`.
- Full astronomy workflows (coordinates, time systems, tables) → use `astropy` directly.
- Chemical compound properties, structures, or identifiers → use `pubchem-database` or `rdkit`.
- Generic scientific-database record retrieval → use `database-lookup`.
- Non-numeric factual questions answerable by web search → use a research skill.

## The One Rule: Never Hardcode a Constant

Do **not** write `c = 3e8` or `h = 6.626e-34`. Always import from a database:

```python
from scipy import constants as const

c   = const.c            # speed of light, m/s
h   = const.h            # Planck constant, J·s
k_B = const.k            # Boltzmann constant, J/K
e   = const.e            # elementary charge, C
N_A = const.N_A          # Avogadro number, 1/mol
```

Why: constants are revised (CODATA 2014 → 2018 → 2022), and a mistyped exponent
is a class of bug that unit tests rarely catch. Pulling from `scipy.constants`
guarantees internal consistency across your codebase.

### CODATA edition depends on your scipy version

`scipy.constants` bundles **one** CODATA edition, tied to the scipy release
(recent scipy — roughly ≥1.15 — ships CODATA 2022; earlier ships CODATA 2018).
Confirm which edition your version bundles from scipy's release notes before
citing, and always state the edition in results, e.g. "CODATA 2022 via
scipy.constants 1.15". See `references/scipy-constants.md`.

## scipy.constants: constants, conversions, search

Three access patterns cover almost everything:

```python
from scipy import constants as const

# 1. Named attributes for common constants and unit factors
const.c, const.hbar, const.G, const.eV, const.angstrom, const.atm

# 2. The physical_constants table: (value, unit, uncertainty)
value, unit, uncertainty = const.physical_constants['Bohr radius']

# 3. Convenience accessors + keyword search
const.value('fine-structure constant')     # float
const.unit('fine-structure constant')       # str
const.precision('fine-structure constant')  # relative uncertainty
const.find('electron')                       # list of matching keys
```

The full constant catalog, the complete unit-conversion reference (energy,
length, pressure, temperature, time, angle), and the uncertainty/precision APIs
are in **`references/scipy-constants.md`**.

## Domain databases (pointers)

Each domain database has its own access pattern, auth, and citation. Full
examples, field names, and caveats live in **`references/domain-databases.md`**.

- **Astronomical constants** — prefer `astropy.constants` (`M_sun`, `R_sun`,
  `L_sun`, `M_earth`, `au`, …); every value carries `.uncertainty` and
  `.reference`. Delegate deep astronomy to the `astropy` skill.
- **Materials Project** — `from mp_api.client import MPRester`; query band gap,
  formation energy, density, and symmetry by formula or material-id. Requires an
  `MP_API_KEY`. Method paths are version-sensitive (see reference).
- **Particle Data Group (PDG)** — particle masses, charges, spins, lifetimes.
  Use the official `pdg` package for programmatic queries, or the curated
  reference values for common particles. Always cite the PDG review year.
- **OEIS** — identify or look up integer sequences via the stable JSON endpoint
  `https://oeis.org/search?q=<terms>&fmt=json`.
- **NIST Chemistry WebBook** — thermochemistry, phase-change, and spectral data
  at `webbook.nist.gov`. There is no stable official REST API; access via the web
  interface, and prefer `pubchem-database` for programmatic compound data.

## Reporting Values

- Report the **uncertainty** when the source provides one (CODATA, PDG, astropy).
- State the **provenance and edition**: "CODATA 2022 via scipy.constants",
  "PDG 2024 (Phys. Rev. D 110, 030001)", "Materials Project mp-149".
- Preserve full precision in computation; round only for display.

## References

- `references/scipy-constants.md` — constant catalog, unit-conversion tables, search & uncertainty APIs.
- `references/domain-databases.md` — astropy, Materials Project, PDG, OEIS, NIST WebBook: examples, fields, auth, citations.

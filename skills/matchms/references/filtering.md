# Filtering & Metadata Harmonization

Filters are single-spectrum transforms in `matchms.filtering`. Each takes a
`Spectrum` and returns a modified copy — or `None` when the spectrum fails a
requirement (all `require_*` filters, and some repair filters). **Always
reassign the result and guard against `None`** before the next step.

Three families: metadata processing, peak processing, and quality gates. Order
matters: harmonize metadata first, normalize before relative-intensity
selection, add losses/fingerprints before the scorer that needs them.

## `default_filters(spectrum)`

The standard metadata-harmonization bundle. Run it first on almost every
spectrum. It applies (in order): `make_charge_int`, `add_precursor_mz`,
`add_retention_time`, `add_retention_index`, `derive_adduct_from_name`,
`derive_formula_from_name`, `clean_compound_name`, `harmonize_undefined_smiles`,
`harmonize_undefined_inchi`.

## Metadata processing

### Compound & chemical identity
| Filter | Purpose |
| --- | --- |
| `add_compound_name(s)` | Move the compound name into the canonical metadata field. |
| `clean_compound_name(s)` | Strip common junk/formatting from names. |
| `derive_adduct_from_name(s)` | Extract adduct notation embedded in a name. |
| `derive_formula_from_name(s)` | Extract a molecular formula embedded in a name. |
| `derive_annotation_from_compound_name(s)` | Look up SMILES/InChI from PubChem by name (network). |

### Structure conversions (require RDKit)
| Filter | Purpose |
| --- | --- |
| `derive_inchi_from_smiles(s)` | SMILES → InChI. |
| `derive_smiles_from_inchi(s)` | InChI → SMILES. |
| `derive_inchikey_from_inchi(s)` | InChI → 27-char InChIKey. |
| `repair_inchi_inchikey_smiles(s)` | Fix identifiers stored in the wrong field. |
| `repair_not_matching_annotation(s)` | Make SMILES/InChI/InChIKey mutually consistent. |
| `add_fingerprint(s, fingerprint_type="daylight", nbits=2048)` | Compute a molecular fingerprint for `FingerprintSimilarity`. Types: `"daylight"`, `"morgan1"`, `"morgan2"`, `"morgan3"`. |

### Mass & charge
| Filter | Purpose |
| --- | --- |
| `add_precursor_mz(s)` | Normalize/standardize precursor m/z. |
| `add_parent_mass(s, estimate_from_adduct=True)` | Neutral parent mass from precursor m/z + adduct. |
| `correct_charge(s)` | Align charge sign with ionmode. |
| `make_charge_int(s)` | Coerce charge to integer. |
| `clean_adduct(s)` | Standardize adduct notation. |
| `interpret_pepmass(s)` | Split a combined `pepmass` field into m/z + intensity. |

### Ion mode & retention
| Filter | Purpose |
| --- | --- |
| `derive_ionmode(s)` | Infer positive/negative from the adduct. |
| `require_correct_ionmode(s, ion_mode)` | Keep only the requested mode; else `None`. |
| `add_retention_time(s)` / `add_retention_index(s)` | Harmonize RT / RI fields. |

### Harmonize "undefined" values
`harmonize_undefined_smiles(s, undefined="", aliases=None)`,
`harmonize_undefined_inchi(...)`, `harmonize_undefined_inchikey(...)` — unify the
many "unknown"/blank representations to one consistent value.

### Repair & structure-validation gates
| Filter | Behavior |
| --- | --- |
| `repair_adduct_based_on_smiles(s, mass_tolerance=0.1)` | Fix adduct so calculated mass matches. |
| `repair_parent_mass_is_mol_wt(s, mass_tolerance=0.1)` | Convert average MW to monoisotopic mass. |
| `repair_precursor_is_parent_mass(s)` | Un-swap precursor/parent mass fields. |
| `repair_smiles_of_salts(s, mass_tolerance=0.1)` | Strip salt counter-ions to match parent mass. |
| `require_parent_mass_match_smiles(s, mass_tolerance=0.1)` | `None` if parent mass ≠ SMILES-derived mass. |
| `require_valid_annotation(s)` | `None` unless SMILES/InChI/InChIKey are present and consistent. |

## Peak processing

| Filter | Purpose |
| --- | --- |
| `normalize_intensities(s)` | Scale peaks so max intensity = 1.0. Do this before relative-intensity selection and most scoring. |
| `select_by_intensity(s, intensity_from=0.0, intensity_to=1.0)` | Keep peaks in an **absolute** intensity range. |
| `select_by_relative_intensity(s, intensity_from=0.0, intensity_to=1.0)` | Keep peaks as a fraction of the max intensity. |
| `select_by_mz(s, mz_from=0.0, mz_to=1000.0)` | Keep peaks in an m/z window. |
| `reduce_to_number_of_peaks(s, n_max=None, ratio_desired=None)` | Drop weakest peaks past a cap. |
| `remove_peaks_around_precursor_mz(s, mz_tolerance=17)` | Remove precursor + isotope peaks; common before fragment-based scoring. |
| `remove_peaks_outside_top_k(s, k=10, ratio_desired=None)` | Keep only peaks near the k most intense. |
| `add_losses(s, loss_mz_from=5.0, loss_mz_to=200.0)` | Compute neutral losses (`precursor_mz - fragment_mz`) for `NeutralLossesCosine`. |

## Quality gates (return `None` on failure)

| Filter | Rejects when |
| --- | --- |
| `require_minimum_number_of_peaks(s, n_required=10)` | fewer than `n_required` peaks. |
| `require_minimum_number_of_high_peaks(s, n_required=5, intensity_threshold=0.05)` | too few peaks above the threshold. |
| `require_precursor_mz(s, minimum_accepted_mz=0.0)` | precursor m/z missing or below threshold. |
| `require_precursor_below_mz(s, maximum_accepted_mz=1000.0)` | precursor m/z above threshold. |

## Standard combinations

Basic preprocessing:
```python
from matchms.filtering import (default_filters, normalize_intensities,
    select_by_relative_intensity, require_minimum_number_of_peaks)

s = default_filters(s)
s = normalize_intensities(s)
s = select_by_relative_intensity(s, intensity_from=0.01)
s = require_minimum_number_of_peaks(s, n_required=5)   # may be None
```

Quality control (guard each gate):
```python
s = require_precursor_mz(s, minimum_accepted_mz=50.0)
if s is None: return
s = require_minimum_number_of_peaks(s, n_required=10)
if s is None: return
s = require_minimum_number_of_high_peaks(s, n_required=5, intensity_threshold=0.05)
```

Chemical annotation (needs RDKit):
```python
s = derive_inchi_from_smiles(s)
s = derive_inchikey_from_inchi(s)
s = add_fingerprint(s, fingerprint_type="morgan2", nbits=2048)
s = require_valid_annotation(s)
```

Peak cleaning:
```python
s = normalize_intensities(s)
s = remove_peaks_around_precursor_mz(s, mz_tolerance=17)
s = select_by_relative_intensity(s, intensity_from=0.01)
s = reduce_to_number_of_peaks(s, n_max=200)
```

## Notes

- **Reassign, don't mutate in place** — filters return copies.
- **Order dependence** — normalize before relative selection; add losses /
  fingerprints before the scorer that consumes them; harmonize metadata (via
  `default_filters`) before anything that reads it.
- **Chain intent** — apply the *same* filter chain to references and queries.
- Full parameter list:
  `https://matchms.readthedocs.io/en/latest/api/matchms.filtering.html`.

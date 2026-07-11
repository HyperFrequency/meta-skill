# Importing & Exporting Spectra

matchms reads and writes the common MS/MS exchange formats. All `load_from_*`
functions return a **generator** — wrap in `list(...)` to materialize, or
iterate directly to stream large files without holding everything in memory.
Most importers accept `metadata_harmonization=True` (default), which normalizes
metadata keys to matchms conventions (e.g. `PRECURSOR_MZ`, `Precursor_mz`,
`precursormz` → `precursor_mz`). Keep it on unless you have a specific reason.

## Import functions (`matchms.importing`)

| Function | Signature | Notes |
| --- | --- | --- |
| `load_from_mgf` | `load_from_mgf(filename, metadata_harmonization=True)` | Mascot Generic Format; `BEGIN IONS`/`END IONS` blocks. Common exchange format. |
| `load_from_msp` | `load_from_msp(filename, metadata_harmonization=True)` | NIST/MoNA spectral-library text format. |
| `load_from_mzml` | `load_from_mzml(filename, ms_level=2, metadata_harmonization=True)` | XML raw-data standard. `ms_level=2` for MS/MS, `1` for MS1. |
| `load_from_mzxml` | `load_from_mzxml(filename, ms_level=2, metadata_harmonization=True)` | Older XML raw format, predecessor to mzML. |
| `load_from_json` | `load_from_json(filename, metadata_harmonization=True)` | GNPS-compatible JSON. |
| `load_from_usi` | `load_from_usi(usi, server=...)` | Fetch a single spectrum by Universal Spectrum Identifier from an online repository. |
| `load_from_pickle` | `load_from_pickle(filename)` | Reload previously saved matchms `Spectrum` objects. Fastest; not portable. |

```python
from matchms.importing import load_from_mgf, load_from_mzml

spectra = list(load_from_mgf("data.mgf"))                 # materialize
ms2 = list(load_from_mzml("run.mzML", ms_level=2))        # MS/MS only

# Stream a large file without loading it all:
for spectrum in load_from_mgf("huge_library.mgf"):
    ...  # process one at a time
```

Loading many files from a directory:

```python
import glob
all_spectra = []
for path in glob.glob("data/*.mgf"):
    all_spectra.extend(load_from_mgf(path))
```

## Export functions (`matchms.exporting`)

| Function | Signature | Notes |
| --- | --- | --- |
| `save_as_mgf` | `save_as_mgf(spectra, filename)` | Widely supported, human-readable, good for sharing / GNPS uploads. |
| `save_as_msp` | `save_as_msp(spectra, filename)` | Spectral-library format; strong metadata support. |
| `save_as_json` | `save_as_json(spectra, filename)` | Structured, GNPS-compatible; easy to parse. |
| `save_as_pickle` | `save_as_pickle(spectra, filename)` | Fastest save/load, preserves exact state; Python-only, not human-readable, may break across Python versions. |

```python
from matchms.exporting import save_as_mgf, save_as_pickle

save_as_mgf(processed, "clean.mgf")       # portable
save_as_pickle(processed, "clean.pkl")    # fast reload for later runs
```

Export takes a **list** of `Spectrum` objects (materialize the generator first).
Some writers support an append mode (e.g. `write_mode="a"`) for incremental
output; confirm the argument name in your installed version if you rely on it.

## Choosing a format

- **MGF** — default for sharing and publication; broad tool support.
- **MSP** — reference libraries, NIST-style compatibility.
- **JSON** — GNPS integration, programmatic/structured consumption.
- **Pickle** — intermediate cache of preprocessed spectra in a Python-only
  pipeline; never for archival or cross-tool exchange.
- **mzML / mzXML** — read raw instrument data in; rarely a write target from
  matchms (large, and matchms works on processed spectra).

## Format conversion

```python
from matchms.importing import load_from_mzml
from matchms.exporting import save_as_mgf, save_as_msp

spectra = list(load_from_mzml("data.mzML", ms_level=2))
save_as_mgf(spectra, "data.mgf")
save_as_msp(spectra, "data.msp")
```

## Failure modes

- **Empty result.** A generator consumed twice yields nothing the second time —
  re-load or keep the materialized list.
- **Wrong MS level.** `load_from_mzml`/`load_from_mzxml` default to `ms_level=2`;
  set `ms_level=1` if you need survey scans.
- **Metadata key surprises.** With `metadata_harmonization=False` you get raw
  vendor keys and `spectrum.get("precursor_mz")` may return `None`.
- **Pickle portability.** Do not ship `.pkl` between environments with different
  matchms/Python/NumPy versions; use MGF/MSP/JSON for exchange.

Official docs:
`https://matchms.readthedocs.io/en/latest/api/matchms.importing.html` and
`https://matchms.readthedocs.io/en/latest/api/matchms.exporting.html`.

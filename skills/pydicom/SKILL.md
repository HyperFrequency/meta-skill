---
name: pydicom
version: 0.1.0
description: >-
  Read, write, and manipulate DICOM (Digital Imaging and Communications in
  Medicine) files with pydicom, the pure-Python medical-imaging format library.
  Use when parsing DICOM datasets and tags, extracting or windowing pixel data
  from CT/MRI/X-ray/ultrasound/PET scans, decompressing or compressing pixel
  data (JPEG, JPEG 2000, JPEG-LS, RLE), de-identifying PHI, converting DICOM to
  PNG/JPEG/TIFF, stacking a slice series into a 3D volume, or authoring DICOM
  from NumPy arrays. Covers the pydicom 3.x API shift (pydicom.pixels module,
  enforce_file_format). Do NOT use for non-DICOM medical formats (NIfTI, NRRD,
  Analyze — use nibabel), DICOM network transfer / PACS C-STORE/C-FIND (use
  pynetdicom), 3D registration or morphological processing (use SimpleITK/ITK),
  or as an ML training pipeline (feed the extracted arrays to your framework).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (pydicom)"
---

# Pydicom

## Overview

`pydicom` is a pure-Python library for reading, modifying, and writing DICOM,
the standard container for medical imaging (CT, MR, X-ray, US, PET, etc.). A
DICOM file is a flat-ish `Dataset` of tagged data elements plus, usually, an
encoded pixel-data blob and a small `file_meta` header that names the
**transfer syntax** (byte order + compression). This skill routes the common
tasks: pull tags, decode and window pixels correctly, edit and de-identify,
compress/decompress, reconstruct volumes, and create files from scratch.

Install with `uv pip install pydicom numpy pillow`. Pixel access needs NumPy;
compressed pixels need extra plugins — see
[references/transfer_syntaxes.md](references/transfer_syntaxes.md).

> Version note: this skill targets **pydicom 3.x**. In 3.0 the pixel utilities
> moved from `pydicom.pixel_data_handlers` to `pydicom.pixels` (old path
> deprecated, removed in 4.0), and `save_as(..., write_like_original=...)` is
> superseded by `enforce_file_format`. Both old and new forms are shown where it
> matters; prefer the new one on new code.

## When to Use This Skill

- Reading `.dcm` files and inspecting/editing DICOM tags and metadata.
- Extracting pixel arrays and displaying them with **correct** grayscale
  transforms (Modality LUT / rescale to HU, then VOI LUT / windowing).
- Decompressing or compressing pixel data (JPEG, JPEG-LS, JPEG 2000, RLE).
- De-identifying / anonymizing Protected Health Information (PHI).
- Converting DICOM slices to PNG/JPEG/TIFF.
- Sorting a directory of slices into an ordered 3D volume with real voxel sizes.
- Authoring new DICOM datasets from NumPy arrays.

## When NOT to Use This Skill

- **Non-DICOM neuroimaging/volumetric formats** (NIfTI, NRRD, MINC, Analyze) —
  use `nibabel` / SimpleITK, not pydicom.
- **DICOM networking / PACS** (C-STORE, C-FIND, C-MOVE, DICOMweb) — that is
  `pynetdicom` or a DICOMweb client, not this library.
- **Registration, resampling, segmentation, filtering** on volumes — use
  SimpleITK/ITK or scikit-image; pydicom only gets you the array.
- **Model training** — decode arrays here, then hand off to your ML framework
  (`scikit-learn`, PyTorch, etc.); pixel loading is not this skill's job at scale.
- **Trusting a fixed-tag scrub as real de-identification** — see the safety note
  under Editing & De-identification.

## Reading & Inspecting

```python
import pydicom

ds = pydicom.dcmread("scan.dcm")          # -> Dataset
print(ds.PatientName, ds.Modality, ds.StudyDate)
print(ds)                                  # full dump of all elements
print(ds.file_meta.TransferSyntaxUID.name) # e.g. "Explicit VR Little Endian"
```

Access elements by keyword (`ds.PatientName`) or by tag (`ds[0x0010, 0x0010].value`).
Guard optional tags — missing keywords raise `AttributeError`:

```python
name    = ds.get("PatientName", "Unknown")      # safe, returns default
present = "WindowCenter" in ds                    # membership test
```

Use `pydicom.dcmread(path, stop_before_pixels=True)` to read tags fast without
decoding pixels, and `defer_size="1 KB"` to lazily load large elements. The full
tag dictionary (categories, VRs, standard values) lives in
[references/common_tags.md](references/common_tags.md).

## Pixel Data — Decode It Correctly

`ds.pixel_array` returns the **raw stored** values as a NumPy array. Do not feed
that straight to a viewer for CT/MR — apply the grayscale pipeline in order:
**(1) Modality LUT / rescale** (stored value → physical units, e.g. Hounsfield),
then **(2) VOI LUT / windowing** for display contrast.

```python
import pydicom
from pydicom.pixels import apply_modality_lut, apply_voi_lut  # pydicom 3.x

ds  = pydicom.dcmread("ct.dcm")
raw = ds.pixel_array                       # shape (Rows, Columns)
hu  = apply_modality_lut(raw, ds)          # applies RescaleSlope/Intercept
disp = apply_voi_lut(hu, ds, index=0)      # WindowCenter/Width or VOI LUT
```

On pydicom < 3.0 import from `pydicom.pixel_data_handlers.util` instead. Multi-
frame data comes back as `(frames, rows, cols)`; color data as `(rows, cols, 3)`
— convert `YBR_FULL`/`YBR_FULL_422` to RGB with
`pydicom.pixels.convert_color_space`. Shapes, dtypes, color handling, and the
`pixel_array_options()` control knobs are in
[references/recipes.md](references/recipes.md#pixel-data). Hand finished arrays
to the `matplotlib` or `scientific-visualization` skill for figures.

## Editing & De-identification

Mutate the dataset in place, then save. Prefer `enforce_file_format=True`
(pydicom 3.x) over the deprecated `write_like_original=False` to guarantee a
compliant file-meta header on output:

```python
ds.StudyDescription = "Edited"
del ds.PatientComments                      # remove an element (if present)
ds.save_as("edited.dcm", enforce_file_format=True)
```

**De-identification safety.** Deleting a fixed list of keywords (PatientName,
PatientID, …) is a *starting point, not compliance*. Real de-identification per
DICOM **PS3.15 Annex E** must also handle: UIDs (regenerate consistently to keep
referential integrity), private tags, the whole tag tree inside sequences,
`StructuredReport`/OCR text, and **burned-in pixel annotations** (text baked into
the image itself — deleting tags does nothing for those). Always verify the
output and inspect pixels before sharing. A worked scrubber with the extended PHI
list and its caveats is in
[references/recipes.md](references/recipes.md#de-identification).

## Compression, Volumes & Authoring

- **Compress/decompress**: `ds.decompress()` / `ds.compress(pydicom.uid.RLELossless)`,
  or the 3.x functional forms `pydicom.pixels.decompress` / `.compress`. Which
  transfer syntax needs which plugin (`pylibjpeg-*`, `python-gdcm`, `pillow`; RLE
  needs none) is tabulated in
  [references/transfer_syntaxes.md](references/transfer_syntaxes.md).
- **Slice series → 3D volume**: read a directory, sort by
  `ImagePositionPatient[2]` (or `InstanceNumber`), `np.stack` the arrays, and
  read `PixelSpacing` + `SliceThickness` for real voxel size. Full loop in
  [references/recipes.md](references/recipes.md#series-to-volume).
- **Author from scratch**: build `file_meta`, a `FileDataset`, set the required
  Image-module tags, assign `PixelData = arr.tobytes()`, generate UIDs with
  `pydicom.uid.generate_uid()`. Template in
  [references/recipes.md](references/recipes.md#creating-a-dataset).

## Common Failure Modes

- **"Unable to decode pixel data"** → the transfer syntax needs a plugin that
  is not installed (see transfer_syntaxes reference); RLE always works.
- **Image too dark/bright/inverted** → you skipped the Modality/VOI pipeline, or
  `PhotometricInterpretation` is `MONOCHROME1` (min = white) — invert for display.
- **`AttributeError` on a tag** → use `ds.get(...)` / `in`, not bare attribute
  access; the tag is simply absent in that dataset.
- **Deprecation warnings** → migrate `pixel_data_handlers` imports to
  `pydicom.pixels` and `write_like_original` to `enforce_file_format`.

## References

- [references/common_tags.md](references/common_tags.md) — DICOM tag dictionary
  by module (Patient/Study/Series/Image/CT/MR/…) and Value Representations.
- [references/transfer_syntaxes.md](references/transfer_syntaxes.md) — transfer
  syntax UIDs, compression tradeoffs, and which plugin each format requires.
- [references/recipes.md](references/recipes.md) — runnable recipes: pixel
  decoding, DICOM→PNG/JPEG, de-identification, series→volume, dataset authoring,
  metadata dumps, and pydicom 2.x→3.x migration notes.

Official docs: https://pydicom.github.io/pydicom/stable/

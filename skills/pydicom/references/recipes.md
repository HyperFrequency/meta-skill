# Pydicom Recipes

Runnable recipes for the tasks the SKILL router points here for. All target
**pydicom 3.x**; legacy equivalents are called out inline. Install:

```bash
uv pip install pydicom numpy pillow
# compressed pixels also need a decoder plugin — see transfer_syntaxes.md
```

---

## Pixel Data

`Dataset.pixel_array` decodes the stored pixel data into a NumPy array,
automatically decompressing if the required plugin is installed.

```python
import pydicom

ds = pydicom.dcmread("image.dcm")
arr = ds.pixel_array
print(arr.shape, arr.dtype)          # (Rows, Columns) for a single grayscale frame
print(ds.Rows, ds.Columns, ds.BitsStored, ds.PhotometricInterpretation)
```

### Shape by content

| Content | `pixel_array.shape` |
|---|---|
| Single grayscale frame | `(rows, cols)` |
| Single color frame | `(rows, cols, 3)` |
| Multi-frame grayscale | `(frames, rows, cols)` |
| Multi-frame color | `(frames, rows, cols, 3)` |

### Correct grayscale pipeline

Apply transforms in this order; skipping them is the usual cause of "wrong
looking" CT/MR images.

```python
from pydicom.pixels import apply_modality_lut, apply_voi_lut   # pydicom 3.x
# pydicom <3.0: from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut

hu   = apply_modality_lut(ds.pixel_array, ds)   # stored value -> physical (e.g. HU)
disp = apply_voi_lut(hu, ds, index=0)           # windowing for display
```

`MONOCHROME1` means minimum sample value displays as **white** — invert
(`disp.max() - disp`) before showing it in a normal grayscale colormap.

### Color frames

```python
from pydicom.pixels import convert_color_space

arr = ds.pixel_array
if ds.PhotometricInterpretation in ("YBR_FULL", "YBR_FULL_422"):
    arr = convert_color_space(arr, ds.PhotometricInterpretation, "RGB")
```

### Controlling the decode (pydicom 3.x)

`Dataset.pixel_array_options(...)` tunes the new decoding backend before you
touch `pixel_array` — e.g. select a decoding plugin, request a specific frame,
or get raw (untransformed) output. Use it when the default plugin choice fails
or you need only one frame of a large multi-frame file.

---

## DICOM to PNG / JPEG / TIFF

Grayscale medical pixels are usually 12–16 bit and must be normalized to 8-bit
before saving to a standard image format. Do this from the **display** array
(after windowing) so contrast is meaningful.

```python
import pydicom, numpy as np
from PIL import Image
from pydicom.pixels import apply_voi_lut

def dicom_to_image(in_path, out_path, frame=0, window=True):
    ds  = pydicom.dcmread(in_path)
    arr = ds.pixel_array
    if arr.ndim >= 3 and arr.shape[0] > 1 and arr.shape[-1] not in (3, 4):
        arr = arr[frame]                       # pick one frame of a multi-frame series
    if window and "WindowCenter" in ds:
        arr = apply_voi_lut(arr, ds)
    if arr.ndim == 2:                          # grayscale -> normalize to uint8
        lo, hi = arr.min(), arr.max()
        arr = ((arr - lo) / (hi - lo) * 255).astype(np.uint8) if hi > lo \
              else np.zeros_like(arr, dtype=np.uint8)
        Image.fromarray(arr, mode="L").save(out_path)
    else:                                      # already color
        Image.fromarray(arr).save(out_path)
```

`Image.save` infers the format from the extension; pass `format="JPEG"` to force
it. For an interactive figure, hand the array to the `matplotlib` skill instead
of writing a file.

---

## De-identification

> **This is a scrub template, not a compliance guarantee.** DICOM PS3.15 Annex E
> requires handling UIDs, private tags, nested sequences, structured-report text,
> and **burned-in pixel annotations** (text rendered into the image — invisible
> to any tag-based scrub). Always verify output and inspect pixels before sharing
> patient data. For regulated workflows use a validated de-identifier (e.g. the
> DICOM standard profiles / `deid` / `dcm4che`) rather than an ad-hoc list.

```python
import pydicom

# Direct-identifier keywords (extend per your PS3.15 profile / local policy)
PHI_KEYWORDS = [
    "PatientName", "PatientID", "PatientBirthDate", "PatientBirthTime",
    "PatientSex", "PatientAge", "PatientSize", "PatientWeight",
    "PatientAddress", "PatientTelephoneNumbers", "PatientMotherBirthName",
    "MilitaryRank", "EthnicGroup", "Occupation", "PatientComments",
    "InstitutionName", "InstitutionAddress", "InstitutionalDepartmentName",
    "ReferringPhysicianName", "PerformingPhysicianName", "OperatorsName",
    "PhysiciansOfRecord", "NameOfPhysiciansReadingStudy",
    "StudyDescription", "SeriesDescription", "AdmittingDiagnosesDescription",
    "RequestingPhysician", "RequestedProcedureDescription",
    "ScheduledPerformingPhysicianName", "PerformedStationName",
]

def deidentify(in_path, out_path, patient_id="ANON", patient_name="ANONYMOUS"):
    ds = pydicom.dcmread(in_path)
    for kw in PHI_KEYWORDS:
        if kw not in ds:
            continue
        if kw == "PatientName":     ds.PatientName = patient_name
        elif kw == "PatientID":     ds.PatientID = patient_id
        elif kw == "PatientBirthDate": ds.PatientBirthDate = "19000101"
        else:                       delattr(ds, kw)
    ds.remove_private_tags()        # drop vendor private data
    # Regenerate UIDs consistently if you must break linkage to the source study:
    # ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.save_as(out_path, enforce_file_format=True)
```

`Dataset.walk(callback)` lets you recurse into sequences to scrub nested items;
a fixed top-level loop misses PHI buried inside `SQ` elements.

---

## Series to Volume

Sort a folder of single-slice files into a spatially ordered 3D array.

```python
import pydicom, numpy as np
from pathlib import Path

slices = [pydicom.dcmread(p) for p in Path("series/").glob("*.dcm")]
slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))  # by z-position
# fallback when position is absent: key=lambda s: int(s.InstanceNumber)

volume = np.stack([s.pixel_array for s in slices])           # (n_slices, rows, cols)
row_sp, col_sp = map(float, slices[0].PixelSpacing)
z_sp = float(slices[0].SliceThickness)
print("voxel size (mm):", row_sp, col_sp, z_sp)
```

Caveats: verify all slices share one `SeriesInstanceUID`, guard against missing
`ImagePositionPatient`, and check for non-uniform slice spacing (gaps/overlaps)
before treating the stack as an isotropic grid. For resampling to isotropic
voxels or any registration, move the array into SimpleITK/ITK.

---

## Creating a Dataset

Minimal secondary-capture-style file authored from a NumPy array. Populate the
required Image-module attributes or the file will not be readable elsewhere.

```python
import pydicom, numpy as np
from pydicom.dataset import Dataset, FileDataset
from datetime import datetime

file_meta = Dataset()
file_meta.MediaStorageSOPClassUID    = pydicom.uid.CTImageStorage
file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
file_meta.TransferSyntaxUID          = pydicom.uid.ExplicitVRLittleEndian

ds = FileDataset("new.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
ds.PatientName = "Test^Patient"; ds.PatientID = "000000"; ds.Modality = "CT"
ds.StudyInstanceUID  = pydicom.uid.generate_uid()
ds.SeriesInstanceUID = pydicom.uid.generate_uid()
ds.SOPClassUID    = file_meta.MediaStorageSOPClassUID
ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
ds.StudyDate = datetime.now().strftime("%Y%m%d")

# Image pixel module
ds.SamplesPerPixel = 1
ds.PhotometricInterpretation = "MONOCHROME2"
ds.Rows, ds.Columns = 512, 512
ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 16, 15
ds.PixelRepresentation = 0
ds.PixelData = np.random.randint(0, 4096, (512, 512), dtype=np.uint16).tobytes()

ds.save_as("new.dcm", enforce_file_format=True)
```

---

## Metadata Dump

Iterate elements for a readable report or JSON. `elem.keyword`, `elem.name`,
`elem.VR`, and `elem.value` are the fields you want; `VR == "SQ"` marks a nested
sequence.

```python
import pydicom, json

ds = pydicom.dcmread("scan.dcm")

# Human-readable
for elem in ds:
    if elem.VR != "SQ":
        print(f"{elem.name:40s} {elem.value}")

# JSON (top-level, non-sequence elements)
flat = {e.keyword: str(e.value) for e in ds if e.VR != "SQ" and e.keyword}
print(json.dumps(flat, indent=2))
```

pydicom also ships native DICOM-JSON via `ds.to_json()` / `Dataset.from_json()`
when you need the standard model rather than an ad-hoc flattening.

---

## pydicom 2.x → 3.x Migration Notes

| 2.x | 3.x | Notes |
|---|---|---|
| `from pydicom.pixel_data_handlers.util import apply_voi_lut, apply_modality_lut, convert_color_space` | `from pydicom.pixels import ...` | Old module deprecated in 3.0, removed in 4.0. |
| `ds.save_as(path, write_like_original=False)` | `ds.save_as(path, enforce_file_format=True)` | `write_like_original` removed in 4.0; `enforce_file_format=True` writes a conformant file-meta header. |
| `ds.decompress()` / `ds.compress(uid)` | still valid; also `pydicom.pixels.decompress(ds)` / `pydicom.pixels.compress(ds, uid)` | Functional forms use the new backend. |
| implicit backend | `ds.pixel_array_options(...)` | Explicitly pick decoding plugin / options. |

## Troubleshooting

- **`AttributeError` reading a tag** → the element is absent; use `ds.get(kw)` or
  `kw in ds`.
- **"Unable to decode pixel data"** → missing decoder plugin for the transfer
  syntax (see transfer_syntaxes.md); `python-gdcm` covers the most formats.
- **Wrong window/contrast** → apply Modality LUT then VOI LUT; check for
  `MONOCHROME1`.
- **Reads slowly / large files** → `dcmread(path, stop_before_pixels=True)` for
  tags only, or `defer_size=...` to lazily load big elements.
- **Round-trip file rejected by other tools** → save with
  `enforce_file_format=True` so the preamble and file-meta group are written.

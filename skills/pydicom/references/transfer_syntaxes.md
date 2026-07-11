# DICOM Transfer Syntaxes & Compression

The **Transfer Syntax UID** in `ds.file_meta.TransferSyntaxUID` fixes how a
dataset is encoded: byte order, implicit vs explicit VR, and the pixel-data
compression (if any). You must know it before decoding pixels, because each
compressed format needs a specific decoder plugin installed.

Inspect it:

```python
ts = ds.file_meta.TransferSyntaxUID
print(ts, ts.name)              # e.g. "1.2.840.10008.1.2.1  Explicit VR Little Endian"
print(ts.is_compressed, ts.is_little_endian, ts.is_implicit_VR)
```

## Uncompressed

| UID | pydicom constant | Notes |
|-----|------------------|-------|
| 1.2.840.10008.1.2 | `ImplicitVRLittleEndian` | Standard default; VR is implicit |
| 1.2.840.10008.1.2.1 | `ExplicitVRLittleEndian` | Most common; use for new files |
| 1.2.840.10008.1.2.2 | `ExplicitVRBigEndian` | **Retired** — avoid |
| 1.2.840.10008.1.2.1.99 | `DeflatedExplicitVRLittleEndian` | Whole-dataset zlib; rare |

## Compressed

| UID | pydicom constant | Loss | Plugin needed |
|-----|------------------|------|---------------|
| …1.2.4.50 | `JPEGBaseline8Bit` | Lossy, 8-bit | `pylibjpeg-libjpeg` or `pillow` |
| …1.2.4.51 | `JPEGExtended12Bit` | Lossy, 8/12-bit | `pylibjpeg-libjpeg` or `gdcm` |
| …1.2.4.57 | `JPEGLossless` | Lossless | `pylibjpeg-libjpeg` or `gdcm` |
| …1.2.4.70 | `JPEGLosslessSV1` | Lossless | `pylibjpeg-libjpeg` or `gdcm` |
| …1.2.4.80 | `JPEGLSLossless` | Lossless | `pylibjpeg-libjpeg` or `gdcm` |
| …1.2.4.81 | `JPEGLSNearLossless` | Near-lossless | `pylibjpeg-libjpeg` or `gdcm` |
| …1.2.4.90 | `JPEG2000Lossless` | Lossless | `pylibjpeg-openjpeg`, `gdcm`, or `pillow` |
| …1.2.4.91 | `JPEG2000` | Lossy/lossless | `pylibjpeg-openjpeg`, `gdcm`, or `pillow` |
| …1.2.5 | `RLELossless` | Lossless | **none — built in** |
| …1.2.4.100/101 | `MPEG2MPML` / `MPEG2MPHL` | Lossy video | `gdcm` / `pyav` |
| …1.2.4.102–106 | MPEG-4 AVC/H.264 | Lossy video | `gdcm` / `pyav` |

(Prefix every `…` with `1.2.840.10008`.)

## Installing decoder plugins

```bash
# broadest single dependency
uv pip install python-gdcm

# or the pylibjpeg family (JPEG / JPEG-LS / JPEG 2000)
uv pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg
```

RLE needs nothing extra. If you cannot install native deps at all, RLE is the
only compression you can read and write out of the box.

## Decompressing

```python
import pydicom
ds = pydicom.dcmread("compressed.dcm")

arr = ds.pixel_array           # auto-decompresses if the plugin is present
ds.decompress()                # in-place; converts pixel data to uncompressed
ds.save_as("plain.dcm", enforce_file_format=True)   # pydicom 3.x
```

pydicom 3.x also exposes the functional form `pydicom.pixels.decompress(ds)`,
which uses the new decoding backend.

## Compressing

```python
import pydicom
ds = pydicom.dcmread("plain.dcm")

ds.compress(pydicom.uid.RLELossless)            # no extra deps
ds.save_as("rle.dcm", enforce_file_format=True)

ds.compress(pydicom.uid.JPEG2000Lossless)       # needs a J2K plugin
ds.compress(pydicom.uid.JPEGBaseline8Bit,       # optionally pin the encoder
            encoding_plugin="pylibjpeg")
```

Functional equivalent: `pydicom.pixels.compress(ds, pydicom.uid.RLELossless)`.

## Choosing a syntax

- **New files for interoperability** → `ExplicitVRLittleEndian`.
- **Archive without quality loss** → `JPEG2000Lossless` (best ratio) or
  `RLELossless` (zero external deps).
- **Diagnostic images** → never lossy; regulators and radiologists reject
  lossy-compressed primary diagnostic data.
- **Constrained environment** → `RLELossless`, since it needs no plugin.

## Failure modes

- **"Unable to decode pixel data"** → decoder plugin for that syntax is not
  installed; install `python-gdcm` (widest coverage) and retry.
- **"Unsupported Transfer Syntax"** → uncommon/retired format; `python-gdcm`
  handles the most edge cases.
- **Decoded but looks wrong** → decoding succeeded but you still need the
  Modality LUT / VOI LUT display pipeline (see recipes.md).

## References

- DICOM PS3.5 (encoding): https://dicom.nema.org/medical/dicom/current/output/chtml/part05/PS3.5.html
- pydicom pixel-data guide: https://pydicom.github.io/pydicom/stable/guides/user/index.html

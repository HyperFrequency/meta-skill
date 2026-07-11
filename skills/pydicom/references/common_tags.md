# DICOM Tag Dictionary

Frequently used DICOM data elements grouped by information module, plus the
Value Representation (VR) table. Tag numbers, keywords, and VRs are defined by
the DICOM standard (Part 6). In pydicom, reach an element by keyword
(`ds.PatientName`) or by group/element tag (`ds[0x0010, 0x0010].value`).

Use the full tag browser at https://dicom.innolitics.com/ciods for anything not
listed here.

## Patient

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (0010,0010) | PatientName | PN | Patient's full name |
| (0010,0020) | PatientID | LO | Primary patient identifier |
| (0010,0030) | PatientBirthDate | DA | Date of birth (YYYYMMDD) |
| (0010,0040) | PatientSex | CS | M / F / O |
| (0010,1010) | PatientAge | AS | Age (nnnD/W/M/Y) |
| (0010,1020) | PatientSize | DS | Height (m) |
| (0010,1030) | PatientWeight | DS | Weight (kg) |
| (0010,1040) | PatientAddress | LO | Mailing address |
| (0010,4000) | PatientComments | LT | Free-text comments |

## Study

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (0020,000D) | StudyInstanceUID | UI | Unique study identifier |
| (0008,0020) | StudyDate | DA | Study start date |
| (0008,0030) | StudyTime | TM | Study start time |
| (0008,1030) | StudyDescription | LO | Study description |
| (0020,0010) | StudyID | SH | Site-defined study ID |
| (0008,0050) | AccessionNumber | SH | RIS-generated identifier |
| (0008,0090) | ReferringPhysicianName | PN | Referring physician |

## Series

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (0020,000E) | SeriesInstanceUID | UI | Unique series identifier |
| (0020,0011) | SeriesNumber | IS | Series index |
| (0008,103E) | SeriesDescription | LO | Series description |
| (0008,0060) | Modality | CS | CT, MR, US, XR, PT, … |
| (0018,0015) | BodyPartExamined | CS | Body part |
| (0018,5100) | PatientPosition | CS | HFS, FFS, … |
| (0020,0060) | Laterality | CS | R / L |

## Image / Instance

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (0008,0018) | SOPInstanceUID | UI | Unique instance identifier |
| (0020,0013) | InstanceNumber | IS | Image number within series |
| (0008,0008) | ImageType | CS | Image characteristics |
| (0020,0032) | ImagePositionPatient | DS | (x,y,z) of top-left voxel (mm) |
| (0020,0037) | ImageOrientationPatient | DS | Row/column direction cosines |
| (0020,1041) | SliceLocation | DS | Relative slice position |
| (0018,0050) | SliceThickness | DS | Slice thickness (mm) |
| (0018,0088) | SpacingBetweenSlices | DS | Slice spacing (mm) |

## Pixel Module

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (7FE0,0010) | PixelData | OB/OW | Encoded pixel data |
| (0028,0010) | Rows | US | Image height |
| (0028,0011) | Columns | US | Image width |
| (0028,0100) | BitsAllocated | US | Bits per sample container |
| (0028,0101) | BitsStored | US | Bits actually used |
| (0028,0102) | HighBit | US | Most-significant bit position |
| (0028,0103) | PixelRepresentation | US | 0 = unsigned, 1 = signed |
| (0028,0002) | SamplesPerPixel | US | 1 (gray) or 3 (color) |
| (0028,0004) | PhotometricInterpretation | CS | MONOCHROME1/2, RGB, YBR_* |
| (0028,0006) | PlanarConfiguration | US | Color sample interleaving |
| (0028,0030) | PixelSpacing | DS | [row, col] spacing (mm) |
| (0028,0008) | NumberOfFrames | IS | Frame count (multi-frame) |

## Display / Rescale

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (0028,1050) | WindowCenter | DS | Display window center |
| (0028,1051) | WindowWidth | DS | Display window width |
| (0028,1052) | RescaleIntercept | DS | b in output = m·SV + b |
| (0028,1053) | RescaleSlope | DS | m in output = m·SV + b |
| (0028,1054) | RescaleType | LO | Units after rescale (e.g. HU) |
| (0028,3010) | VOILUTSequence | SQ | VOI LUT description |

`RescaleSlope`/`RescaleIntercept` are what `apply_modality_lut` uses;
`WindowCenter`/`WindowWidth` (or the VOI LUT sequence) drive `apply_voi_lut`.

## File Meta (group 0002)

| Tag | Keyword | VR | Meaning |
|-----|---------|----|---------|
| (0002,0002) | MediaStorageSOPClassUID | UI | SOP Class UID |
| (0002,0003) | MediaStorageSOPInstanceUID | UI | SOP Instance UID |
| (0002,0010) | TransferSyntaxUID | UI | Encoding / compression |

Access these via `ds.file_meta`, not the main dataset.

## Modality Extras

- **CT**: KVP (0018,0060), XRayTubeCurrent (0018,1151), Exposure (0018,1152),
  ConvolutionKernel (0018,1210), GantryDetectorTilt (0018,1120).
- **MR**: RepetitionTime/TR (0018,0080), EchoTime/TE (0018,0081),
  InversionTime/TI (0018,0082), MagneticFieldStrength (0018,0087),
  FlipAngle (0018,1314), EchoTrainLength (0018,0091).

## Value Representations (VR)

| VR | Meaning | VR | Meaning |
|----|---------|----|---------|
| AE | Application Entity | PN | Person Name |
| AS | Age String | SH | Short String (≤16) |
| CS | Code String (≤16) | SQ | Sequence of Items |
| DA | Date (YYYYMMDD) | ST | Short Text (≤1024) |
| DS | Decimal String | TM | Time (HHMMSS.FFFFFF) |
| DT | Date Time | UI | Unique Identifier (UID) |
| IS | Integer String | UL | Unsigned Long (4 B) |
| LO | Long String (≤64) | US | Unsigned Short (2 B) |
| LT | Long Text (≤10240) | OB/OW | Other Byte / Word String |

## Access Patterns

```python
name  = ds.PatientName                 # by keyword
name  = ds[0x0010, 0x0010].value       # by tag number
safe  = ds.get("StudyDescription", "") # default if absent
exists = (0x0010, 0x0010) in ds        # membership by tag
```

## References

- DICOM standard: https://www.dicomstandard.org/
- Tag browser: https://dicom.innolitics.com/ciods
- pydicom docs: https://pydicom.github.io/pydicom/stable/

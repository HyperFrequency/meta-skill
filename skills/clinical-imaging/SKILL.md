---
name: clinical-imaging
version: 0.1.0
description: >-
  Analyze clinical and physiological imaging data with the scientific-Python
  stack. Covers diffusion-MRI ADC maps (monoexponential fit over b-values),
  micro-CT bone morphometry (BV/TV, Tb.Th/Sp/N, Ct.Th), hemodynamic parameters
  from arterial pressure waveforms (systolic/diastolic, MAP, pulse pressure,
  heart rate), circadian cosinor fits (MESOR, amplitude, acrophase, rhythm
  F-test), ciliary beat frequency via FFT, tissue-deformation optical flow
  (strain, divergence, curl), and amyloid-plaque quantification from
  fluorescence microscopy. Use when you have raw NIfTI/CT volumes, biosignal
  waveforms, or microscopy images and need quantitative biomarkers with correct
  units. NOT for DICOM file I/O (use pydicom), general ECG/EMG/EDA biosignal
  pipelines (use neurokit2), generic bioimage segmentation, or model training —
  this owns the domain-specific computations, not file plumbing or ML.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "methods only; built on scipy/scikit-image (BSD-3-Clause), nibabel (MIT), OpenCV (Apache-2.0)"
---

# Clinical and Physiological Imaging Analysis

## Overview

This skill is a **router** for quantitative analysis of clinical and
physiological imaging data. Each capability turns a raw acquisition — a
diffusion-MRI series, a micro-CT volume, an arterial pressure trace, a
high-speed cilia video, a fluorescence section — into named biomarkers with
correct physical units. The SKILL.md gives you the trigger map, the method
choices that actually matter, and the failure modes; the runnable code and
parameter detail live in `references/`.

The stack is standard scientific Python: `nibabel` for NIfTI volumes, `scipy`
(`optimize`, `signal`, `stats`, `ndimage`), `scikit-image` for segmentation and
morphometry, `numpy.fft` for spectral analysis, and OpenCV (`cv2`) for optical
flow. Nothing here is proprietary — the value is in choosing the right model and
reporting the right units, not in any single wrapper API.

## When to Use This Skill

Trigger when the user has raw data and wants a quantitative readout:

- Compute an **ADC map** from a multi-b-value diffusion MRI series (`references/mri-ct-morphometry.md`)
- Measure **bone microarchitecture** (BV/TV, trabecular thickness/spacing/number, cortical thickness) from a micro-CT volume (`references/mri-ct-morphometry.md`)
- Extract **hemodynamic parameters** (systolic/diastolic BP, MAP, pulse pressure, heart rate) from an arterial pressure waveform (`references/physiological-rhythms.md`)
- Fit **circadian / ultradian rhythms** with a cosinor model and test rhythm significance (`references/physiological-rhythms.md`)
- Measure **ciliary beat frequency** from high-speed video via FFT (`references/physiological-rhythms.md`)
- Quantify **tissue deformation / strain** between image frames with optical flow (`references/microscopy-motion.md`)
- Count and size **amyloid plaques** in fluorescence microscopy (`references/microscopy-motion.md`)

## When NOT to Use This Skill

- **Reading/writing DICOM** or pulling pixel data + metadata off a scanner
  export — use `pydicom`. This skill assumes you already have arrays/NIfTI.
- **General biosignal pipelines** (ECG R-peaks, HRV, EMG envelopes, EDA
  decomposition) — use `neurokit2`; the hemodynamics here is BP-waveform-specific.
- **Generic image segmentation / registration** with no clinical biomarker in
  mind — use `scikit-image` / SimpleITK directly, or a bioimage-analysis skill.
- **Plotting** the results — hand arrays to `matplotlib` or `seaborn`.
- **Statistical modeling of cohorts / group comparisons** — compute biomarkers
  here, then use `statistical-analysis` or `statsmodels` for the group stats.
- **Training ML models** on the derived features — use `scikit-learn` or
  `pytorch-lightning`; this skill produces features, it does not learn.

## Install

```bash
pip install nibabel scipy scikit-image opencv-python numpy pandas
# micro-CT stacks often arrive as multipage TIFF: also `pip install tifffile`
```

## Capability Map

Each row is an entry point; follow the reference for signatures, parameters, and
runnable code.

| Task | Core method / library | Reference |
|---|---|---|
| Diffusion-MRI ADC map | `scipy.optimize.curve_fit` monoexponential per voxel; `nibabel` I/O | `references/mri-ct-morphometry.md` |
| Regional ADC stats | mask + `numpy` percentiles | `references/mri-ct-morphometry.md` |
| Micro-CT bone morphometry | `skimage.filters.threshold_otsu`, `scipy.ndimage.distance_transform_edt` | `references/mri-ct-morphometry.md` |
| Blood-pressure hemodynamics | `scipy.signal.butter`/`filtfilt`/`find_peaks` | `references/physiological-rhythms.md` |
| Circadian cosinor fit + F-test | linearized least squares, `scipy.stats.f` | `references/physiological-rhythms.md` |
| Ciliary beat frequency | windowed `numpy.fft.rfft`, per-ROI dominant peak | `references/physiological-rhythms.md` |
| Tissue deformation / strain | `cv2.calcOpticalFlowFarneback` (dense) / `calcOpticalFlowPyrLK` (sparse) | `references/microscopy-motion.md` |
| Amyloid plaque quantification | `skimage` threshold + `label`/`regionprops` | `references/microscopy-motion.md` |

## Method Choices That Matter

These are the load-bearing scientific decisions — get them wrong and the numbers
are meaningless regardless of code correctness.

- **ADC fitting.** Prefer a per-voxel **monoexponential** fit `S(b) = S0·exp(-b·ADC)`
  (`curve_fit`, bounded so `ADC ∈ [0, ~5×10⁻³] mm²/s`) over the fast log-linear
  average when you have ≥3 b-values. Use ≥2 non-zero b-values; b = 0 and
  b = 1000 s/mm² is the standard brain pair. Restrict fitting to a brain/tissue
  mask — background voxels are pure noise and blow up the log ratio.
- **Bone morphometry units.** BV/TV is dimensionless (report as fraction or %);
  Tb.Th, Tb.Sp, Ct.Th are lengths (mm) and depend entirely on the correct
  `voxel_size` — always thread the scan's isotropic voxel size through. Validate
  the Otsu threshold against a manual segmentation before trusting BV/TV.
- **Cosinor sampling.** Collect ≥2 full cycles; report MESOR, amplitude,
  acrophase (as clock time), R², and the rhythm-detection F-test p-value. If a
  24 h fit is non-significant, test other periods (e.g. 12 h ultradian) rather
  than declaring "arrhythmic".
- **CBF Nyquist.** Frame rate must exceed 2× the highest expected beat frequency.
  Human respiratory CBF is ~5–20 Hz, so record at ≥40 fps (250–500 fps is
  typical). Band-limit the peak search to a physiological window to reject drift
  and lighting flicker.
- **Optical flow model.** Use **Farneback** (dense) when you need a full
  strain/divergence/curl field over tissue; use **Lucas–Kanade** (sparse) when
  tracking a few high-contrast features. Displacements are in **pixels** — convert
  with the known pixel size before reporting physical strain.
- **Always report units.** ADC in 10⁻³ mm²/s, bone metrics in mm, BP in mmHg,
  CBF in Hz, plaque area in µm² (not px) once you apply the pixel calibration.

## Failure Modes and Gotchas

- **Division by zero / log of zero in ADC.** Guard the b = 0 image (`S0`) and
  clip signal ratios to a small positive floor; mask background before any log.
- **Volume/b-value mismatch.** The number of DWI volumes must equal the number
  of b-values, in the same order — a silent off-by-one produces a plausible-but-wrong map.
- **Otsu on the whole volume.** Thresholding across air + soft tissue + bone
  mislabels soft tissue as bone. Restrict Otsu to the ROI, and verify Hounsfield
  calibration for CT.
- **Peak detection on unfiltered BP.** Detect systolic peaks with a minimum
  inter-beat distance (~0.5 s → 120 bpm ceiling) and a prominence threshold; a
  light Butterworth low-pass first suppresses dicrotic-notch false peaks.
- **Aliased CBF.** A frequency near the Nyquist limit, or a stable "beat"
  exactly at the mains frequency (50/60 Hz), is almost always an artifact — check
  the recording fps and the ROI actually contains beating cilia.
- **Plaques merged or fragmented.** Tune `min_size` (remove noise specks) and,
  if plaques touch, apply a watershed split before `regionprops`; use
  `clear_border` to drop objects clipped by the field of view.
- **Reporting pixels as physical units.** Every microscopy/flow metric is in
  pixels until you multiply by the calibrated pixel size. State the calibration.

## References

- `references/mri-ct-morphometry.md` — volumetric imaging: full ADC-map
  computation (monoexponential per-voxel fit, masking, physiological clipping),
  regional ADC statistics, and micro-CT bone morphometry (Otsu segmentation,
  distance-transform Tb.Th/Tb.Sp, Tb.N, cortical thickness) with unit handling.
- `references/physiological-rhythms.md` — time-series and periodic signals:
  blood-pressure beat detection and hemodynamic parameters, cosinor circadian
  analysis with the linearized fit and rhythm F-test, and FFT-based ciliary beat
  frequency with per-ROI spatiotemporal mapping.
- `references/microscopy-motion.md` — 2D microscopy and motion: dense/sparse
  optical flow for tissue deformation (displacement, divergence, curl, strain
  tensor) and amyloid-plaque segmentation + morphometry (count, area,
  eccentricity, intensity, density).

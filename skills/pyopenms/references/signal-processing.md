# Signal Processing

Raw-spectrum algorithms follow one pattern: construct, tune `Param`, run. Filters
mutate the experiment (or spectrum) in place — copy first if you need the
original.

```python
algo = ms.SomeFilter()
params = algo.getParameters()
params.setValue("key", value)
algo.setParameters(params)
algo.filterExperiment(exp)     # or filterSpectrum(spec)
```

## Smoothing

### Gaussian filter

```python
g = ms.GaussFilter()
p = g.getParameters()
p.setValue("gaussian_width", 0.2)      # width in the data's m/z or RT units
p.setValue("use_ppm_tolerance", "true")
p.setValue("ppm_tolerance", 10.0)
g.setParameters(p)
g.filterExperiment(exp)                 # or g.filterSpectrum(spec)
```

### Savitzky-Golay filter

Polynomial smoothing that better preserves peak shape than a Gaussian.

```python
sg = ms.SavitzkyGolayFilter()
p = sg.getParameters()
p.setValue("frame_length", 11)          # odd window size
p.setValue("polynomial_order", 4)
sg.setParameters(p)
sg.filterExperiment(exp)
```

## Peak picking / centroiding

Convert profile-mode spectra to centroids. Feature finders require centroided
input, so this is usually a mandatory first step.

```python
picker = ms.PeakPickerHiRes()
p = picker.getParameters()
p.setValue("signal_to_noise", 3.0)
picker.setParameters(p)

exp_centroided = ms.MSExperiment()
picker.pickExperiment(exp, exp_centroided)
```

`PeakPickerCWT` (continuous wavelet transform) is an alternative for lower-
resolution or noisier data; it exposes `signal_to_noise` and `peak_width`.

## Normalization

```python
norm = ms.Normalizer()
p = norm.getParameters()
p.setValue("method", "to_TIC")          # or "to_one"
norm.setParameters(p)
norm.filterExperiment(exp)
```

## Intensity filtering

```python
# Absolute threshold
mower = ms.ThresholdMower()
mower.getParameters().setValue("threshold", 1000.0)   # then setParameters
mower.filterExperiment(exp)

# Keep top-N peaks per sliding m/z window
wm = ms.WindowMower()
p = wm.getParameters()
p.setValue("windowsize", 50.0)
p.setValue("peakcount", 2)
wm.setParameters(p)
wm.filterExperiment(exp)

# Keep the N most intense peaks overall
nl = ms.NLargest()
nl.getParameters().setValue("n", 200)
nl.filterExperiment(exp)
```

(For clarity, `setValue` mutates the `Param`; always follow with
`algo.setParameters(p)` before running — omitted above only where it was already
shown.)

## Baseline reduction

```python
morph = ms.MorphologicalFilter()
p = morph.getParameters()
p.setValue("struc_elem_length", 3.0)
p.setValue("method", "tophat")          # tophat | bothat | erosion | dilation
morph.setParameters(p)
morph.filterExperiment(exp)
```

## Spectrum merging

Combine adjacent spectra (e.g. to boost S/N over an RT window).

```python
merger = ms.SpectraMerger()
p = merger.getParameters()
p.setValue("block_method:rt_block_size", 5)   # merge every 5 consecutive scans
merger.setParameters(p)
merger.mergeSpectraBlockWise(exp)             # reads block_method:* params
```

## Retention-time alignment

Align RT across runs before linking features (see also
`feature-detection.md`). `MapAlignmentAlgorithmPoseClustering` operates on both
raw experiments and feature maps. Set one run as the reference, then call
`align` once per other run — it takes a single map plus a single
`TransformationDescription`, and `MapAlignmentTransformer` applies the shift in
place.

```python
aligner = ms.MapAlignmentAlgorithmPoseClustering()
aligner.setReference(exp1)                      # align everything to this run

tr = ms.MapAlignmentTransformer()
trafo = ms.TransformationDescription()
aligner.align(exp2, trafo)                       # one map + one trafo
tr.transformRetentionTimes(exp2, trafo, True)    # shifts exp2's RTs in place
```

## Quick spectrum QC

```python
mz, intensity = spec.get_peaks()
tic = intensity.sum()
base_peak_mz = mz[intensity.argmax()]
base_peak_intensity = intensity.max()
```

## Preprocessing pipeline

```python
import pyopenms as ms

def preprocess(input_file, output_file):
    exp = ms.MSExperiment()
    ms.MzMLFile().load(input_file, exp)

    ms.GaussFilter().filterExperiment(exp)          # 1. smooth

    picker = ms.PeakPickerHiRes()                   # 2. centroid
    centroided = ms.MSExperiment()
    picker.pickExperiment(exp, centroided)

    norm = ms.Normalizer()                          # 3. normalize
    p = norm.getParameters(); p.setValue("method", "to_TIC")
    norm.setParameters(p); norm.filterExperiment(centroided)

    mower = ms.ThresholdMower()                      # 4. drop noise
    p = mower.getParameters(); p.setValue("threshold", 10.0)
    mower.setParameters(p); mower.filterExperiment(centroided)

    ms.MzMLFile().store(output_file, centroided)
    return centroided
```

## Notes

- Sweep parameters on representative data (e.g. a pooled QC injection) rather
  than guessing — small changes in `gaussian_width` or `signal_to_noise`
  meaningfully change downstream feature counts.
- Keep an untouched copy (`ms.MSExperiment(exp)`) for before/after comparison
  since filters mutate in place.
- Charge deconvolution / neutral-mass assignment for small molecules lives with
  `MetaboliteAdductDecharger` in `feature-detection.md`.

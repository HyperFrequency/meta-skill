# Colocalization Analysis Reference

Quantify spatial overlap between two fluorescence channels (e.g. protein A vs.
protein B). Report **both** a correlation metric (Pearson) and co-occurrence
metrics (Manders M1/M2) — they answer different questions and can disagree.

## Metrics at a glance

| Metric | Range | Answers |
|---|---|---|
| Pearson (PCC) | −1 to +1 | Do intensities co-vary linearly across pixels? |
| Manders M1 | 0 to 1 | Fraction of channel-1 signal that overlaps channel-2 |
| Manders M2 | 0 to 1 | Fraction of channel-2 signal that overlaps channel-1 |
| Manders overlap (MOC) | 0 to 1 | Symmetric co-occurrence (intensity-weighted) |

Pearson is sensitive to intensity covariance and can be low even with high
co-occurrence (and vice versa). Manders coefficients are asymmetric on purpose:
report M1 and M2 separately.

## Pearson + Manders

```python
import numpy as np
import skimage.io, skimage.filters
from scipy.stats import pearsonr

ch1 = skimage.io.imread("green.tif").astype(float)
ch2 = skimage.io.imread("red.tif").astype(float)

# Background subtraction (per-channel) before thresholding.
ch1 = np.clip(ch1 - np.percentile(ch1, 5), 0, None)
ch2 = np.clip(ch2 - np.percentile(ch2, 5), 0, None)

# Threshold each channel; analyze the union of signal pixels.
t1 = skimage.filters.threshold_otsu(ch1)
t2 = skimage.filters.threshold_otsu(ch2)
mask = (ch1 > t1) | (ch2 > t2)
a, b = ch1[mask], ch2[mask]

pcc, pval = pearsonr(a, b)

M1 = a[b > 0].sum() / a.sum()        # fraction of ch1 co-occurring with ch2
M2 = b[a > 0].sum() / b.sum()        # fraction of ch2 co-occurring with ch1
MOC = (a * b).sum() / np.sqrt((a**2).sum() * (b**2).sum())

print(f"Pearson r={pcc:.4f} (p={pval:.2e}) | M1={M1:.4f} M2={M2:.4f} MOC={MOC:.4f}")
```

## Threshold-method choice

The threshold used to define "signal" strongly affects Manders values. Pick by
signal quality:

- `threshold_otsu` — general default, bimodal histograms.
- `threshold_li` — dim signals (minimum cross-entropy); often best for faint stains.
- `threshold_yen` — high-dynamic-range images.

**Costes approach:** rather than pick a threshold by eye, Costes' method searches
for the intensity threshold below which the two channels are uncorrelated (PCC ≈ 0),
and computes Manders above it — this removes user bias. Approximate it by sweeping
thresholds and taking the largest one at which residual PCC drops to ~0, or use a
package that implements it directly.

## Required controls and pitfalls

- **Single-stained controls.** Image each fluorophore alone to measure spectral
  bleed-through; subtract or unmix before colocalization, or overlap is inflated.
- **Costes randomization significance.** Compare the measured PCC against PCC from
  many runs with one channel's pixel blocks randomized; real colocalization should
  exceed the randomized distribution.
- **Register the channels.** Chromatic aberration/misalignment between channels
  lowers true colocalization; align channels first if needed.
- **Do not colocalize on saturated pixels.** Clipped maxima break the linear
  intensity assumption behind PCC and Manders — check for saturation first.
- **Segment to compartments when relevant.** Whole-field colocalization mixes
  compartments; mask to nuclei/cytoplasm (see `references/segmentation.md`) to ask
  a compartment-specific question.

## Reporting

State: the two channels/fluorophores, background-subtraction and threshold method,
PCC with p-value, M1 and M2 (not just one), and the control strategy. A single
number without the threshold method and controls is not interpretable.

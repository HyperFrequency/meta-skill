# Volumetric Imaging: ADC Maps and Bone Morphometry

Quantitative biomarkers from 3D/4D volumes. All code assumes NumPy arrays; use
`nibabel` for NIfTI and `tifffile` for micro-CT TIFF stacks.

## 1. Diffusion-MRI ADC Map

The apparent diffusion coefficient (ADC) quantifies water mobility and is used
for stroke, tumor cellularity, and tissue characterization. The signal decays
monoexponentially with the diffusion weighting `b`:

```
S(b) = S0 · exp(-b · ADC)
```

### Preferred: per-voxel monoexponential fit

Fit the model directly with bounds. This is more robust than the fast log-linear
average when SNR is low or you have ≥3 b-values.

```python
import warnings
import nibabel as nib
import numpy as np
from scipy.optimize import curve_fit

ADC_MIN, ADC_MAX = 0.0, 0.005   # physiological bounds, mm^2/s

def monoexponential(b, s0, adc):
    return s0 * np.exp(-b * adc)

def fit_adc_voxel(signal, bvals):
    """Fit S(b)=S0*exp(-b*ADC) to one voxel. Returns ADC (mm^2/s) or NaN."""
    if np.any(signal <= 0) or np.all(signal == signal[0]):
        return np.nan
    s0_init = signal[0] if signal[0] > 0 else np.max(signal)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = curve_fit(
                monoexponential, bvals, signal,
                p0=[s0_init, 0.001],
                bounds=([0, ADC_MIN], [np.inf, ADC_MAX * 2]),
                maxfev=1000,
            )
        return popt[1]
    except (RuntimeError, ValueError):
        return np.nan

def compute_adc_map(data4d, bvals, mask=None):
    """data4d: (x,y,z,nb) DWI stack; bvals: 1D array in s/mm^2 (same order)."""
    nx, ny, nz, nb = data4d.shape
    if nb != len(bvals):
        raise ValueError(f"{nb} volumes but {len(bvals)} b-values")
    if mask is None:
        mask = np.ones((nx, ny, nz), dtype=bool)
    adc = np.full((nx, ny, nz), np.nan)
    for i, j, k in np.argwhere(mask):
        val = fit_adc_voxel(data4d[i, j, k, :], bvals)
        if not np.isnan(val):
            adc[i, j, k] = np.clip(val, ADC_MIN, ADC_MAX)
    return adc
```

Load, fit, and save preserving the affine/header:

```python
img = nib.load("dwi.nii.gz")          # 4D NIfTI, one volume per b-value
data = np.asarray(img.dataobj, dtype=np.float64)
bvals = np.array([0, 500, 1000], dtype=float)
mask = np.asarray(nib.load("brain_mask.nii.gz").dataobj).astype(bool)  # optional

adc_map = compute_adc_map(data, bvals, mask)
out = nib.Nifti1Image(adc_map, img.affine, img.header)
nib.save(out, "adc_map.nii.gz")
```

### Fast alternative: log-linear estimate

When you only need a quick map, average per-b-value log ratios against the b = 0
image (`ADC = -ln(S/S0)/b`). Guard against zeros and clip:

```python
S0 = data[..., 0].astype(float)
S0[S0 == 0] = 1e-10
contribs = []
for vi, b in enumerate(bvals):
    if b > 0:
        ratio = np.clip(data[..., vi] / S0, 1e-10, None)
        contribs.append(-np.log(ratio) / b)
adc_fast = np.clip(np.mean(contribs, axis=0), 0, 3.5e-3)
```

### Regional ADC statistics

Report ADC in `10⁻³ mm²/s`. Exclude NaN / non-positive voxels.

```python
def regional_adc_stats(adc_map, roi_mask):
    v = adc_map[roi_mask & ~np.isnan(adc_map) & (adc_map > 0)]
    return {
        "mean":  v.mean()   * 1e3,
        "median": np.median(v) * 1e3,
        "std":   v.std()    * 1e3,
        "n_voxels": int(v.size),
        "unit": "10^-3 mm^2/s",
    }
```

**Notes**
- Use ≥2 non-zero b-values; b = 0 / b = 1000 s/mm² is standard for brain.
- Confirm DWI volume order matches `bvals` order exactly.
- Smooth the DWI (small Gaussian) before fitting if the map is noisy; always mask
  background — free-water/air voxels dominate the log ratio otherwise.

## 2. Micro-CT Bone Morphometry

Standard trabecular/cortical parameters from a segmented micro-CT volume. Names
follow the ASBMR nomenclature (BV/TV, Tb.Th, Tb.Sp, Tb.N, Ct.Th).

```python
import numpy as np
from scipy import ndimage
from skimage.filters import threshold_otsu
from skimage.morphology import binary_erosion, ball

def bone_morphometry(volume, voxel_size_um, roi_mask=None):
    """volume: 3D micro-CT array. voxel_size_um: isotropic voxel size (µm)."""
    if roi_mask is None:
        roi_mask = np.ones_like(volume, dtype=bool)
    vox_mm = voxel_size_um / 1000.0

    # Segment bone inside the ROI only (never Otsu the whole air+tissue volume)
    thresh = threshold_otsu(volume[roi_mask])
    bone = (volume > thresh) & roi_mask

    # BV/TV — dimensionless
    bv_tv = bone.sum() / roi_mask.sum()

    # Tb.Th via distance transform: 2 * mean(EDT within bone)
    d_bone = ndimage.distance_transform_edt(bone)
    tb_th = 2 * d_bone[bone].mean() * vox_mm if bone.any() else 0.0

    # Tb.Sp via distance transform of the marrow space
    marrow = (~bone) & roi_mask
    d_marrow = ndimage.distance_transform_edt(marrow)
    tb_sp = 2 * d_marrow[marrow].mean() * vox_mm if marrow.any() else 0.0

    # Tb.N ~ BV/TV / Tb.Th  (1/mm)
    tb_n = bv_tv / tb_th if tb_th > 0 else 0.0

    # Cortical thickness: shell = bone minus its erosion
    eroded = binary_erosion(bone, ball(3))
    cortex = bone & ~eroded
    ct_th = (ndimage.distance_transform_edt(cortex)[cortex].mean() * vox_mm
             if cortex.any() else 0.0)

    return {
        "BV/TV": bv_tv,          # fraction
        "Tb.Th_mm": tb_th,
        "Tb.Sp_mm": tb_sp,
        "Tb.N_per_mm": tb_n,
        "Ct.Th_mm": ct_th,
        "bone_voxels": int(bone.sum()),
        "total_voxels": int(roi_mask.sum()),
    }
```

Usage with a TIFF stack:

```python
import tifffile
volume = tifffile.imread("microct_stack.tif")   # (z, y, x)
res = bone_morphometry(volume, voxel_size_um=10)
print(f"BV/TV={res['BV/TV']:.3f}  Tb.Th={res['Tb.Th_mm']:.4f} mm")
```

**Notes**
- The isotropic `voxel_size_um` is load-bearing: every length scales with it.
- Validate the Otsu threshold against a manual segmentation; for anisotropic CT
  or beam-hardening artifacts, use a local/adaptive threshold instead.
- The distance-transform Tb.Th is the plate-model estimate; report the method
  alongside the value for reproducibility.

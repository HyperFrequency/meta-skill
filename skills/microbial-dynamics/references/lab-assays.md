# Wet-Lab Assays & Genome Annotation

Quantification helpers for common microbiology bench readouts, plus bacterial
genome annotation. Everything here is standard NumPy/pandas/SciPy; the colony
counter additionally needs scikit-image + OpenCV, and annotation needs Prokka.

## Crystal-violet biofilm assay

Biofilm biomass is estimated from OD570 after crystal-violet staining and
solubilization. Subtract a blank, aggregate replicates to mean/SEM, and express
each condition as fold-change vs the control (place control first).

```python
import numpy as np
import pandas as pd

def analyze_biofilm_cv(od_data, blank_od=0.05):
    """od_data: dict of condition -> list of OD570 replicates (control first)."""
    rows = []
    for condition, replicates in od_data.items():
        corrected = np.clip(np.array(replicates) - blank_od, 0, None)
        n = len(corrected)
        sd = np.std(corrected, ddof=1)
        rows.append({'condition': condition, 'mean_od': corrected.mean(),
                     'std_od': sd, 'n': n, 'sem': sd / np.sqrt(n)})
    df = pd.DataFrame(rows)
    df['fold_change'] = df['mean_od'] / df.iloc[0]['mean_od']
    return df

od_data = {
    'Control': [0.85, 0.92, 0.88, 0.90],
    '10 uM':   [0.55, 0.52, 0.58, 0.50],
    '100 uM':  [0.20, 0.18, 0.22, 0.19],
}
print(analyze_biofilm_cv(od_data)[['condition', 'mean_od', 'sem', 'fold_change']])
```

**Normalization caveat:** crystal violet stains total biomass, so a lower signal
can mean either less biofilm *or* less growth. To isolate biofilm-specific
effects, run a parallel planktonic OD600 and report the CV/OD600 ratio (specific
biofilm formation index). For dose-response EC50 fitting on the fold-change
series, hand off to `statistical-analysis`.

## CFU enumeration from serial dilution

CFU/mL = colony_count / (dilution_factor x volume_plated_mL). Aggregate replicate
plates and attach a t-distribution 95% confidence interval.

```python
import numpy as np
from scipy import stats

def calculate_cfu(counts, dilution_factor, volume_plated_ml=0.1):
    """counts: colony counts from replicate plates at one dilution.
    dilution_factor: e.g. 1e-6 for a 10^-6 dilution."""
    cfu = np.array(counts) / (dilution_factor * volume_plated_ml)
    n = len(cfu)
    mean = cfu.mean()
    sem = np.std(cfu, ddof=1) / np.sqrt(n)
    ci = stats.t.interval(0.95, df=n - 1, loc=mean, scale=sem)
    return {'mean_cfu_per_ml': mean, 'sem': sem, 'ci_95': ci,
            'n': n, 'log10_cfu': np.log10(mean)}

r = calculate_cfu([42, 38, 45], dilution_factor=1e-6, volume_plated_ml=0.1)
print(f"{r['mean_cfu_per_ml']:.2e} CFU/mL  log10={r['log10_cfu']:.2f}  "
      f"95% CI ({r['ci_95'][0]:.2e}, {r['ci_95'][1]:.2e})")
```

**Countable-range rule:** only use plates with **30-300 colonies**. Below 30 the
Poisson count error is too large; above 300 colonies merge and are undercounted.
If multiple dilutions are countable, average the back-calculated CFU/mL. Report
on the log10 scale — CFU is log-normally distributed, so arithmetic means and
CIs are more sensible in log space for large counts.

## Colony counting from plate images

Automate colony counts from an agar-plate photograph, including touching/
overlapping colonies, via watershed segmentation. Pipeline:

1. **Load** the image (OpenCV, BGR) and convert to grayscale.
2. **Blur** with a Gaussian kernel to suppress texture noise.
3. **Threshold** to a binary mask — Otsu global threshold, optionally combined
   with adaptive thresholding for uneven lighting.
4. **Distance transform** the mask (`scipy.ndimage.distance_transform_edt`); the
   local maxima mark colony centers.
5. **Seed + watershed** — find peaks with `skimage.feature.peak_local_max`, label
   them as markers, and run `skimage.segmentation.watershed` on the negated
   distance map to split touching colonies.
6. **Filter** labeled regions by area/radius (min/max radius) and circularity to
   drop debris and plate-edge artifacts; count the survivors and summarize their
   size distribution.

```python
import cv2
import numpy as np
from scipy import ndimage
from skimage.feature import peak_local_max
from skimage.segmentation import watershed

def count_colonies(path, min_radius=5, max_radius=40, blur_ksize=11):
    img = cv2.imread(str(path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
    _, mask = cv2.threshold(blurred, 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dist = ndimage.distance_transform_edt(mask)
    peaks = peak_local_max(dist, min_distance=min_radius, labels=mask)
    markers = np.zeros(dist.shape, dtype=int)
    markers[tuple(peaks.T)] = np.arange(1, len(peaks) + 1)
    labels = watershed(-dist, markers, mask=mask)

    radii = []
    for label_id in range(1, labels.max() + 1):
        area = np.sum(labels == label_id)
        radius = np.sqrt(area / np.pi)
        if min_radius <= radius <= max_radius:
            radii.append(radius)
    return {'count': len(radii),
            'mean_radius_px': float(np.mean(radii)) if radii else 0.0}
```

Tunable parameters:
- `min_radius` / `max_radius` — size gate in pixels; set from a known scale bar
  or plate diameter. Lower `min_radius` for very small colonies.
- `min_distance` (in `peak_local_max`) — minimum separation between colony
  centers; raise it to merge over-segmented single colonies.
- Blur kernel and threshold sensitivity — raise blur for noisy photos.

Failure modes: uneven illumination (use adaptive/CLAHE preprocessing or a flat-
field correction), reflections and condensation (mask the plate rim, shoot on a
dark matte background), and confluent lawns (unresolvable — dilute and replate).
For richer microscopy/fluorescence workflows beyond colony counting, use
`bioimage-analysis`.

## Bacterial genome annotation (Prokka)

Prokka wraps gene prediction (Prodigal) and functional annotation. Run it on an
assembly, then parse the GFF3 for feature statistics.

```python
import subprocess
import pandas as pd

def run_prokka(fasta_path, output_dir, prefix='genome', genus=None, species=None):
    cmd = ['prokka', fasta_path, '--outdir', output_dir, '--prefix', prefix,
           '--cpus', '4', '--force', '--kingdom', 'Bacteria']
    if genus:   cmd += ['--genus', genus]
    if species: cmd += ['--species', species]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Prokka failed: {proc.stderr}")
    return f'{output_dir}/{prefix}'

def parse_prokka_gff(gff_path):
    """Extract CDS/tRNA/rRNA/tmRNA features from Prokka GFF3."""
    genes = []
    with open(gff_path) as f:
        for line in f:
            if line.startswith('#') or line.startswith('>') or '\t' not in line:
                continue
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 9 or parts[2] not in ('CDS', 'tRNA', 'rRNA', 'tmRNA'):
                continue
            attrs = dict(kv.split('=', 1) for kv in parts[8].split(';') if '=' in kv)
            genes.append({'type': parts[2], 'start': int(parts[3]),
                          'end': int(parts[4]), 'strand': parts[6],
                          'gene': attrs.get('gene', ''),
                          'product': attrs.get('product', ''),
                          'length': int(parts[4]) - int(parts[3]) + 1})
    df = pd.DataFrame(genes)
    coding = df[df['type'] == 'CDS']['length'].sum()
    genome_size = df['end'].max()
    print(df['type'].value_counts())
    print(f"mean CDS length: {df[df['type']=='CDS']['length'].mean():.0f} bp")
    print(f"coding density: {100 * coding / genome_size:.1f}%")
    return df
```

Useful Prokka flags: `--kingdom {Bacteria,Archaea,Viruses}`, `--genus`/`--species`
(improves product naming from a genus-specific database), `--cpus`, `--force`
(overwrite output), `--gcode` (translation table), `--rfam` (also scan
non-coding RNAs). A typical E. coli genome yields ~4000-4500 CDS and a coding
density near 88%.

**Troubleshooting:** "no genes found" usually means a malformed FASTA (stray
whitespace, non-nucleotide characters) or non-bacterial input — verify the
sequence and set `--kingdom Bacteria` explicitly. For downstream work on the
predicted genes (translation, BLAST, alignment), hand the CDS to `biopython`.

## Reference

- Seemann (2014), Prokka, *Bioinformatics* 30:2068-2069;
  https://github.com/tseemann/prokka
- `skimage.segmentation.watershed`, `skimage.feature.peak_local_max` docs.
- `scipy.stats.t.interval` for the CFU confidence interval.

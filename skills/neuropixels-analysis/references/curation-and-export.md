# Curation and Export Reference

Turn quality metrics + waveforms into final good/MUA/noise labels, then export
for review or sharing. All calls use `spikeinterface.full as si`.

## Threshold-based auto-curation

The simplest curation is a rule over the metrics DataFrame. Be explicit and
record the thresholds you used.

```python
def classify(qm):
    labels = {}
    for uid, row in qm.iterrows():
        if row["snr"] < 2 or row["presence_ratio"] < 0.5:
            labels[uid] = "noise"
        elif row["isi_violations_ratio"] > 0.1:
            labels[uid] = "mua"
        elif row["snr"] > 5 and row["isi_violations_ratio"] < 0.01 and row["presence_ratio"] > 0.9:
            labels[uid] = "good"
        else:
            labels[uid] = "unsorted"
    return labels

labels = classify(qm)
good_ids = [u for u, l in labels.items() if l == "good"]
sorting_clean = sorting.select_units(good_ids)
```

## Bombcell (4-class classification)

Bombcell classifies each unit as **single somatic / MUA / noise / non-somatic**
(axonal-dendritic) using waveform-shape and spatial-decay features that pure
threshold metrics miss.

```python
import bombcell as bc
results = bc.run_bombcell(kilosort_folder="/path/ks4/", raw_data_path="/path/rec.ap.bin",
                          sample_rate=30000, n_channels=384)
unit_labels = results["unit_labels"]   # 'good' / 'mua' / 'noise' / 'non-somatic'
```

Key Bombcell features: `peak_trough_ratio` (somatic vs non-somatic),
`spatial_decay` (noise), refractory-period violations, `presence_ratio`,
`waveform_duration` (narrow vs broad — putative cell type). It reads a Phy export,
so `si.export_to_phy(analyzer, ...)` first if starting from a SpikeInterface
analyzer.

## SpikeInterface curation API (merge / split / remove)

```python
from spikeinterface.curation import CurationSorting

cur = CurationSorting(sorting)
noise = qm.query("snr < 2").index.tolist()
cur.remove_units(noise)

# Merge over-split templates using template similarity (review before trusting)
analyzer.compute("template_similarity")
sim = analyzer.get_extension("template_similarity").get_data()
# inspect pairs with sim > ~0.9, then cur.merge([[uid_a, uid_b], ...])

sorting_curated = cur.sorting
```

There is also model-based auto-curation in `spikeinterface.curation` (trained
classifiers that predict good/noise from the metric vector) — useful when you
have a labeled subset to calibrate against your rig.

## AI-assisted visual curation (technique)

Borderline units (the SNR ~3–8 band) are best judged from a summary figure: mean
waveform shape, a clean refractory gap in the autocorrelogram, and amplitude
stability over time. The general, vendor-neutral pattern is **render → inspect**:

```python
uncertain = qm.query("snr > 3 and snr < 8").index.tolist()
for uid in uncertain:
    si.plot_unit_summary(analyzer, unit_id=uid).figure.savefig(f"unit_{uid}.png", dpi=120)
```

Then classify each `unit_<id>.png`:
- **Inside an agent with vision** (like Claude Code): read the PNG directly and
  ask for a good/MUA/noise call with reasoning — no external API needed.
- **Programmatically:** send the image to any vision-language model's messages
  API (e.g. `anthropic.Anthropic().messages.create(...)` with an image block).

What the figure shows and what to look for:

| Panel | Look for |
|---|---|
| Mean template ± std | clean negative peak, physiological shape, low variance |
| Autocorrelogram | a clear gap at 0 ms (refractory period) |
| Amplitudes over time | stable, no sudden drop-out (drift) |
| ISI histogram | few intervals below ~1.5 ms |

Best practice: use vision only for the uncertain band, always combine it with the
numeric metrics, and keep a human in the loop for publication-critical calls.

## UnitMatch (cross-session tracking)

Track the same neurons across recording days from per-session Kilosort/Bombcell
outputs — see https://github.com/EnnyvanBeest/UnitMatch (van Beest et al., 2024).

## Export

### To Phy (manual review)

```python
si.export_to_phy(analyzer, output_folder="phy_export/",
                 compute_pc_features=True, compute_amplitudes=True, copy_binary=True)
# Open in a terminal:  phy template-gui phy_export/params.py
```

Load the human labels back:

```python
sorting_curated = si.read_phy("phy_export/")   # after curating in Phy
```

### To NWB (sharing / archiving)

```python
from spikeinterface.exporters import export_to_nwb
export_to_nwb(analyzer, nwbfile_path="results.nwb",
              metadata={"session_description": "Neuropixels recording"})
```

### Plain artifacts

```python
qm.to_csv("quality_metrics.csv")
import json
json.dump(labels, open("curation_labels.json", "w"), indent=2)
```

## Suggested project layout

```
project/
├── raw_data/                 # SpikeGLX run folder(s)
├── preprocessed/             # saved preprocessed recording
├── sorting_output/           # sorter output
├── analyzer/                 # SortingAnalyzer (waveforms, metrics)
├── phy_export/               # for manual curation
└── results/                  # quality_metrics.csv, curation_labels.json, results.nwb
```

## References

- Curation module:
  https://spikeinterface.readthedocs.io/en/stable/modules/curation.html
- Bombcell — https://github.com/Julie-Fabre/bombcell (Fabre et al., 2023)
- Exporters:
  https://spikeinterface.readthedocs.io/en/stable/modules/exporters.html

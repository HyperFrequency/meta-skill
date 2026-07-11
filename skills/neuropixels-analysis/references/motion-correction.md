# Motion / Drift Correction Reference

Neuropixels probes drift 10–100+ µm relative to the brain during a recording.
Uncorrected drift makes units appear and disappear, shifts waveform amplitudes,
and over-splits single neurons. **Always inspect drift before sorting.**

## Detect drift before sorting

Detect and localize peaks, then plot them as a raster over depth vs time. A
straight horizontal band = stable; a drifting band = motion.

```python
import spikeinterface.full as si
from spikeinterface.sortingcomponents.peak_detection import detect_peaks
from spikeinterface.sortingcomponents.peak_localization import localize_peaks

rec = si.highpass_filter(recording, freq_min=400.0)
rec = si.common_reference(rec, operator="median", reference="global")   # do NOT whiten here

noise_levels = si.get_noise_levels(rec, return_in_uV=False)
peaks = detect_peaks(rec, method="locally_exclusive", noise_levels=noise_levels,
                     detect_threshold=5, radius_um=50.0)
peak_locations = localize_peaks(rec, peaks, method="center_of_mass")

si.plot_drift_raster_map(peaks=peaks, peak_locations=peak_locations,
                         recording=rec, clim=(-200, 0))
```

Reading the raster:

| Pattern | Interpretation | Action |
|---|---|---|
| Horizontal, stable bands | No significant drift | Skip correction |
| Slow diagonal drift | Gradual settling | Correct (rigid or non-rigid) |
| Rapid vertical jumps | Pulsation / movement | Non-rigid correction |
| Chaotic smear | Severe instability | Consider discarding the segment |

## Preset-based correction (recommended start)

```python
rec_corrected, motion_info = si.correct_motion(
    recording=rec, preset="nonrigid_accurate", output_motion_info=True)
```

`output_motion_info=True` returns `(recording, motion_info)`; omit it to get just
the corrected recording. Presets:

| Preset | Speed | Accuracy | Use for |
|---|---|---|---|
| `rigid_fast` | fast | low | quick check, small drift |
| `kilosort_like` | medium | good | Kilosort-compatible results |
| `nonrigid_accurate` | slow | high | publication quality |
| `nonrigid_fast_and_accurate` | medium | high | sensible default |
| `dredge` / `dredge_fast` | slow / medium | highest | complex drift |

## Full manual control

```python
from spikeinterface.sortingcomponents.motion import estimate_motion, interpolate_motion

motion = estimate_motion(
    rec, peaks, peak_locations,
    method="decentralized", direction="y",   # 'y' = along the probe shank
    rigid=False,                             # non-rigid for Neuropixels
    bin_s=2.0,                               # temporal resolution
    win_step_um=50, win_sigma_um=150,        # spatial window step / smoothing
)
si.plot_motion(motion, recording=rec)

rec_corrected = interpolate_motion(recording=rec, motion=motion,
                                   border_mode="force_extrapolate",
                                   spatial_interpolation_method="kriging")
```

Persist the estimate so you can reapply it without recomputing:
`np.savez("motion.npz", ...)`.

## DREDge and LFP-based estimation

DREDge (Windolf et al., 2023) is the current best-performing method for complex
drift. For very fast drift, estimate from the LFP band and apply to the AP band:

```python
lfp = si.read_spikeglx("/path/to/run_g0/", stream_id="imec0.lf")
motion_lfp = si.estimate_motion(lfp, preset="dredge_lfp")   # coarse but robust to fast drift
# then interpolate_motion(recording=rec_ap, motion=motion_lfp, ...)
```

## Integration with the sorter

Pick **one** correction path — do not stack them.

- **Pre-correct (recommended):** `si.correct_motion(...)` → `rec.save(...)` →
  `si.run_sorter("kilosort4", rec_corrected, ...)`.
- **Let Kilosort do it:** pass the *uncorrected* recording and enable the
  sorter's internal drift handling (`nblocks`, `do_correction=True`).

## Troubleshooting

- **Over-correction (wavy artifacts):** increase temporal smoothing (`bin_s=5.0`)
  or use `rigid=True` for small drift.
- **Under-correction (drift remains):** finer non-rigid windows
  (`win_step_um=25, win_sigma_um=75`) and/or a lower `detect_threshold` for more
  peaks.
- **Edge artifacts:** `border_mode="force_extrapolate"` or `"remove_channels"`.

## Validate afterwards

Re-detect peaks on the corrected recording and plot before/after side by side —
the drifting band should flatten out.

## References

- Motion-correction module:
  https://spikeinterface.readthedocs.io/en/stable/modules/motion_correction.html
- Handle-drift how-to:
  https://spikeinterface.readthedocs.io/en/stable/how_to/handle_drift.html
- DREDge — https://github.com/evarol/DREDge ; Windolf et al. (2023)

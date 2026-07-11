# Preprocessing Reference

Load Neuropixels data and condition the raw traces for spike sorting. All calls
use `spikeinterface.full as si`.

## Loading and inspecting

```python
# SpikeGLX (most common). A "run" folder holds imec sub-folders + .meta sidecars.
rec = si.read_spikeglx("/path/to/run_g0/", stream_id="imec0.ap")

# Open Ephys (point at the Record Node folder)
rec = si.read_openephys("/path/to/Record Node 101/")

# NWB
rec = si.read_nwb("/path/to/session.nwb")

# Discover available streams before committing to one
streams, ids = si.get_neo_streams("spikeglx", "/path/to/run_g0/")
# e.g. ['imec0.ap', 'imec0.lf', 'nidq'] — ".ap" = 30 kHz action-potential band, ".lf" = LFP
```

Verify what you loaded:

```python
rec.get_num_channels()          # 384 for a standard Neuropixels bank
rec.get_sampling_frequency()    # ~30000.0 for the AP band
rec.get_total_duration()        # seconds
rec.get_probe()                 # probeinterface Probe with geometry
rec.get_channel_locations()     # (n_channels, 2) x/y in microns
```

**Work on a slice while developing** so you are not filtering an hour of data on
every iteration:

```python
rec_test = rec.frame_slice(0, int(60 * rec.get_sampling_frequency()))   # first 60 s
```

## Standard preprocessing chain

The order matters. Phase-shift before referencing; reference after filtering.

```python
rec = si.highpass_filter(rec, freq_min=300)                 # or bandpass_filter for a fixed AP band
rec = si.phase_shift(rec)                                    # NP 1.0 ADC correction (see below)
bad_ids, labels = si.detect_bad_channels(rec)               # labels: 'dead' / 'noise' / 'out'
rec = rec.remove_channels(bad_ids)                          # or si.interpolate_bad_channels(rec, bad_ids)
rec = si.common_reference(rec, reference="global", operator="median")   # CMR removes correlated noise
```

## Filtering options

```python
# Fixed AP band (preserve less low-frequency content than a pure highpass)
rec = si.bandpass_filter(rec, freq_min=300, freq_max=6000)

# Filter internals
rec = si.bandpass_filter(rec, freq_min=300, freq_max=6000,
                         filter_order=5, ftype="butter", margin_ms=5.0)

# Line-noise notch (and harmonics)
rec = si.notch_filter(rec, freq=60, q=30)
```

## Reference schemes

```python
# Common median reference (recommended default)
rec = si.common_reference(rec, reference="global", operator="median")

# Common average reference
rec = si.common_reference(rec, reference="global", operator="average")

# Per-shank reference on multi-shank probes — reference within each shank group
groups = rec.get_channel_groups()
rec = si.common_reference(rec, reference="global", operator="median", groups=groups)
```

## Bad-channel detection

```python
bad_ids, labels = si.detect_bad_channels(
    rec, method="coherence+psd",
    dead_channel_threshold=-0.5, noisy_channel_threshold=1.0,
    outside_channel_threshold=-0.3, n_neighbors=11,
)
rec = si.interpolate_bad_channels(rec, bad_ids)   # fill from neighbors instead of dropping
```

Interpolating keeps the channel count/geometry intact (helpful for sorters that
assume a full probe); removing is simpler when only a few edge channels are bad.

## IBL-style destriping

For recordings with strong common-mode stripes, add a spatial highpass after the
temporal filter (this is the core of the IBL destriping recipe):

```python
rec = si.highpass_filter(rec, freq_min=400)
rec = si.phase_shift(rec)
rec = si.highpass_spatial_filter(rec)                                   # destripe
rec = si.common_reference(rec, reference="global", operator="median")
```

## Whitening and artifacts

```python
rec = si.whiten(rec, mode="local", radius_um=100)          # decorrelate channels (some sorters expect it)

triggers = [10000, 20000, 30000]                            # stim onsets in SAMPLES
rec = si.remove_artifacts(rec, triggers, ms_before=0.5, ms_after=3.0, mode="cubic")
```

Do **not** whiten before drift estimation — whitening distorts peak amplitudes
used to localize spikes.

## Probe-specific handling

| Probe | Channels | phase_shift? | Notes |
|---|---|---|---|
| Neuropixels 1.0 | 384 of 960 | **required** | Shared ADC samples channels at staggered times |
| Neuropixels 2.0 (single-shank) | 384 of 1280 | not needed | Per-channel ADC; denser geometry |
| Neuropixels 2.0 (4-shank) | 384 of 5120 | not needed | Reference per shank via `get_channel_groups()` |

## Saving preprocessed data

Preprocessing in SpikeInterface is **lazy** — filters are applied on read. Save
once to materialize the result and make sorting/metrics fast to re-run:

```python
rec = rec.save(folder="preprocessed/", format="binary", n_jobs=-1, chunk_duration="1s")
# Reload later without recomputing the chain:
rec = si.load_extractor("preprocessed/")
```

Use `format="zarr"` for compressed on-disk storage when disk space matters.

## References

- SpikeInterface preprocessing module:
  https://spikeinterface.readthedocs.io/en/stable/modules/preprocessing.html
- Analyze-Neuropixels how-to:
  https://spikeinterface.readthedocs.io/en/stable/how_to/analyze_neuropixels.html
- IBL destriping: `ibl-neuropixel` — https://github.com/int-brain-lab/ibl-neuropixel

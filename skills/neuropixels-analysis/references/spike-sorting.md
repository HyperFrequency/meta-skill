# Spike Sorting Reference

Run a sorter on a preprocessed (and ideally drift-corrected) recording to get a
`Sorting` object of spike trains per unit. All calls use `spikeinterface.full as si`.

## Available sorters

| Sorter | GPU | Speed | Quality | Best for |
|---|---|---|---|---|
| **Kilosort4** | CUDA required | fast | excellent | production default |
| **Kilosort3 / 2.5** | CUDA required | fast | very good | legacy pipelines |
| **SpykingCircus2** | no | medium | good | CPU-only systems |
| **Tridesclous2** | no | medium | good | CPU, interactive |
| **Mountainsort5** | no | medium | good | short recordings |

```python
print(si.installed_sorters())                       # what is actually runnable here
params = si.get_default_sorter_params("kilosort4")  # full default parameter dict
```

## Kilosort4 (recommended)

```python
sorting = si.run_sorter("kilosort4", rec, folder="ks4_output", verbose=True)
print(f"Found {len(sorting.unit_ids)} units")
```

Key parameters (pass as kwargs to `run_sorter`):

```python
sorting = si.run_sorter(
    "kilosort4", rec, folder="ks4_output",
    # detection
    Th_universal=9,        # universal detection threshold (lower -> more spikes)
    Th_learned=8,          # threshold for learned templates
    # templates / clustering
    dmin=15,               # min vertical distance between templates (µm)
    dminx=12,              # min horizontal distance (µm)
    nblocks=5,             # non-rigid drift blocks (0 disables internal correction)
    # performance
    batch_size=60000,      # samples per batch (lower on GPU OOM)
    do_CAR=False,          # skip CAR if already done in preprocessing
)
```

## CPU alternatives

```python
sorting = si.run_sorter("spykingcircus2", rec, folder="sc2/")   # detect_threshold≈5
sorting = si.run_sorter("tridesclous2",  rec, folder="tdc2/")
sorting = si.run_sorter("mountainsort5", rec, folder="ms5/", scheme="2")
```

## Containerized sorters

Run a sorter without a local install via Docker/Singularity images:

```python
sorting = si.run_sorter("kilosort3", rec, folder="ks3/",
                        docker_image="spikeinterface/kilosort3-compiled-base:latest")
# or singularity_image="/path/to/kilosort3.sif"
```

## Long recordings

```python
# Concatenate multiple files, sort once, then split back
recs = [si.read_spikeglx(f"/path/rec_{i}/", stream_id="imec0.ap") for i in range(3)]
rec_all = si.concatenate_recordings(recs)
sorting = si.run_sorter("kilosort4", rec_all, folder="ks4/")
sortings = si.split_sorting(sorting, rec_all)
```

## Compare multiple sorters

Agreement across independent sorters is a strong quality signal.

```python
s_ks4 = si.run_sorter("kilosort4", rec, folder="ks4/")
s_sc2 = si.run_sorter("spykingcircus2", rec, folder="sc2/")
cmp = si.compare_multiple_sorters([s_ks4, s_sc2], name_list=["KS4", "SC2"])
consensus = cmp.get_agreement_sorting(minimum_agreement_count=2)   # found by >=2 sorters
```

## Inspect the output

```python
len(sorting.unit_ids)                          # number of units
sorting.get_total_num_spikes()                 # dict unit_id -> count
duration = rec.get_total_duration()
for uid in sorting.unit_ids[:5]:
    n = len(sorting.get_unit_spike_train(uid))
    print(uid, f"{n/duration:.2f} Hz")
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| GPU out of memory | lower `batch_size` (e.g. 30000) |
| Too few units | lower `Th_universal`/`Th_learned` (e.g. 7 / 6) |
| Too many units (over-split) | raise `dmin`/`dminx` (e.g. 20 / 16) |
| `CUDA not available` | fall back to a CPU sorter; check `torch.cuda.is_available()` |
| Sorter not found | `si.installed_sorters()`; install it or use a Docker image |

## References

- Sorters module:
  https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html
- Kilosort4 — https://github.com/MouseLand/Kilosort (GPL-3.0)

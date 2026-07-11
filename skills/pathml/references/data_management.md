# Data Management & Storage

PathML persists processed slides — tiles, masks, features, counts, and metadata — to a
single HDF5 file in the **h5path** format. This is how you avoid re-running expensive
preprocessing: process once, write `.h5path`, then reload for training or analysis. At
cohort scale, `SlideDataset` plus Dask spreads processing across workers.

## Persisting a slide (h5path)

```python
wsi.run(pipeline, tile_size=256, tile_stride=256, level=1)
wsi.write("processed/slide001.h5path")     # tiles + masks + metadata (+ counts)
```

Reload with PathML's h5path reader to get back a fully-populated `SlideData` (verify the
exact reader entry point for your version — recent PathML exposes a `read`/`SlideData`
h5path loader). You can also open the raw HDF5 with `h5py` for memory-mapped access to
individual tiles without materializing the whole slide:

```python
import h5py
with h5py.File("processed/slide001.h5path", "r") as f:
    # inspect the group/dataset layout, then pull only what you need
    ...
```

An h5path file is hierarchical: slide metadata, a `tiles` group (each tile's image,
coords, and per-tile masks), and extracted features/counts. Use `h5py` when you want to
stream a subset rather than load everything.

## Tiling strategies

| Strategy | How | Use when |
| --- | --- | --- |
| Non-overlapping | `tile_stride == tile_size` | classification, embeddings; fastest, no redundancy |
| Overlapping | `tile_stride < tile_size` | segmentation/detection; reduces boundary artifacts |
| Tissue-only | tile, then keep tiles whose `tile.masks["tissue"]` coverage exceeds a threshold | sparse tissue; skip background |

Tissue-only filtering after `TissueDetectionHE`:

```python
kept = [t for t in wsi.tiles
        if "tissue" in t.masks and t.masks["tissue"].mean() > 0.5]
```

## Stitching predictions back

After per-tile inference, reassemble a full-resolution map. With overlapping tiles,
blend the overlaps (average or distance-weighted) to avoid seams; with non-overlapping
tiles, place each tile at its `coords`. Track each tile's `coords` and the target level
dimensions so the reconstruction lands in the right coordinate frame.

## Distributed processing with Dask

`run` fans tiles across a Dask cluster when you pass `distributed=True` and a client:

```python
import glob
from dask.distributed import Client, LocalCluster
from pathml.core import SlideDataset, HESlide

cluster = LocalCluster(n_workers=8, threads_per_worker=2, memory_limit="8GB")
client  = Client(cluster)                       # dashboard at localhost:8787

paths   = glob.glob("raw/**/*.svs", recursive=True)
dataset = SlideDataset([HESlide(p) for p in paths])
dataset.run(pipeline, tile_size=256, tile_stride=256, level=1,
            distributed=True, client=client)

for slide in dataset:
    slide.write(f"processed/{slide.name}.h5path")

client.close(); cluster.close()
```

Worker sizing: image processing is CPU-bound (favor more single-thread processes);
GPU transforms (Mesmer, model inference) want fewer workers with the GPU. See the `dask`
skill for cluster tuning.

## Batch and HPC workflows

- **Sequential** (memory-safe): loop over paths, `run`, `write`, move on — process is
  released between slides.
- **HPC job arrays** (SLURM/PBS): write a one-slide script that takes a path argument
  and `write`s the h5path, then submit an array over a slide-list file. One slide per
  array task parallelizes cleanly without a shared Dask cluster.

## Feature stores

For tile-embedding or MIL workflows, extract per-tile features once and store them
compactly. A plain HDF5 with a `features` array plus a `coords` array (and slide-level
attrs) is enough; a `float32` memmap is convenient for random-access training. Keep the
feature store separate from the h5path so you can regenerate embeddings without
reprocessing pixels.

```python
import h5py
with h5py.File("features/slide001.h5", "w") as f:
    f.create_dataset("features", data=features, compression="gzip", chunks=True)
    f.create_dataset("coords", data=coords)
    f.attrs["model"] = "resnet50"
```

## Project layout and provenance

Keep raw slides, processed h5path, features, models, and results in separate trees, and
maintain a slide manifest (id, path, cohort, tissue, scanner, magnification, stain)
joined to clinical metadata by slide id. Record processing parameters (pipeline,
`tile_size`, `level`, PathML version) so runs are reproducible. For large datasets,
version with DVC and validate transfers with checksums.

## Performance and troubleshooting

- **Compression vs speed** — `gzip` level ~4 with chunking is a good default; raise to 9
  for archival, drop for hot I/O.
- **Chunk to match access** — one tile per chunk for tile-at-a-time reads.
- **Files too large** — store only what you need, use `uint8` for images (not float),
  drop redundant intermediates.
- **Slow I/O** — tune chunking, lower compression, use SSD/local scratch on HPC.
- **Corruption/loss** — checksum after transfers, back up data *and* the manifest.

## External references

- PathML data API: https://pathml.readthedocs.io/en/latest/
- HDF5 / h5py: https://docs.h5py.org/ · Dask: https://docs.dask.org/ · DVC: https://dvc.org/

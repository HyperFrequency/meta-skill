# Multiparametric Imaging (CODEX, Vectra, Multiplex IF)

Multiparametric imaging measures many protein markers per cell in situ. PathML's
strongest support is for **CODEX** (cyclic IF, 40+ markers) and **Vectra Polaris**
(multispectral IF, 6-8 markers); the same `SegmentMIF` → `QuantifyMIF` path applies to
other multiplex IF stacks. The workflow is always: collapse the raw acquisition into one
multichannel image, segment cells with Mesmer, quantify per-cell marker expression into
an `AnnData`, then analyze with `scanpy`/`squidpy`.

> PathML targets multiplex **immunofluorescence**. For MERFISH / imaging spatial
> transcriptomics (barcode decoding, transcript-to-cell assignment), use a dedicated
> spatial-transcriptomics toolchain — do not assume PathML classes for it.

## CODEX

### Load

```python
from pathml.core import CODEXSlide
codex = CODEXSlide("path/to/codex_dir/")   # directory of per-cycle, per-channel TIFFs
```

CODEX data is a directory of tiles per acquisition cycle plus a channel-names file.
Inspect `codex.channel_names` and the channel/cycle counts before building the pipeline
so you can map marker names to channel indices.

### Pipeline

```python
from pathml.preprocessing import Pipeline, CollapseRunsCODEX, SegmentMIF, QuantifyMIF

codex_pipeline = Pipeline([
    CollapseRunsCODEX(z=2),                         # 1. pick focal plane, merge cycles
    SegmentMIF(                                     # 2. Mesmer cell segmentation
        model="mesmer",
        nuclear_channel=<dapi_index>,
        cytoplasm_channel=<membrane_index>,
        image_resolution=0.377,                     # microns/pixel — must be accurate
    ),
    QuantifyMIF(segmentation_mask_name="cell_segmentation"),  # 3. -> codex.counts
])
codex.run(codex_pipeline)

cell_table = codex.counts     # AnnData: cells x markers
```

`CollapseRunsCODEX` consolidates the multi-cycle stack into a single (H, W, C) image and
selects a z-slice; `z` is the focal plane index.

## Vectra

Vectra stores multispectral data in `.qptiff`. Load with `VectraSlide`, collapse with
`CollapseRunsVectra`, then the identical `SegmentMIF`/`QuantifyMIF` steps:

```python
from pathml.core import VectraSlide
from pathml.preprocessing import Pipeline, CollapseRunsVectra, SegmentMIF, QuantifyMIF

vectra = VectraSlide("slide.qptiff")
vectra.run(Pipeline([
    CollapseRunsVectra(),
    SegmentMIF(model="mesmer", nuclear_channel=0, cytoplasm_channel=1, image_resolution=0.5),
    QuantifyMIF(segmentation_mask_name="cell_segmentation"),
]))
```

## Cell segmentation with Mesmer

`SegmentMIF` wraps DeepCell's **Mesmer** model. It needs a **nuclear** channel and a
**cytoplasm/membrane** channel (by index) and the true **microns-per-pixel**
(`image_resolution`); a wrong resolution is the most common cause of poor segmentation.

Choosing the membrane channel by tissue:

- immune-rich tissue → a pan-leukocyte marker (e.g. CD45),
- epithelial/tumor tissue → pan-cytokeratin (panCK),
- mixed → a universal membrane marker, or average several membrane channels.

Mesmer runs on GPU locally through DeepCell; for GPU-free inference DeepCell also offers
a hosted API. Verify which segmentation entry points your PathML version exposes.

## Quantification → AnnData

`QuantifyMIF` measures per-cell marker statistics over the segmentation mask and writes
an `AnnData` to `slide.counts`:

- `adata.X` — cells × markers expression matrix,
- `adata.obs` — per-cell metadata (id, area, centroid, ...),
- `adata.var` — marker metadata,
- `adata.obsm["spatial"]` — cell centroid coordinates.

Because the result is a standard `AnnData`, everything downstream is `scanpy`/`squidpy`
(and `anndata` for IO/concatenation). Combine slides:

```python
import anndata as ad
combined = ad.concat([s.counts for s in slides], label="slide", keys=slide_ids)
combined.write("codex_cohort.h5ad")
```

## Downstream analysis (scanpy / squidpy)

PathML stops at the cell table. Do phenotyping and spatial statistics with the scverse
tools:

```python
import scanpy as sc, squidpy as sq

# phenotyping
sc.pp.normalize_total(adata); sc.pp.log1p(adata); sc.pp.scale(adata, max_value=10)
sc.pp.pca(adata); sc.pp.neighbors(adata); sc.tl.umap(adata); sc.tl.leiden(adata)

# spatial neighborhood enrichment
sq.gr.spatial_neighbors(adata, coord_type="generic")
sq.gr.nhood_enrichment(adata, cluster_key="cell_type")
sq.gr.co_occurrence(adata, cluster_key="cell_type")
sq.gr.spatial_autocorr(adata, mode="moran")          # Moran's I
```

Cell-type calling can be threshold-based on canonical markers (CD3 → T cell, CD20 → B
cell, CD68 → macrophage, panCK → tumor) or unsupervised (Leiden clusters annotated by
marker means). See the `scanpy` and `anndata` skills for the full downstream pipeline.

## Batch processing

Process a cohort with `SlideDataset` + Dask (details in `data_management.md`), then
write one `.h5ad` per slide or a concatenated cohort object. Track batch/slide identity
in `adata.obs` and apply batch correction before pooling experiments.

## Quality control

- Visualize segmentation on a few crops before trusting a whole cohort.
- Check the cell-size distribution for over/under-segmentation.
- Filter low-signal cells (low total intensity, few markers detected) in `scanpy`.
- Consider background subtraction before quantification to reduce autofluorescence.

## Troubleshooting

- **Poor segmentation** — wrong `image_resolution`, wrong nuclear/cytoplasm channel
  indices, or a poorly chosen membrane marker.
- **Low marker intensity** — verify channel↔marker mapping; inspect raw images for
  focus/exposure issues; check background subtraction.
- **Cell types don't match expectation** — set data-driven thresholds from the marker
  distributions rather than fixed cutoffs.

## External references

- PathML multiparametric API: https://pathml.readthedocs.io/en/latest/api_multiparametric_reference.html
- DeepCell Mesmer: https://www.deepcell.org/
- Scanpy: https://scanpy.readthedocs.io/ · Squidpy: https://squidpy.readthedocs.io/

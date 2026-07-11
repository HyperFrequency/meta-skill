# Graph Construction & Spatial Representation

PathML's `pathml.graph` module turns segmented tissue into graphs for graph-neural-
network models. It implements the **HACT** (hierarchical cell-to-tissue) representation
used by `HACTNet`: a fine **cell graph** built from nucleus instances, a coarse **tissue
graph** built from superpixels, and an **assignment matrix** linking each cell to the
tissue region that contains it. Node features are handcrafted morphology/texture
descriptors (or learned embeddings), and the output is PyTorch-Geometric-compatible so
you can feed it straight into a GNN.

> The `pathml.graph` API was added later than the core/preprocessing modules and its
> signatures shift across PathML major versions. Use the pieces below as the map; verify
> exact argument names against the `pathml.graph` API reference for your version.

## The three pieces

### Cell graph (KNN over nucleus centroids)

Detect nuclei (HoVer-Net or another instance segmenter), reduce to an instance map,
then connect each cell to its nearest neighbors.

```python
from pathml.graph import KNNGraphBuilder
from pathml.graph.utils import get_full_instance_map

# instance map + per-instance centroids from a segmentation model
instance_map, instance_centroids = get_full_instance_map(wsi, patch_size=256)

cell_graph = KNNGraphBuilder(k=5, thresh=50, add_loc_feats=True).process(
    instance_map, features=node_features,
)
```

- `k` — neighbors per cell.
- `thresh` — maximum edge distance (pixels); prunes long spurious edges.
- `add_loc_feats` — append normalized (x, y) location to node features.

### Tissue graph (RAG over superpixels)

Oversegment the tissue into superpixels, merge similar neighbors, then build a
region-adjacency graph.

```python
from pathml.graph import ColorMergedSuperpixelExtractor, RAGGraphBuilder

superpixels = ColorMergedSuperpixelExtractor(
    superpixel_size=200, compactness=20, blur_kernel_size=1,
).process(image)

tissue_graph = RAGGraphBuilder(add_loc_feats=True).process(
    superpixels, features=superpixel_features,
)
```

Nodes are tissue regions; edges connect spatially adjacent superpixels.

### Assignment matrix (cell → tissue)

Link the two levels so the GNN can pool cell features into their enclosing tissue
regions.

```python
from pathml.graph.utils import build_assignment_matrix

assignment = build_assignment_matrix(instance_centroids, superpixels)
```

### Packaging for HACTNet

The paired cell graph, tissue graph, and assignment are carried by `HACTPairData`
(a `torch_geometric.data.Data` subclass), which batches through a PyG `DataLoader` and
is consumed directly by `HACTNet` (see `machine_learning.md`).

```python
from pathml.graph.utils import HACTPairData

data = HACTPairData(
    x_cell=cell_graph.node_features,     edge_index_cell=cell_graph.edge_index,
    x_tissue=tissue_graph.node_features, edge_index_tissue=tissue_graph.edge_index,
    assignment=assignment, target=label,
)
```

## Node features

`GraphFeatureExtractor` computes handcrafted descriptors per region/cell — shape
(area, perimeter, eccentricity, solidity, axis lengths, orientation) and texture
(Haralick/GLCM, LBP). You can also attach learned embeddings from a CNN, or per-cell
marker means from `QuantifyMIF` (for multiplex data).

```python
from pathml.graph import GraphFeatureExtractor

extractor = GraphFeatureExtractor()
features = extractor.process(image, instance_map)   # per-instance feature table
```

Normalize features (z-score) before training so morphology and intensity scales are
comparable.

## Downstream spatial analysis — hand off, don't reimplement

PathML builds graphs for GNNs; it does not aim to be a spatial-statistics library. Once
you have segmented cells with coordinates and (for multiplex) marker expression in an
`AnnData` (`slide.counts`), do neighborhood and interaction analysis with the
established tools:

- **`squidpy`** — spatial neighbor graphs, neighborhood enrichment
  (`sq.gr.nhood_enrichment`), co-occurrence, Ripley's K/L, Moran's I
  (`sq.gr.spatial_autocorr`).
- **`scanpy`** — clustering (Leiden), UMAP, marker ranking on the same `AnnData`.
- **`networkx`** — classical topology metrics (degree, clustering coefficient,
  centrality) on an exported adjacency; PathML graphs convert to a NetworkX graph for
  visualization and analysis.

This split matters: build the graph in PathML for model input, analyze spatial pattern
in `squidpy`/`scanpy`.

## End-to-end sketch

```python
# 1. segment nuclei (HoVer-Net) -> instance map + centroids
instance_map, centroids = get_full_instance_map(wsi, patch_size=256)

# 2. features per cell
features = GraphFeatureExtractor().process(wsi_image, instance_map)

# 3. cell graph + tissue graph + assignment
cell_graph   = KNNGraphBuilder(k=5, thresh=50, add_loc_feats=True).process(instance_map, features)
superpixels  = ColorMergedSuperpixelExtractor(superpixel_size=200).process(wsi_image)
tissue_graph = RAGGraphBuilder(add_loc_feats=True).process(superpixels, tissue_features)
assignment   = build_assignment_matrix(centroids, superpixels)

# 4. package -> HACTNet input (see machine_learning.md)
data = HACTPairData(...)
```

## Performance

- Large sections: build graphs tile-by-tile and merge, or downsample to a working
  pyramid level; use sparse adjacency.
- Convert pixel distances to microns (via `openslide.mpp-x`) so `thresh`/neighbor radii
  are biologically meaningful and comparable across scanners.
- Handle boundary cells with a tissue mask so partial cells at tile edges don't create
  spurious nodes.

## External references

- PathML graph API: https://pathml.readthedocs.io/en/latest/api_graph_reference.html
- HACTNet / HACT representation: Pati et al., "Hierarchical Graph Representations in
  Digital Pathology," Medical Image Analysis, 2022.
- PyTorch Geometric: https://pytorch-geometric.readthedocs.io/ · squidpy:
  https://squidpy.readthedocs.io/

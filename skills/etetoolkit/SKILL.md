---
name: etetoolkit
version: 0.1.0
description: >-
  Environment for Tree Exploration (ETE / the `ete3` Python package) — a toolkit for
  phylogenetic and hierarchical tree analysis. Use when you need to read/write Newick,
  NHX, PhyloXML or NeXML trees; traverse, prune, reroot, ladderize, or compare topologies
  (Robinson-Foulds); detect duplication/speciation events and infer orthologs/paralogs
  from gene trees (`PhyloTree`); query or build trees from the NCBI Taxonomy database
  (`NCBITaxa`); score clustering dendrograms with silhouette / Dunn metrics (`ClusterTree`);
  or render publication-quality tree figures (PDF/SVG/PNG) with custom node styles and
  faces. Do NOT use for multiple-sequence alignment or de-novo tree inference itself
  (use MAFFT/RAxML/IQ-TREE), for generic non-tree tabular data (use `data-analysis`),
  for general graphs that are not trees (use `networkx`), for ordinary statistical plots
  (use `matplotlib`/`seaborn`), or for the newer `ete4` package whose import paths and API differ.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "GPL-3.0 (ETE Toolkit / ete3)"
---

# ETE Toolkit (Phylogenetic Trees)

## Overview

ETE (Environment for Tree Exploration) is a mature Python library for manipulating,
analyzing, and drawing tree-shaped data — most commonly phylogenetic trees, but also gene
trees, taxonomies, and clustering dendrograms. This skill targets the stable `ete3`
package. Everything hangs off a single node object (`Tree`, an alias of `TreeNode`) where
each node is itself a subtree, plus three specializations:

- `PhyloTree` — gene/species trees with linked alignments and evolutionary-event inference.
- `NCBITaxa` — offline queries against a local copy of the NCBI Taxonomy database.
- `ClusterTree` — dendrograms with an attached numeric data matrix and cluster-quality metrics.

Use this file as a router. Concrete method signatures live in
[references/api-reference.md](references/api-reference.md), end-to-end recipes in
[references/workflows.md](references/workflows.md), and all styling/rendering detail in
[references/visualization.md](references/visualization.md).

## When to Use This Skill

- Loading, converting, or editing tree files (Newick formats 0-100, NHX, PhyloXML, NeXML).
- Structural edits: prune to a taxon set, reroot (outgroup or midpoint), collapse/detach
  nodes, resolve polytomies, ladderize.
- Comparing two or more trees by Robinson-Foulds distance or shared bipartitions.
- Gene-tree analysis: label species, detect duplication vs speciation nodes, extract
  orthologs/paralogs, split gene families by duplication.
- Taxonomy work: translate names ↔ taxids, fetch lineages/ranks, build a species topology
  connecting a set of taxa.
- Scoring hierarchical clustering results (silhouette, Dunn) against a data matrix.
- Producing publication figures: styled nodes, aligned faces (text, charts, heatmaps,
  sequence motifs), rectangular or circular layouts, to PDF/SVG/PNG.

## When NOT to Use This Skill

- **Building the tree in the first place** — ETE does not infer phylogenies from sequences.
  Run alignment (MAFFT, MUSCLE) and inference (RAxML, IQ-TREE, FastTree, PhyML) elsewhere,
  then load the resulting Newick here. (`ete3 build` only *orchestrates* those external
  tools; it is not itself an inference engine.)
- **Non-tree tabular analysis** — use `data-analysis`, `polars`, or `scikit-learn`.
- **General graphs (cycles, DAGs, arbitrary networks)** — use `networkx`.
- **Ordinary statistical charts** (scatter, bar, distribution) — use `matplotlib`/`seaborn`;
  ETE draws trees, not data plots.
- **The `ete4` package** — imports (`from ete4 import Tree`) and several APIs changed.
  This skill's examples are `ete3`-specific.

## Setup

```bash
uv pip install ete3            # core library
```

Rendering (`tree.render(...)`, `tree.show()`) and the GUI require Qt/PyQt5, which is a
system dependency, not a pip-only install:

```bash
# macOS
brew install qt@5 && uv pip install PyQt5
# Debian/Ubuntu
sudo apt-get install python3-pyqt5 python3-pyqt5.qtsvg
```

Headless servers additionally need a virtual display (`xvfb-run python your_script.py`).
Tree *manipulation and analysis work without Qt* — only rendering needs it.

The first `NCBITaxa()` instantiation downloads and builds a ~300 MB SQLite database at
`~/.etetoolkit/taxa.sqlite`; this happens once. Refresh with
`ncbi.update_taxonomy_database()`.

## Core Capabilities

Each capability below is a summary; follow the reference links for full signatures,
parameters, and worked examples.

### 1. Tree I/O and manipulation

```python
from ete3 import Tree
tree = Tree("tree.nw", format=1)          # format 0-100 selects which fields are parsed
tree.prune(["sp1", "sp2", "sp3"], preserve_branch_length=True)
tree.set_outgroup(tree.get_midpoint_outgroup())
tree.write(outfile="rooted.nw", format=5)
```

Traversal (`preorder`/`postorder`/`levelorder`), node lookup (`tree & "name"`,
`search_nodes`, `get_common_ancestor`), topology edits (`detach`, `delete`,
`resolve_polytomy`, `ladderize`), and distances (`get_distance`, `get_farthest_leaf`) are
in [references/api-reference.md](references/api-reference.md). Newick format codes and NHX
custom-feature persistence are covered there too.

### 2. Phylogenetic analysis (`PhyloTree`)

```python
from ete3 import PhyloTree
gt = PhyloTree("gene_tree.nw", alignment="aln.fasta", alg_format="fasta")
gt.set_species_naming_function(lambda name: name.split("_")[0])
events = gt.get_descendant_evol_events()   # tags each node .evoltype "D" or "S"
```

Each returned event exposes `.etype` ("D"/"S"), `.in_seqs`, and `.out_seqs`, which drive
ortholog/paralog extraction. `split_by_dups()`, `get_speciation_trees()`, and
`collapse_lineage_specific_expansions()` operate on gene families. Full recipes:
[references/workflows.md](references/workflows.md#phylogenetic-analysis).

### 3. NCBI taxonomy (`NCBITaxa`)

```python
from ete3 import NCBITaxa
ncbi = NCBITaxa()
taxids = ncbi.get_name_translator(["Homo sapiens", "Mus musculus"])
tree = ncbi.get_topology([9606, 10090])    # minimal tree connecting taxa
lineage = ncbi.get_lineage(9606)           # list of taxids root→leaf
```

Also: `get_taxid_translator`, `get_rank`, `get_descendant_taxa`, `annotate_ncbi_taxa`.
See [references/workflows.md](references/workflows.md#taxonomy-integration).

### 4. Tree comparison

```python
res = t1.compare(t2)                        # dict: norm_rf, rf, max_rf, ...
rf_tuple = t1.robinson_foulds(t2)           # (rf, max_rf, common_leaves, parts_t1, parts_t2, ...)
```

Prefer `compare()` for a normalized 0-1 distance; `robinson_foulds()` returns the raw
partitions but its tuple length has varied across `ete3` releases, so index by position
rather than unpacking a fixed count. Multi-tree distance matrices and consensus counting:
[references/workflows.md](references/workflows.md#tree-comparison).

### 5. Clustering analysis (`ClusterTree`)

```python
from ete3 import ClusterTree
ct = ClusterTree("((G1,G2),G3);", text_array=matrix_tsv)  # header + row names, tab-delimited
for node in ct.traverse():
    if not node.is_leaf():
        node.get_silhouette(); node.get_dunn()             # supports euclidean/pearson/spearman
```

Metrics (`intercluster_dist`, `intracluster_dist`, `.profile`) and heatmap display:
[references/api-reference.md](references/api-reference.md#clustertree-methods) and
[references/visualization.md](references/visualization.md).

### 6. Visualization

```python
from ete3 import Tree, TreeStyle
ts = TreeStyle(); ts.show_branch_support = True; ts.mode = "c"   # "r" rectangular, "c" circular
tree.render("fig.pdf", tree_style=ts)                            # also .png, .svg
```

`NodeStyle` (colors/shapes/line styles), the full Face catalogue (`TextFace`, `AttrFace`,
`CircleFace`, `RectFace`, `BarChartFace`, `PieChartFace`, `ImgFace`, `SeqMotifFace`),
`layout_fn` dynamic styling, faces positions/columns, legends, and heatmap/clade-highlight
patterns are all in [references/visualization.md](references/visualization.md). Use PDF or
SVG for publications (vector, editable); PNG for slides. Test interactively with
`tree.show()` before batch rendering.

## Command-line usage

`ete3` also installs a CLI for quick operations without writing Python. The main
subcommands are `view` (render/show), `compare` (RF between trees), `ncbiquery` (taxonomy
lookups), `mod` (topology edits like rerooting/pruning/sorting), and `build` (orchestrates
external aligners + tree builders into a phylogenomics pipeline). Discover exact flags with
`ete3 <subcommand> --help` — the flag surface changes between releases, so check `--help`
rather than assuming.

## Common failure modes

- **`ModuleNotFoundError: PyQt5` / Qt errors on `render`/`show`** — install Qt (see Setup)
  and run headless jobs under `xvfb-run`.
- **`write(format=...)` drops data** — the Newick format code controls which fields
  (internal names, support, branch lengths) are written. Custom node features survive only
  via NHX: `tree.write(features=["mykey"], outfile="t.nhx")`. Format table in the API reference.
- **Wrong orthologs** — `get_descendant_evol_events()` results depend entirely on the
  species-naming function; verify `leaf.species` is correct before trusting events.
- **Slow / memory-heavy on large trees (>10k leaves)** — iterate with `iter_leaves()` /
  `traverse()` instead of `get_leaves()`, and use `get_cached_content()` for repeated
  subtree-content lookups.
- **First `NCBITaxa()` call "hangs"** — it is building the ~300 MB local database; this is
  a one-time cost.

## Reference Documentation

- [references/api-reference.md](references/api-reference.md) — classes, constructors, node
  properties, traversal, topology ops, I/O, and per-class method catalogues
  (`PhyloTree`, `NCBITaxa`, `ClusterTree`), plus the Newick format table.
- [references/workflows.md](references/workflows.md) — task-oriented recipes for tree
  operations, gene-tree/orthology analysis, tree comparison, taxonomy integration,
  clustering, and batch processing.
- [references/visualization.md](references/visualization.md) — `TreeStyle`, `NodeStyle`,
  the Face catalogue, layout functions, circular layouts, legends, and advanced figures
  (heatmaps, clade highlighting, evolutionary-event annotation).

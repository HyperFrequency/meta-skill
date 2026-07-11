# ETE Toolkit Workflows

Task-oriented recipes for `ete3`. Each block is self-contained. See
[api-reference.md](api-reference.md) for signatures and [visualization.md](visualization.md)
for rendering.

## Contents

- [Basic tree operations](#basic-tree-operations)
- [Phylogenetic analysis](#phylogenetic-analysis)
- [Tree comparison](#tree-comparison)
- [Taxonomy integration](#taxonomy-integration)
- [Clustering analysis](#clustering-analysis)
- [Batch processing](#batch-processing)

## Basic tree operations

### Load, inspect, extract a subtree

```python
from ete3 import Tree

tree = Tree("my_tree.nw", format=1)
print(tree.get_ascii(show_internal=True))
print(f"{len(tree)} leaves, {len(list(tree.traverse()))} nodes")

# Extract a monophyletic clade to its own file
ancestor = tree.get_common_ancestor(["sp1", "sp2", "sp3"])
ancestor.copy().write(outfile="clade.nw")
```

### Prune and reroot

```python
tree.prune(["taxon1", "taxon2", "taxon3"], preserve_branch_length=True)

# Root on an outgroup, or at the midpoint if no outgroup is known
tree.set_outgroup(tree & "Outgroup")
tree.set_outgroup(tree.get_midpoint_outgroup())
tree.write(outfile="rooted.nw")
```

### Annotate nodes and persist with NHX

```python
metadata = {"sp1": {"habitat": "marine", "temp": 20},
            "sp2": {"habitat": "freshwater", "temp": 15}}
for leaf in tree:
    if leaf.name in metadata:
        leaf.add_features(**metadata[leaf.name])

# Custom features survive ONLY in NHX output
tree.write(outfile="annotated.nhx", features=["habitat", "temp"])
```

### Edit topology

```python
(tree & "unwanted_clade").detach()          # drop a whole subtree
(tree & "low_support_node").delete()        # collapse node, keep its children
(tree & "target").add_child(name="new_sp", dist=0.5)
tree.resolve_polytomy(recursive=True)
```

## Phylogenetic analysis

### Link an alignment and detect events

```python
from ete3 import PhyloTree, Tree

gt = PhyloTree("gene_tree.nw", format=1)
gt.link_to_alignment("alignment.fasta", alg_format="fasta")
gt.set_species_naming_function(lambda name: name.split("_")[0])

# Species Overlap (no species tree needed):
events = gt.get_descendant_evol_events()
# ...or reconciliation against a known species tree:
events = gt.get_descendant_evol_events(species_tree=Tree("species_tree.nw"))

dups = sum(1 for n in gt.traverse() if getattr(n, "evoltype", None) == "D")
spec = sum(1 for n in gt.traverse() if getattr(n, "evoltype", None) == "S")
print(f"{dups} duplications, {spec} speciations")
```

### Orthologs and paralogs of a query gene

```python
query = gt & "species1_gene1"
orthologs, paralogs = [], []
for event in events:
    if query in event.in_seqs:
        target = orthologs if event.etype == "S" else paralogs
        target.extend(s for s in event.out_seqs if s != query)

print("orthologs:", {s.name for s in orthologs})
print("paralogs :", {s.name for s in paralogs})
```

`etype == "S"` (speciation) across the event means the out-group sequences are orthologs;
`"D"` (duplication) means they are paralogs.

### Split gene families and collapse expansions

```python
for i, sub in enumerate(gt.split_by_dups()):
    species = {leaf.species for leaf in sub}
    sub.write(outfile=f"subfamily_{i}.nw")
    print(f"subfamily {i}: {len(sub)} genes / {len(species)} species")

gt.collapse_lineage_specific_expansions()   # merge species-specific in-paralog fans
```

### Test monophyly

```python
is_mono, clade_type, mrca = tree.check_monophyly(values=["sp1","sp2","sp3"],
                                                 target_attr="name")
# clade_type ∈ {"monophyletic","paraphyletic","polyphyletic"}
groups = tree.get_monophyletic(values=["typeA"], target_attr="type")
```

## Tree comparison

### Two trees

```python
res = tree1.compare(tree2)          # normalized, release-stable dict
print(f"norm RF: {res['norm_rf']:.3f}  ({res['rf']}/{res['max_rf']})")

tup = tree1.robinson_foulds(tree2)  # raw partitions; index positionally
rf, max_rf, common = tup[0], tup[1], tup[2]
parts_t1, parts_t2 = tup[3], tup[4]
print("partitions unique to tree1:", len(parts_t1 - parts_t2))
```

### Distance matrix over many trees

```python
import numpy as np
trees = [Tree(f) for f in tree_files]
n = len(trees)
D = np.zeros((n, n))
for i in range(n):
    for j in range(i + 1, n):
        D[i, j] = D[j, i] = trees[i].compare(trees[j])["norm_rf"]
```

### Bootstrap support / consensus counting

```python
ref = bootstrap_trees[0].copy()
counts = {}
for t in bootstrap_trees:
    tup = ref.robinson_foulds(t)
    for part in tup[4]:               # partitions found in t
        counts[part] = counts.get(part, 0) + 1
supported = {p: c for p, c in counts.items()
             if c / len(bootstrap_trees) >= 0.70}   # ≥70% support
```

## Taxonomy integration

### Build a species tree from names

```python
from ete3 import NCBITaxa
ncbi = NCBITaxa()
species = ["Homo sapiens", "Pan troglodytes", "Mus musculus", "Rattus norvegicus"]
name2taxid = ncbi.get_name_translator(species)
taxids = [name2taxid[s][0] for s in species]
tree = ncbi.get_topology(taxids)
tree.annotate_ncbi_taxa()
for node in tree.traverse():
    if getattr(node, "sci_name", None):
        print(node.sci_name, node.rank, node.taxid)
```

### Annotate an existing tree with lineages

```python
leaf_to_species = {"Hsap_g1": "Homo sapiens", "Ptro_g1": "Pan troglodytes"}
name2taxid = ncbi.get_name_translator(list(set(leaf_to_species.values())))
for leaf in tree:
    sp = leaf_to_species.get(leaf.name)
    if not sp:
        continue
    taxid = name2taxid[sp][0]
    lineage = ncbi.get_lineage(taxid)
    names = ncbi.get_taxid_translator(lineage)
    leaf.add_features(species=sp, taxid=taxid,
                      lineage=[names[t] for t in lineage])
```

### Query taxonomy directly

```python
primates = ncbi.get_name_translator(["Primates"])["Primates"][0]
all_primates = ncbi.get_descendant_taxa(primates, collapse_subspecies=True)
lineage = ncbi.get_lineage(9606)
ranks   = ncbi.get_rank(lineage)
names   = ncbi.get_taxid_translator(lineage)
for t in lineage:
    print(f"{ranks[t]:15s} {names[t]}")
```

## Clustering analysis

```python
from ete3 import ClusterTree

matrix = """#Names\tS1\tS2\tS3\tS4
Gene1\t1.5\t2.3\t0.8\t1.2
Gene2\t0.9\t1.1\t1.8\t2.1
Gene3\t2.1\t2.5\t0.5\t0.9
Gene4\t0.7\t0.9\t2.2\t2.4"""

ct = ClusterTree("((Gene1,Gene2),(Gene3,Gene4));", text_array=matrix)
for node in ct.traverse():
    if not node.is_leaf():
        print(node.name,
              f"silhouette={node.get_silhouette():.3f}",
              f"dunn={node.get_dunn():.3f}",
              f"inter={node.intercluster_dist:.3f}",
              f"intra={node.intracluster_dist:.3f}")

# Compare metrics: positive silhouette = coherent cluster
for metric in ("euclidean", "pearson", "spearman"):
    for node in ct.traverse():
        if not node.is_leaf():
            s = node.get_silhouette(distance=metric)
            print(metric, node.name, f"{s:.3f}", "good" if s > 0 else "poor")
```

## Batch processing

```python
import os
from ete3 import Tree

os.makedirs("processed", exist_ok=True)
for fn in os.listdir("input_trees"):
    if not fn.endswith(".nw"):
        continue
    tree = Tree(os.path.join("input_trees", fn))
    tree.set_outgroup(tree.get_midpoint_outgroup())
    tree.resolve_polytomy(recursive=True)
    # drop weakly-supported internal nodes (collapse, don't detach)
    for node in list(tree.traverse()):
        if not node.is_leaf() and not node.is_root() \
           and getattr(node, "support", 1.0) < 0.5:
            node.delete()
    tree.write(outfile=os.path.join("processed", f"processed_{fn}"))
```

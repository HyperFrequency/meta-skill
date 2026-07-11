# ETE Toolkit (`ete3`) API Reference

Method signatures and node properties for the `ete3` package. All examples assume
`from ete3 import Tree` (and other classes as needed). `Tree` is an alias for `TreeNode`;
every node *is* the root of its own subtree.

## Constructors

### `Tree` / `TreeNode`

```python
Tree(newick=None, format=0, dist=None, support=None, name=None, quoted_node_names=False)
```

- `newick` — a Newick string, or a path to a `.nw`/`.nwk` file.
- `format` — Newick flavor (see [Newick formats](#newick-formats)).
- `dist` — branch length to parent (default `1.0`).
- `support` — support/bootstrap value on the node (default `1.0`).
- `name` — node label.

### `PhyloTree`

```python
PhyloTree(newick=None, alignment=None, alg_format="fasta",
          sp_naming_function=<first 3 chars>, format=0)
```

Extends `TreeNode` with alignment linkage and evolutionary-event inference. `alg_format`
is `"fasta"` or `"phylip"`. If `sp_naming_function` is omitted, the species is taken from
the first three characters of the leaf name.

### `ClusterTree`

```python
ClusterTree(newick, text_array=None)
```

`text_array` is a tab-delimited matrix string: a header row starting with `#Names`
followed by the sample columns, then one row per leaf (row name matching a leaf name).

### `NCBITaxa`

```python
NCBITaxa(dbfile=None)   # first call builds ~/.etetoolkit/taxa.sqlite (~300 MB)
```

## Node properties

| Property   | Type        | Meaning                          | Default    |
|------------|-------------|----------------------------------|------------|
| `name`     | str         | node label                       | `"NoName"` |
| `dist`     | float       | branch length to parent          | `1.0`      |
| `support`  | float       | support / bootstrap              | `1.0`      |
| `up`       | TreeNode    | parent (`None` at root)          | `None`     |
| `children` | list        | direct children                  | `[]`       |

Custom data attaches as *features*:

```python
node.add_feature("habitat", "marine")
node.add_features(temp=20, depth=100)
value = getattr(node, "habitat", None)   # safe access
```

## Navigation and traversal

```python
node.is_leaf(); node.is_root(); len(node)      # len = number of leaves under node
node.up; node.children; node.get_tree_root()

for n in tree.traverse("preorder"):   ...      # root → children
for n in tree.traverse("postorder"):  ...      # children → root (bottom-up)
for n in tree.traverse("levelorder"): ...      # breadth-first
for n in tree.iter_descendants("postorder"): ...   # excludes the start node

leaves      = tree.get_leaves()                # or: for leaf in tree
descendants = tree.get_descendants()
ancestors   = node.get_ancestors()
mrca        = tree.get_common_ancestor("A", "B", "C")
matches     = tree.search_nodes(name="X")
node        = tree & "X"                        # shortcut for first match
```

For large trees prefer iterators (`iter_leaves`, `iter_search_nodes`, `iter_descendants`)
to avoid materializing lists.

## Construction and modification

```python
t = Tree()
a = t.add_child(name="A", dist=1.0)
c = a.add_sister(name="C", dist=1.5)
t.populate(10)                          # random topology with 10 leaves

node.detach()                           # remove node AND its subtree
node.delete()                           # remove node, reconnect children to parent
tree.prune(["A", "B", "C"], preserve_branch_length=True)   # keep only listed leaves
```

### Rooting and shape

```python
tree.set_outgroup(tree & "Outgroup")
tree.set_outgroup(tree.get_midpoint_outgroup())
tree.unroot()
tree.resolve_polytomy(recursive=True)   # multifurcations → bifurcations
tree.ladderize(direction=0)             # sort branches by subtree size
tree.convert_to_ultrametric()           # equalize root-to-leaf path lengths
```

### Copying

```python
tree.copy()                 # default "cpickle": full fidelity, preserves feature types
tree.copy("newick")         # fastest: topology + name/dist/support only
tree.copy("newick-extended")# includes custom features as text
tree.copy("deepcopy")       # slowest: handles arbitrary python objects on nodes
```

## Distances and comparison

```python
tree.get_distance("A", "B")                     # summed branch length
tree.get_distance("A", "B", topology_only=True) # number of edges
node.get_farthest_leaf()                        # (node, distance)

is_mono, clade_type, mrca = tree.check_monophyly(values=["A","B"], target_attr="name")
# clade_type ∈ {"monophyletic","paraphyletic","polyphyletic"}
clades = tree.get_monophyletic(values=["typeA"], target_attr="type")

res = t1.compare(t2)          # dict incl. "rf", "max_rf", "norm_rf", "effective_tree_size"
tup = t1.robinson_foulds(t2)  # tuple; tup[0]=rf, tup[1]=max_rf, tup[2]=common_leaves,
                              # tup[3]/tup[4]=partition sets. Tuple LENGTH varies by
                              # release — index positionally, do not fixed-count unpack.
```

## Input / output

```python
Tree("(A:1,(B:1,C:1):0.5);")          # from string
Tree("tree.nw", format=1)             # from file with internal names

tree.write()                          # Newick string
tree.write(format=5, outfile="out.nw")
tree.write(features=["habitat","temp"], outfile="out.nhx")   # NHX persists custom features

print(tree.get_ascii(show_internal=True))   # ASCII art in the terminal
```

### Newick formats

| Format | Contents                                            |
|--------|-----------------------------------------------------|
| 0      | flexible: branch lengths + leaf names (default)     |
| 1      | internal node names                                 |
| 2      | branch lengths + all names + support                |
| 5      | internal names + branch lengths                     |
| 8      | all names only                                      |
| 9      | leaf names only                                     |
| 100    | topology only                                       |

Reading with a stricter format than the file supports raises an error — start with
`format=0` if unsure, or `format=1` when internal names must be preserved.

## `PhyloTree` methods

```python
tree.link_to_alignment("aln.fasta", alg_format="fasta")   # populates leaf.sequence
tree.set_species_naming_function(lambda name: name.split("_")[0])

events = tree.get_descendant_evol_events()          # Species Overlap algorithm
events = tree.get_descendant_evol_events(species_tree=Tree("species.nw"))  # reconciliation
# each event: .etype ("D"/"S"), .in_seqs, .out_seqs; nodes gain .evoltype ("D"/"S")

tree.get_speciation_trees()                # ortholog subtrees
tree.split_by_dups()                       # split gene family at duplication nodes
tree.collapse_lineage_specific_expansions()
```

## `NCBITaxa` methods

```python
ncbi.get_name_translator(["Homo sapiens"])   # {'Homo sapiens': [9606]}
ncbi.get_taxid_translator([9606, 9598])      # {9606: 'Homo sapiens', 9598: 'Pan troglodytes'}
ncbi.get_rank([9606])                        # {9606: 'species'}
ncbi.get_lineage(9606)                       # [1, 131567, 2759, ..., 9606]
ncbi.get_descendant_taxa("Primates", collapse_subspecies=True)
ncbi.get_topology([9606, 9598, 9593])        # minimal tree connecting taxids
tree.annotate_ncbi_taxa()                    # adds .sci_name, .taxid, .rank, .named_lineage
ncbi.update_taxonomy_database()              # refresh local db
```

## `ClusterTree` methods

```python
tree.link_to_arraytable(matrix_string)
leaf.profile                                 # numpy array for the leaf
node.get_silhouette(distance="euclidean")    # also "pearson", "spearman"
node.get_dunn(distance="euclidean")
node.intercluster_dist; node.intracluster_dist; node.deviation
```

## Performance

```python
node2content = tree.get_cached_content()     # {node: set(leaves)}; amortize repeated lookups
for leaf in tree.iter_leaves(): ...          # memory-efficient vs get_leaves()
```

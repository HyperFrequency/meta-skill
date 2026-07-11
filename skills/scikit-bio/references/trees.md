# Phylogenetic Trees

Deep reference for `skbio.TreeNode` and `skbio.tree`. Return to `SKILL.md` for
the capability map.

`TreeNode` is a recursive node object: every node knows its `.children`,
`.parent`, `.name`, and branch `.length`. A whole tree is just its root node.

## Newick I/O

```python
from skbio import TreeNode
tree = TreeNode.read("tree.nwk", format="newick")   # format auto-detected too
tree.write("out.nwk", format="newick")
print(tree.ascii_art())                             # quick text visualization
```

For publication-quality figures, export Newick and render with `etetoolkit`
(ETE) or ggtree — scikit-bio only produces ASCII art.

## Construction from a distance matrix

```python
from skbio import DistanceMatrix
from skbio.tree import nj, upgma, gme, bme

dm = DistanceMatrix(
    [[0, 5, 9, 9], [5, 0, 10, 10], [9, 10, 0, 8], [9, 10, 8, 0]],
    ids=["A", "B", "C", "D"],
)

nj_tree    = nj(dm)      # neighbor joining (classic, unrooted)
upgma_tree = upgma(dm)   # UPGMA — assumes a molecular clock (ultrametric)
gme_tree   = gme(dm)     # greedy minimum evolution — scalable
bme_tree   = bme(dm)     # balanced minimum evolution — scalable
```

Use `gme` / `bme` for large numbers of taxa; they are far more scalable than
`nj`. `upgma` produces a rooted, ultrametric tree and should only be used when
the clock assumption is reasonable.

## Traversal

```python
for node in tree.traverse():        # every node
    ...
for node in tree.preorder():        # also postorder(), levelorder()
    ...
tips = list(tree.tips())            # leaves only
node = tree.find("taxon_name")      # locate by name
```

## Manipulation

```python
sub    = tree.shear(["A", "B", "C"])        # keep only these tips (see notes)
rooted = tree.root_at_midpoint()             # midpoint rooting
lca    = tree.lowest_common_ancestor(["A", "B"])

parent = tree.find("internal")
parent.append(TreeNode(name="new", length=0.5))   # add child
victim = tree.find("gone"); victim.parent.remove(victim)   # remove
```

`shear(names, strict=True, prune=True, inplace=False)` refines the tree to the
given tips. With `strict=True` (default) it raises if a name is missing; pass
`strict=False` to keep only the names that were found. It returns the sheared
tree. `shear` is the standard way to make a reference tree match a feature table
before UniFrac / Faith's PD.

## Distances & comparison

```python
# Patristic distance (sum of branch lengths between two tips)
d = tree.find("A").distance(tree.find("B"))

# All-pairs matrices
cophenetic = tree.cophenetic_matrix()        # DistanceMatrix over tips
tiptip     = tree.tip_tip_distances()

# Robinson-Foulds topological distance between two trees
rf       = tree1.compare_rfd(tree2)                    # count (float)
rf_prop  = tree1.compare_rfd(tree2, proportion=True)   # 0..1 normalized
```

`compare_rfd(other, proportion=False, rooted=None)` counts bipartitions (or
clades, if rooted) that differ; only taxa shared by both trees are considered.
There is **no** `robinson_foulds` method — that name will raise `AttributeError`.

For many trees at once, use the module function:

```python
from skbio.tree import rf_dists
dm = rf_dists([t1, t2, t3, t4], ids=["A", "B", "C", "D"])   # DistanceMatrix
```

Related comparison methods: `compare_subsets`, `compare_biparts`,
`compare_wrfd` (weighted RF), `compare_cophenet` (tip-distance correlation).

## Rooting notes

- `nj`, `gme`, `bme` produce **unrooted** trees; `upgma` is rooted.
- RF distance auto-selects rooted vs unrooted based on whether the calling tree
  is rooted; override with the `rooted=` argument.
- UniFrac needs a tree whose tips cover all feature IDs — see
  `references/diversity-ordination-stats.md`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `AttributeError: 'TreeNode' object has no attribute 'robinson_foulds'` | Use `compare_rfd` (pairwise) or `rf_dists` (many trees). |
| `shear` raises on missing names | A name is not in the tree — pass `strict=False`, or verify tip names via `{t.name for t in tree.tips()}`. |
| UniFrac `MissingNodeError` | Feature IDs not all present as tips — `tree.shear(feature_ids)` and align the `taxa=` list. |
| Unexpected RF value | Rooted/unrooted mismatch — set `rooted=` explicitly. |

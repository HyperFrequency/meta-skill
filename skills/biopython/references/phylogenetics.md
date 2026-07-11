# Phylogenetics — `Bio.Phylo`

One toolkit for reading, writing, building, manipulating, and drawing
phylogenetic trees. A `Tree` is a recursive structure of `Clade` nodes; leaves
(taxa) are terminal clades, internal nodes are non-terminal.

## Read / write / convert

```python
from Bio import Phylo

tree  = Phylo.read("tree.nwk", "newick")        # one tree
trees = list(Phylo.parse("trees.nwk", "newick")) # many
Phylo.write(tree, "out.xml", "phyloxml")
Phylo.convert("in.nwk", "newick", "out.nex", "nexus")
```

Formats: `newick` (most common), `nexus`, `phyloxml` (rich annotations,
colors, taxonomy), `nexml`, `cdao`.

## Navigation & traversal

```python
tree.root
tree.get_terminals()      # leaves
tree.get_nonterminals()   # internal nodes
tree.count_terminals()

for clade in tree.find_clades():                 # default preorder
    clade.name, clade.branch_length, clade.confidence
for clade in tree.find_clades(order="level"):    # breadth-first
    ...

tree.find_any(name="Species_A")                  # first match
tree.find_clades(lambda c: (c.branch_length or 0) > 0.5)  # predicate
```

## Analysis

```python
tree.total_branch_length()
tree.distance("Species_A", "Species_B")          # patristic distance
tree.common_ancestor("Species_A", "Species_B")   # MRCA clade
max(tree.depths().values())                       # depth root→furthest leaf
```

## Manipulation (mutates in place — copy first!)

```python
t = tree.copy()
t.prune("Species_A")                 # remove a taxon
t.ladderize()                        # sort clades by size (reverse=True too)
t.root_at_midpoint()                 # midpoint rooting
t.root_with_outgroup(t.find_any(name="Outgroup"))
```

To keep only a subset, prune everything else:

```python
keep = {"B", "C", "D"}
for leaf in t.get_terminals():
    if leaf.name not in keep:
        t.prune(leaf)
```

## Building trees

### From a distance matrix

```python
from Bio.Phylo.TreeConstruction import DistanceTreeConstructor, DistanceMatrix

dm = DistanceMatrix(
    names=["Alpha", "Beta", "Gamma", "Delta"],
    matrix=[[0],
            [0.23, 0],
            [0.45, 0.34, 0],
            [0.67, 0.58, 0.29, 0]],   # lower-triangular, including diagonal 0
)
ctor = DistanceTreeConstructor()
tree = ctor.upgma(dm)    # or ctor.nj(dm) for neighbor-joining
```

### From a multiple-sequence alignment

```python
from Bio import AlignIO
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor

msa = AlignIO.read("aln.aln", "clustal")
dm  = DistanceCalculator("identity").get_distance(msa)
tree = DistanceTreeConstructor().nj(dm)
tree.root_at_midpoint()
```

Distance models for `DistanceCalculator`: `identity`, `blastn`, `trans` (DNA);
`blosum62`, `pam250` (protein).

## Consensus (bootstrap trees)

```python
from Bio.Phylo.Consensus import majority_consensus, strict_consensus
boots = list(Phylo.parse("bootstrap.nwk", "newick"))
maj    = majority_consensus(boots, cutoff=0.5)
strict = strict_consensus(boots)
```

## Visualization

```python
Phylo.draw_ascii(tree)                    # console
Phylo.draw_ascii(tree, column_width=80)

import matplotlib.pyplot as plt           # publication figure
fig, ax = plt.subplots(figsize=(10, 8))
Phylo.draw(tree, axes=ax, do_show=False)
ax.set_title("Phylogeny")
plt.savefig("tree.png", dpi=300, bbox_inches="tight")

# annotate branches
Phylo.draw(tree, branch_labels=lambda c: f"{c.branch_length:.2f}"
           if c.branch_length else "")
```

## Patterns

**Bootstrap support onto internal nodes** (store as `confidence`):

```python
for node, support in zip(tree.get_nonterminals(), support_values):
    node.confidence = support
```

**Phylogenetic diversity** (sum of branch lengths in a subtree):

```python
def pd(tree):
    return sum(c.branch_length or 0 for c in tree.find_clades())
```

**Robinson–Foulds distance** (topology difference via bipartitions):

```python
def rf(t1, t2):
    bp = lambda t: {frozenset(x.name for x in c.get_terminals())
                    for c in t.get_nonterminals()}
    return len(bp(t1) ^ bp(t2))
```

## Gotchas

- Every mutating op (`prune`, `ladderize`, `root_*`) changes the tree in place —
  `tree.copy()` first if you need the original.
- Distance methods (UPGMA/NJ) are fast but assume clock-like / additive data;
  they are not maximum-likelihood or Bayesian inference. For ML/Bayesian trees
  shell out to RAxML/IQ-TREE/MrBayes and read the Newick back with `Phylo.read`.
- `DistanceMatrix.matrix` is lower-triangular including the zero diagonal.
- `tree.distance(a, b)` accepts clade names or clade objects.

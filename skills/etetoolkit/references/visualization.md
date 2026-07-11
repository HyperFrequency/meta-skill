# ETE Toolkit Visualization

Styling and rendering with `ete3`. Rendering requires Qt/PyQt5 (see the SKILL's Setup
section); tree analysis does not. Three building blocks: `TreeStyle` (whole-tree options),
`NodeStyle` (per-node appearance), and *Faces* (graphical elements attached to nodes),
usually driven by a `layout_fn`.

## Contents

- [Rendering basics](#rendering-basics)
- [TreeStyle](#treestyle)
- [NodeStyle](#nodestyle)
- [Faces](#faces)
- [Layout functions](#layout-functions)
- [Advanced figures](#advanced-figures)

## Rendering basics

```python
from ete3 import Tree
tree = Tree("tree.nw")

tree.render("out.png", w=800, h=600, units="px", dpi=300)   # raster: slides
tree.render("out.pdf", w=200, units="mm")                   # vector: publications
tree.render("out.svg")                                      # vector: editable
tree.show()                                                 # interactive GUI
```

`units` is `"px"`, `"mm"`, or `"in"`. Supplying only `w` auto-computes `h` from the aspect
ratio. Use PDF/SVG for anything going into a paper. Test with `show()` before batch runs.

## TreeStyle

```python
from ete3 import TreeStyle, TextFace
ts = TreeStyle()

ts.show_leaf_name = True
ts.show_branch_length = True
ts.show_branch_support = True
ts.show_scale = True

ts.scale = 50                 # pixels per branch-length unit
ts.branch_vertical_margin = 10
ts.min_leaf_separation = 10
ts.rotation = 0               # 0 = left→right, 90 = top→bottom

ts.mode = "r"                 # "r" rectangular (default), "c" circular
# circular options:
ts.mode = "c"; ts.arc_start = 0; ts.arc_span = 360   # full circle; 180 = semicircle

# title + legend
ts.title.add_face(TextFace("Species Phylogeny", fsize=20, bold=True), column=0)
ts.legend.add_face(TextFace("red = high support", fsize=10), column=0)
ts.legend_position = 1        # 1=TR, 2=TL, 3=BL, 4=BR

tree.render("tree.pdf", tree_style=ts)
```

## NodeStyle

`NodeStyle` sets *permanent* appearance on a node (persists on the object). Assign with
`node.set_style(...)`.

```python
from ete3 import NodeStyle
nstyle = NodeStyle()
nstyle["size"] = 10                 # marker size (px)
nstyle["shape"] = "circle"          # "circle", "square", "sphere"
nstyle["fgcolor"] = "blue"          # marker color
nstyle["bgcolor"] = "lightblue"     # subtree background wash
nstyle["hz_line_type"] = 0          # 0 solid, 1 dashed, 2 dotted
nstyle["hz_line_color"] = "black"
nstyle["hz_line_width"] = 2
nstyle["vt_line_type"] = 0
nstyle["draw_descendants"] = True   # False collapses the subtree visually
node.set_style(nstyle)
```

### Conditional styling example

```python
for node in tree.traverse():
    ns = NodeStyle()
    if node.is_leaf():
        ns["size"], ns["fgcolor"], ns["shape"] = 8, "darkgreen", "circle"
    else:
        strong = node.support > 0.9
        ns["size"] = 6 if strong else 4
        ns["fgcolor"] = "red" if strong else "gray"
        ns["shape"] = "sphere" if strong else "circle"
    node.set_style(ns)
```

## Faces

Faces are graphical elements added at a position/column around a node:

- Positions: `"branch-right"`, `"branch-top"`, `"branch-bottom"`, `"aligned"`
  (`"aligned"` snaps to a column at the tree edge — use it for leaf-level tabular data).
- `column` orders multiple faces left-to-right within a position.

Catalogue:

| Face            | Purpose                                              |
|-----------------|------------------------------------------------------|
| `TextFace`      | literal text (`fsize`, `fgcolor`, `bold`)            |
| `AttrFace`      | render a node feature by name, e.g. `AttrFace("temp")` |
| `CircleFace`    | colored circle (`radius`, `color`)                   |
| `RectFace`      | rectangle (`width`, `height`, `fgcolor`, `bgcolor`) — heatmap cells |
| `BarChartFace`  | bar chart from a list of values (`colors`, `labels`) |
| `PieChartFace`  | pie chart from proportions                           |
| `ImgFace`       | external image file (`width`, `height`)              |
| `SeqMotifFace`  | sequence / alignment motifs (with `PhyloTree`)       |

```python
from ete3 import TextFace, CircleFace, AttrFace
name  = TextFace(node.name, fsize=10)
attr  = AttrFace("temp", fsize=8)                 # shows node.temp
mark  = CircleFace(radius=5, color="blue")
node.add_face(name, column=0, position="branch-right")
```

## Layout functions

A `layout_fn` runs for every node at render time — the idiomatic way to build complex
figures. Set `ts.show_leaf_name = False` when you draw your own name faces to avoid
duplicates.

```python
from ete3 import TreeStyle, TextFace, CircleFace

for leaf in tree:
    leaf.add_feature("habitat", "marine" if "fish" in leaf.name else "land")

def layout(node):
    if node.is_leaf():
        color = "blue" if node.habitat == "marine" else "green"
        node.add_face(CircleFace(radius=5, color=color), column=0, position="aligned")
        node.add_face(TextFace(node.name, fsize=10), column=1, position="aligned")
    elif node.support:
        node.add_face(TextFace(f"{node.support:.2f}", fsize=8, fgcolor="red"),
                      column=0, position="branch-top")

ts = TreeStyle(); ts.layout_fn = layout; ts.show_leaf_name = False
tree.render("annotated.pdf", tree_style=ts)
```

Keep layout functions fast — they are called once per node. Precompute expensive values as
features beforehand.

## Advanced figures

### Highlight a clade

```python
def layout(node):
    members = {"sp1", "sp2", "sp3"}
    if not node.is_leaf() and {l.name for l in node.get_leaves()} == members:
        ns = NodeStyle(); ns["bgcolor"] = "yellow"; node.set_style(ns)
        node.add_face(TextFace("Clade A", fsize=14, bold=True, fgcolor="red"),
                      column=0, position="branch-top")
```

### Collapse a clade visually

```python
def layout(node):
    if not node.is_leaf() and len(node) > 20:
        ns = NodeStyle(); ns["draw_descendants"] = False
        ns["shape"], ns["size"], ns["fgcolor"] = "sphere", 20, "steelblue"
        node.set_style(ns)
        node.add_face(TextFace(f"[{len(node)} spp]", fsize=10),
                      column=0, position="branch-right")
```

### Heatmap alongside leaves

```python
from ete3 import RectFace, TextFace
def layout(node):
    if node.is_leaf():
        node.add_face(TextFace(node.name, fsize=8), column=0, position="aligned")
        for i, v in enumerate(node.data):          # node.data = list of floats in [0,1]
            level = int(255 * v)
            color = f"#{255 - level:02x}{level:02x}00"
            node.add_face(RectFace(20, 15, fgcolor=color, bgcolor=color),
                          column=i + 1, position="aligned")

ts = TreeStyle(); ts.layout_fn = layout; ts.show_leaf_name = False
for i in range(10):
    ts.aligned_header.add_face(TextFace(f"C{i+1}", fsize=8), column=i + 1)
```

### Annotate duplication / speciation events

```python
from ete3 import PhyloTree, NodeStyle, TextFace, TreeStyle
gt = PhyloTree("gene_tree.nw")
gt.set_species_naming_function(lambda x: x.split("_")[0])
gt.get_descendant_evol_events()

def layout(node):
    et = getattr(node, "evoltype", None)
    if et == "D":
        ns = NodeStyle(); ns["fgcolor"], ns["size"], ns["shape"] = "red", 10, "square"
        node.set_style(ns)
        node.add_face(TextFace("DUP", fsize=8, fgcolor="red", bold=True),
                      column=0, position="branch-top")
    elif et == "S":
        ns = NodeStyle(); ns["fgcolor"], ns["size"], ns["shape"] = "blue", 6, "circle"
        node.set_style(ns)

ts = TreeStyle(); ts.layout_fn = layout; ts.show_leaf_name = True
gt.render("gene_tree_events.pdf", tree_style=ts)
```

## Tips

- Prefer vector (PDF/SVG) output for publications; PNG for slides.
- Use `NodeStyle` for state that should persist; use `layout_fn` for render-time decoration.
- `"aligned"` position + incrementing `column` gives clean tabular annotations at leaves.
- On headless servers, wrap rendering in `xvfb-run`.

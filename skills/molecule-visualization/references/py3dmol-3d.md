# Interactive 3D Viewers with py3Dmol

Deep reference for self-contained HTML 3D viewers. py3Dmol wraps 3Dmol.js; the
output HTML embeds the viewer and the coordinates, so it opens in any browser with
no server. APIs are from `py3Dmol`.

## The four modes

The source skill exposed a `--mode` switch; the equivalent py3Dmol recipes are
below. Auto-detect from inputs: protein only → `protein`; protein + ligand →
`complex`; protein + pocket JSON → `pockets`; protein + multi-pose SDF →
`docking-results`.

| Mode | Inputs | Shows |
|------|--------|-------|
| `protein` | PDB | Cartoon, colored by chain / spectrum / b-factor |
| `complex` | PDB + ligand SDF | Protein cartoon + ligand sticks (+ pocket surface) |
| `pockets` | PDB + pocket JSON | Protein + spheres at pocket centers, sized/colored by score |
| `docking-results` | PDB + multi-model SDF | Protein + ranked poses colored best→worst |

## Base viewer and styles

```python
import py3Dmol

view = py3Dmol.view(width=800, height=600)
view.addModel(open("protein.pdb").read(), "pdb")
view.setStyle({"cartoon": {"color": "spectrum"}})
view.setBackgroundColor("white")          # dark for slides; see style-guide.md
view.zoomTo()
```

Representation options (pass as the style dict):

| Representation | Style dict |
|----------------|-----------|
| Cartoon (ribbon) | `{"cartoon": {"color": "spectrum"}}` |
| Sticks | `{"stick": {}}` |
| Ball-and-stick | `{"stick": {"radius": 0.15}, "sphere": {"scale": 0.25}}` |
| Space-filling | `{"sphere": {}}` |
| Surface | `view.addSurface(py3Dmol.VDW, {"opacity": 0.3})` |

Color schemes for cartoon: `"spectrum"`, `"chain"`, `{"prop": "b", "gradient": ...}`
for b-factor, or a fixed CSS color. Selections use AtomSpec dicts, e.g.
`{"chain": "A"}`, `{"resi": [57, 189, 195]}`, `{"model": -1}` (last-added model).

## Complex: protein + ligand + pocket surface

```python
view = py3Dmol.view(width=800, height=600)
view.addModel(open("protein.pdb").read(), "pdb")
view.setStyle({"cartoon": {"color": "spectrum"}})

view.addModel(open("ligand.sdf").read(), "sdf")   # becomes the last model
view.setStyle({"model": -1}, {"stick": {"colorscheme": "greenCarbon"}})

# translucent binding-pocket surface, restricted to residues near the ligand
view.addSurface(py3Dmol.VDW, {"opacity": 0.25}, {"within":
    {"distance": 6, "sel": {"model": -1}}})
view.zoomTo({"model": -1})
```

## Pockets: spheres from a scoring JSON

Read a pocket/druggability JSON (a list of pockets, each with a center `[x,y,z]`,
a volume, and a druggability score in 0-1). Add one custom sphere per pocket;
color by score and size by volume.

```python
import json
pockets = json.load(open("druggability.json"))

def score_color(s):
    return "green" if s > 0.7 else "orange" if s >= 0.4 else "red"

for p in pockets:
    x, y, z = p["center"]
    view.addSphere({
        "center": {"x": x, "y": y, "z": z},
        "radius": (p.get("volume", 100) ** (1/3)) / 2,   # ∝ volume
        "color": score_color(p.get("druggability", 0.5)),
        "opacity": 0.6,
    })
```

The exact JSON keys depend on whatever pocket-detection step produced the file —
read its schema and map `center` / `volume` / `score` accordingly rather than
assuming these names.

## Docking results: ranked poses overlaid

Load a multi-model SDF (one model per pose, ordered best→worst). Add each as its
own model and color by rank so the best pose stands out.

```python
poses = open("poses.sdf").read().split("$$$$\n")     # crude split; keep terminators
rank_colors = ["green", "yellowgreen", "yellow", "orange", "red"]
for i, block in enumerate(poses[:5]):
    if not block.strip():
        continue
    view.addModel(block + "$$$$\n", "sdf")
    view.setStyle({"model": -1}, {"stick": {"color": rank_colors[min(i, 4)]}})

# highlight the top pose with a translucent surface
view.addSurface(py3Dmol.VDW, {"opacity": 0.2}, {"model": 1})
```

For robust multi-pose parsing prefer RDKit's `Chem.SDMolSupplier` / `SDWriter` to
split and re-emit per-pose SDF blocks rather than string-splitting on `$$$$`.

## Writing the HTML

```python
view.write_html("view.html")          # py3Dmol ≥ 2.0
# fallback for older versions:
# html = view._make_html(); open("view.html", "w").write(html)
```

`write_html` produces a standalone file. If your rendering surface enforces a
strict Content-Security-Policy (some notebook/artifact contexts block the embedded
3Dmol.js), open the file directly in a browser instead.

## Practical tips

- Always `zoomTo()` (optionally scoped to the ligand/model) or the camera starts
  fully zoomed out.
- `spin` (`view.spin(True)`) is nice for slides but disable it for screenshots.
- Keep surfaces translucent (opacity 0.2-0.4) so the cartoon and ligand remain
  visible underneath.
- White background for print/publication; dark background reads better on a
  projector — see `style-guide.md`.

---
name: plotly
version: 0.1.0
description: >-
  Build interactive, web-embeddable charts in Python with Plotly — hover
  tooltips, zoom/pan, legend toggling, 40+ chart types (scatter, line, bar,
  box/violin, heatmap, candlestick/OHLC, 3D surface/mesh, choropleth maps,
  sunburst/treemap/sankey), subplots, animations, and standalone HTML export.
  Use when the deliverable is interactive: dashboards, exploratory analysis a
  reader will pan and hover, presentations, or a self-contained HTML figure.
  Reach for Plotly Express (px) for tidy DataFrames and one-liners; drop to
  graph_objects (go) for custom multi-trace figures and chart types px lacks.
  Do NOT use for static print-resolution publication figures needing exact
  vector control (use `matplotlib`, `seaborn`, or `scientific-visualization`),
  for AI-drawn conceptual schematics (use `scientific-schematics`), or to build
  a full web-app backend (that is Dash, not a figure).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: MIT (plotly)
---

# Plotly

## Overview

Plotly is a Python graphing library that renders charts as interactive
JavaScript. Every figure ships with hover tooltips, pan/zoom, box/lasso
selection, and legend toggling for free, and serializes to a self-contained
HTML file or a static image. It exposes two layered APIs over the same figure
object:

- **Plotly Express (`plotly.express`, aliased `px`)** — high-level, one call per
  chart, tuned for tidy pandas DataFrames.
- **Graph Objects (`plotly.graph_objects`, aliased `go`)** — low-level classes
  you assemble by hand for full control.

`px` functions return a `go.Figure`, so you can start high-level and refine with
`go` methods on the same object. That is the normal workflow, not a fallback.

## When to Use This Skill

- You need interactivity: hover-to-inspect, zoom into a region, toggle series
  on/off, or a rangeslider on a time series.
- The output is a dashboard, an exploratory view, a presentation slide, or an
  HTML file a colleague opens in a browser with no Python installed.
- You have many points and want the reader to zoom in rather than pre-cropping.
- You want 3D surfaces/meshes, geographic maps, or hierarchical charts
  (sunburst/treemap/sankey) that stay explorable.

## When NOT to Use This Skill

- **Static, print-resolution publication figures** with exact control over every
  vector element and font metric — use `matplotlib`, `seaborn`, or
  `scientific-visualization`.
- **AI-generated conceptual schematics** (architecture diagrams, pathways) — use
  `scientific-schematics`.
- **A full interactive web application** with callbacks and server state — that
  is Dash (`pip install dash`), which embeds Plotly figures but is a different
  tool; this skill covers the figures, not the app framework.
- **Quick throwaway plots inside a notebook** where interactivity buys nothing —
  `matplotlib` is lighter.

## Install

```bash
uv pip install plotly            # figures + interactive HTML
uv pip install kaleido           # add-on: static PNG/PDF/SVG export
```

`kaleido` v1+ needs a system Chrome/Chromium to render static images. Interactive
HTML export needs nothing beyond `plotly`.

## Choose an API

```python
import plotly.express as px

fig = px.scatter(df, x="temperature", y="yield", color="catalyst",
                 size="mass", trendline="ols", title="Yield vs Temperature")
fig.show()                       # opens in browser / renders in notebook
```

Use **`px`** when the data is a DataFrame and the chart is standard (scatter,
line, bar, histogram, box, violin, choropleth, sunburst, ...). One call gives you
automatic color/size encoding, legends, and faceting.

Use **`go`** when you need a chart type `px` lacks (candlestick, 3D mesh,
isosurface, gauge, table), a custom multi-trace figure, or precise per-element
control:

```python
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(x=x, y=y1, mode="lines+markers", name="observed"))
fig.add_trace(go.Scatter(x=x, y=y2, mode="lines", name="model",
                         line=dict(dash="dash")))
fig.update_layout(template="plotly_white", hovermode="x unified")
```

Combine them — refine a `px` figure with `go` methods:

```python
fig = px.scatter(df, x="x", y="y")
fig.update_layout(title="Custom Title")
fig.add_hline(y=0, line_dash="dash", annotation_text="baseline")
```

Full API contrast and parameter lists: see
[references/plotly-express.md](references/plotly-express.md) and
[references/graph-objects.md](references/graph-objects.md).

## Chart Type Map

Pick a category, then look up the exact call in the catalog.

| Category | Representative charts |
| --- | --- |
| Basic | scatter, line, bar, area, pie/donut, bubble |
| Statistical | histogram, box, violin, strip, ecdf, error bars, 2D density |
| Scientific | heatmap (`imshow`), contour, ternary, log scales, image |
| Financial | candlestick, OHLC, waterfall, funnel, time series + rangeslider |
| Maps | scatter_geo, choropleth, scatter_mapbox, density_mapbox |
| 3D | scatter_3d, line_3d, surface, mesh3d, cone |
| Hierarchical | sunburst, treemap, sankey |
| Specialized | parallel_coordinates, scatter_matrix, indicator/gauge, table |
| Domain | volcano plot, dendrogram, annotated heatmap (`figure_factory`) |

Copy-paste examples for every entry: see
[references/chart-types.md](references/chart-types.md).

## Layout, Subplots, and Styling

Multi-panel figures use `make_subplots`; coordinated styling uses templates.

```python
from plotly.subplots import make_subplots

fig = make_subplots(rows=2, cols=2, subplot_titles=("A", "B", "C", "D"),
                    specs=[[{"type": "scatter"}, {"type": "bar"}],
                           [{"type": "histogram"}, {"type": "box"}]])
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]), row=1, col=1)
fig.update_layout(height=800, template="plotly_white", showlegend=False)
```

Built-in templates: `plotly_white`, `plotly_dark`, `simple_white`, `ggplot2`,
`seaborn`, `presentation`. Perceptually uniform continuous scales: `Viridis`,
`Plasma`, `Cividis`; diverging: `RdBu`, `Spectral`. Subplot specs, custom
templates, colorbars, legends, annotations, and shapes: see
[references/layouts-styling.md](references/layouts-styling.md).

## Export

```python
fig.write_html("chart.html")                       # standalone, ~5 MB embedded
fig.write_html("chart.html", include_plotlyjs="cdn")  # ~2 KB, needs internet
fig.write_image("chart.png", scale=2)              # needs kaleido; also .pdf .svg
```

For HTML, `include_plotlyjs="cdn"` shrinks the file but requires the reader to be
online; the default embeds ~5 MB of plotly.js so the file works offline. Static
export (`write_image`) is the only path that requires `kaleido`. Config flags,
Jinja embedding, hover templates, animations, rangesliders, and dropdown/slider
controls: see [references/export-interactivity.md](references/export-interactivity.md).

## Common Pitfalls

- **`write_image` raises without kaleido** — install it and ensure Chrome is
  present (v1+). Interactive HTML does not need it.
- **`include_plotlyjs="cdn"` figure is blank offline** — the CDN can't load; use
  the default (embedded) for offline reports.
- **Huge scatter feels sluggish** — for >~100k points switch the trace to
  `go.Scattergl` (WebGL) instead of `go.Scatter`.
- **Wide-form vs long-form confusion in `px`** — prefer long/tidy data
  (`color="group"`); pass a list to `y=[...]` only for wide-form.
- **Static-figure expectations** — Plotly's `.png` is fine for a slide, but for
  journal figures the exact-vector control lives in `matplotlib` /
  `scientific-visualization`.

## Reference Files

- [references/plotly-express.md](references/plotly-express.md) — high-level `px`
  API: parameters, trendlines, faceting, animation, hover data.
- [references/graph-objects.md](references/graph-objects.md) — low-level `go`
  API: traces, magic-underscore notation, annotations, shapes, figure tree.
- [references/chart-types.md](references/chart-types.md) — copy-paste catalog of
  40+ chart types across all categories.
- [references/layouts-styling.md](references/layouts-styling.md) — subplots,
  templates, color scales, legends, axes, annotations.
- [references/export-interactivity.md](references/export-interactivity.md) —
  HTML/image export, config, hover, rangesliders, dropdowns, animations.

Upstream docs: <https://plotly.com/python/> ·
API reference: <https://plotly.com/python-api-reference/>

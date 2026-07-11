# Plotly Express (`px`) — High-Level API

`plotly.express` turns a tidy DataFrame into a figure in one call. It picks
sensible defaults for layout, color, and legends, and returns a
`plotly.graph_objects.Figure` you can refine further.

```python
import plotly.express as px
import pandas as pd
```

## The Standard Call Shape

Almost every `px` function follows the same signature: a data frame, the columns
to map onto axes, and optional encodings.

```python
fig = px.scatter(
    data_frame=df,
    x="column_x",
    y="column_y",
    color="category_column",   # auto discrete or continuous color
    size="size_column",        # marker size by value
    symbol="shape_column",     # marker shape by category
    title="Chart Title",
)
fig.show()
```

## Function Catalog

| Group | Functions |
| --- | --- |
| Basic | `scatter`, `line`, `bar`, `area`, `pie` |
| Statistical | `histogram`, `box`, `violin`, `strip`, `ecdf` |
| Density | `density_heatmap`, `density_contour` |
| Maps | `scatter_geo`, `choropleth`, `scatter_mapbox`, `density_mapbox` |
| Hierarchical | `sunburst`, `treemap`, `icicle`, `funnel` |
| Multi-dim | `parallel_coordinates`, `parallel_categories`, `scatter_matrix` |
| 3D | `scatter_3d`, `line_3d` |
| Images | `imshow` |

Exact per-chart examples live in
[chart-types.md](chart-types.md).

## Common Styling Parameters

These are accepted by most `px` functions:

```python
fig = px.scatter(
    df, x="x", y="y",
    width=800, height=600,
    labels={"x": "X Axis", "y": "Y Axis"},         # rename axis titles
    color="category",
    color_discrete_sequence=px.colors.qualitative.Set2,
    color_discrete_map={"A": "red", "B": "blue"},  # pin specific categories
    color_continuous_scale="Viridis",              # numeric color
    category_orders={"category": ["A", "B", "C"]}, # fix legend/axis order
    template="plotly_white",
)
```

## Long-Form vs Wide-Form Data

`px` prefers **long/tidy** data (one row per observation, a category column you
map to `color`). Wide-form works by passing a column list to `y`.

```python
# Long-form (preferred)
fig = px.bar(df_long, x="fruit", y="count", color="contestant")

# Wide-form — each listed column becomes a trace
fig = px.bar(df_wide, x="fruit", y=["A", "B"])
```

## Trendlines

Scatter plots accept statistical trendlines (requires `statsmodels` for `ols`
and `lowess`):

```python
fig = px.scatter(
    df, x="x", y="y",
    trendline="ols",                    # "ols", "lowess", "rolling", "ewm", "expanding"
    trendline_options=dict(log_x=True),
)
```

## Faceting (Small Multiples)

Split into a grid of subplots by category — no `make_subplots` needed:

```python
fig = px.scatter(
    df, x="x", y="y",
    facet_row="category_1",
    facet_col="category_2",
    facet_col_wrap=3,      # wrap after 3 columns
)
```

## Animation

Animate frames over a column, with a play button and slider auto-generated:

```python
fig = px.scatter(
    df, x="gdp", y="life_exp",
    animation_frame="year",
    animation_group="country",   # keeps identity across frames
    size="population", color="continent", hover_name="country",
    range_x=[100, 100000], range_y=[25, 90],   # fix ranges so frames align
)
```

## Hover Customization

```python
fig = px.scatter(
    df, x="x", y="y",
    hover_name="name_column",     # bold title line in the tooltip
    hover_data={
        "extra_col": True,        # add a column
        "x": ":.2f",              # reformat an existing column
        "hidden_col": False,      # remove a default column
    },
)
```

## Refining a `px` Figure

Because `px` returns a `go.Figure`, apply any graph-objects method afterward:

```python
fig = px.scatter(df, x="x", y="y")
fig.update_layout(title="Custom Title", font=dict(size=14))
fig.update_traces(marker=dict(size=10, opacity=0.7))
fig.add_hline(y=0, line_dash="dash")
```

## Session Defaults

```python
px.defaults.template = "plotly_white"
px.defaults.width = 800
px.defaults.height = 600
px.defaults.color_continuous_scale = "Viridis"
```

## Reach for `go` Instead When

- The chart type is not in the catalog above (candlestick, 3D mesh, gauge, sankey).
- You need to hand-assemble many heterogeneous traces.
- You need control `px` parameters do not expose. See
  [graph-objects.md](graph-objects.md).

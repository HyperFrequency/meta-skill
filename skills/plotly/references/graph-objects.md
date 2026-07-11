# Graph Objects (`go`) — Low-Level API

`plotly.graph_objects` exposes Plotly's figure structure as Python classes. You
build a figure by adding trace objects and configuring layout. This is the API
for chart types `px` lacks, custom multi-trace figures, and per-element control.

```python
import plotly.graph_objects as go
```

## Why Drop to `go`

- Validated properties with helpful error messages on typos.
- Attribute *or* dictionary access to any nested property.
- Convenience methods: `.add_trace()`, `.update_layout()`, `.update_traces()`.
- Magic-underscore notation for compact nested writes.
- `go.FigureWidget` for live click/selection callbacks in Jupyter.

## Build a Figure

```python
# Add traces incrementally
fig = go.Figure()
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Line 1"))
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[2, 3, 4], name="Line 2"))

# Or pass all data to the constructor
fig = go.Figure(data=[
    go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Line 1"),
    go.Scatter(x=[1, 2, 3], y=[2, 3, 4], name="Line 2"),
])
```

## Frequently Used Traces

```python
# Scatter / line — mode selects the rendering
go.Scatter(x=x, y=y, mode="lines+markers",   # "lines", "markers", "text"
           line=dict(color="red", width=2, dash="dash"),
           marker=dict(size=10, color="blue", symbol="circle"))

# WebGL scatter — use for >~100k points
go.Scattergl(x=x, y=y, mode="markers")

go.Bar(x=["A", "B", "C"], y=[1, 3, 2], text=[1, 3, 2], textposition="auto")

go.Heatmap(z=z_matrix, x=x_labels, y=y_labels, colorscale="Viridis")

go.Scatter3d(x=x, y=y, z=z, mode="markers", marker=dict(size=5))

go.Candlestick(x=df.date, open=df.open, high=df.high,
               low=df.low, close=df.close)

go.Surface(z=z_matrix, x=x, y=y, colorscale="Viridis")
```

The full trace zoo (Contour, Sankey, Cone, Mesh3d, Indicator, Table, ...) is
enumerated with examples in [chart-types.md](chart-types.md).

## Layout

```python
fig.update_layout(
    title="Figure Title", title_font_size=20,
    xaxis_title="X Axis", yaxis_title="Y Axis",
    width=800, height=600,
    template="plotly_white",
    showlegend=True,
    hovermode="closest",   # "x", "y", "closest", "x unified", False
)
```

### Magic Underscore Notation

Underscores in a keyword flatten nested dicts — these two are equivalent:

```python
fig.update_layout(title=dict(text="Title", font=dict(size=20)))
fig.update_layout(title_text="Title", title_font_size=20)
```

### Axes

```python
fig.update_xaxes(
    title="X Axis", range=[0, 10],
    type="log",             # "linear", "log", "date", "category"
    showgrid=True, gridcolor="lightgray",
    tickformat=".2f", dtick=1, tickangle=-45,
)
fig.update_yaxes(zeroline=True, zerolinewidth=2, zerolinecolor="black")
```

## Update Existing Traces

```python
fig.update_traces(marker=dict(size=10, opacity=0.7))              # all traces
fig.update_traces(marker_color="red", selector=dict(name="Line 1"))  # by match
fig.data[0].marker.size = 15                                      # by index
```

## Annotations and Shapes

```python
fig.add_annotation(x=2, y=5, text="Important Point",
                   showarrow=True, arrowhead=2, ax=40, ay=-40)

fig.add_shape(type="rect", x0=1, y0=2, x1=3, y1=4,
              line=dict(color="red", width=2),
              fillcolor="lightblue", opacity=0.3)

# Convenience wrappers
fig.add_hline(y=5, line_dash="dash", line_color="red")
fig.add_vline(x=3, line_dash="dot", line_color="blue")
fig.add_vrect(x0=1, x1=2, fillcolor="green", opacity=0.2)
```

## The Figure Tree

A figure is `data` (list of traces) plus `layout`. Reach any node by attribute
or dictionary access — both mutate the same object:

```python
fig.layout.title = "New Title"
fig["data"][0]["marker"]["color"] = "red"
```

## Build Traces from a DataFrame

When you want `go` control but have grouped data, loop the groups:

```python
fig = go.Figure()
for group_name, group_df in df.groupby("category"):
    fig.add_trace(go.Scatter(
        x=group_df["x"], y=group_df["y"],
        name=str(group_name), mode="lines+markers",
    ))
```

## Prefer `px` Instead When

The chart is standard and the data is a tidy DataFrame — `px` does the grouping
loop above for you in one line. See [plotly-express.md](plotly-express.md).

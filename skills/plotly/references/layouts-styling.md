# Layout, Subplots, and Styling

How to compose multi-panel figures and control every visual element.

```python
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
```

## Subplots

```python
fig = make_subplots(rows=2, cols=2)
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]), row=1, col=1)
fig.add_trace(go.Bar(x=["A", "B", "C"], y=[1, 3, 2]), row=1, col=2)
```

### Options

```python
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=("Plot 1", "Plot 2", "Plot 3", "Plot 4"),
    column_widths=[0.7, 0.3], row_heights=[0.4, 0.6],
    horizontal_spacing=0.1, vertical_spacing=0.15,
    shared_xaxes=True,        # True | "columns" | "rows" | "all"
    shared_yaxes=False,
    # specs are REQUIRED when a cell holds a non-2D-cartesian trace
    specs=[[{"type": "scatter"}, {"type": "bar"}],
           [{"type": "surface"}, {"type": "table"}]],
)
```

### Mixed 2D / 3D

```python
fig = make_subplots(rows=1, cols=2,
                    specs=[[{"type": "scatter"}, {"type": "scatter3d"}]])
fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4]), row=1, col=1)
fig.add_trace(go.Scatter3d(x=[1, 2], y=[3, 4], z=[5, 6]), row=1, col=2)
```

### Per-Panel Axes

```python
fig.update_xaxes(title_text="X Label", row=1, col=1)      # one panel
fig.update_yaxes(range=[0, 100], row=2, col=1)
fig.update_xaxes(showgrid=True, gridcolor="lightgray")    # all panels
```

### Shared Colorscale Across Panels

```python
fig = make_subplots(rows=1, cols=2)
fig.add_trace(go.Bar(x=["A", "B"], y=[1, 2],
    marker=dict(color=[1, 2], coloraxis="coloraxis")), row=1, col=1)
fig.add_trace(go.Bar(x=["C", "D"], y=[3, 4],
    marker=dict(color=[3, 4], coloraxis="coloraxis")), row=1, col=2)
fig.update_layout(coloraxis=dict(colorscale="Viridis"))   # one shared bar
```

## Templates

Built-in: `plotly` (default), `plotly_white`, `plotly_dark`, `ggplot2`,
`seaborn`, `simple_white`, `presentation`, `xgridoff`, `ygridoff`, `gridon`,
`none`.

```python
fig = px.scatter(df, x="x", y="y", template="plotly_dark")  # in px
fig.update_layout(template="seaborn")                        # in go
pio.templates.default = "plotly_white"                       # session default
```

### Custom Template

```python
pio.templates["custom"] = go.layout.Template(layout=go.Layout(
    font=dict(family="Arial", size=14),
    plot_bgcolor="#f0f0f0", paper_bgcolor="white",
    colorway=["#1f77b4", "#ff7f0e", "#2ca02c"],
    title_font_size=20))
fig = px.scatter(df, x="x", y="y", template="custom")
```

## Color

### Discrete (categorical)

```python
# px.colors.qualitative.{Plotly, D3, G10, Set1, Set2, Pastel, Dark2, ...}
fig = px.scatter(df, x="x", y="y", color="category",
                 color_discrete_sequence=px.colors.qualitative.Set2)
fig = px.scatter(df, x="x", y="y", color="category",
                 color_discrete_map={"A": "red", "B": "blue"})   # pin exact
```

### Continuous (numeric)

```python
# Perceptually uniform: Viridis, Plasma, Inferno, Magma, Cividis
# Sequential:          Blues, Greens, Reds, YlOrRd, YlGnBu
# Diverging:           RdBu, RdYlGn, Spectral, Picnic
fig = px.scatter(df, x="x", y="y", color="value", color_continuous_scale="Viridis")
fig = px.scatter(df, x="x", y="y", color="value", color_continuous_scale="Viridis_r")  # reversed
fig = px.scatter(df, x="x", y="y", color="value",
                 color_continuous_scale=["blue", "white", "red"])   # custom stops
```

### Colorbar

```python
fig.update_coloraxes(colorbar=dict(title="Value", tickmode="linear",
    tick0=0, dtick=10, len=0.7, thickness=20, x=1.02))
```

## Layout Details

```python
fig.update_layout(
    title=dict(text="Main Title",
               font=dict(size=24, family="Arial", color="darkblue"),
               x=0.5, xanchor="center"),
    font=dict(family="Arial", size=14, color="black"),
    width=1000, height=600,
    margin=dict(l=50, r=50, t=100, b=50, pad=10),
    plot_bgcolor="#f0f0f0", paper_bgcolor="white",
)
```

### Legend

```python
fig.update_layout(legend=dict(
    title="Legend Title", orientation="h",       # "h" | "v"
    x=0.5, y=-0.2, xanchor="center", yanchor="top",
    bgcolor="rgba(255,255,255,0.8)", bordercolor="black", borderwidth=1))
```

### Axes

```python
fig.update_xaxes(
    title="X Axis Title", title_font=dict(size=16),
    range=[0, 10], autorange=True,
    showgrid=True, gridwidth=1, gridcolor="lightgray",
    tickmode="linear", tick0=0, dtick=1, tickformat=".2f", tickangle=-45,
    zeroline=True, zerolinewidth=2, zerolinecolor="black",
    type="linear",   # "linear" | "log" | "date" | "category"
)
```

### Annotations and Shapes

```python
fig.add_annotation(text="Important Note", x=2, y=5, showarrow=True,
    arrowhead=2, ax=40, ay=-40, bgcolor="yellow", opacity=0.8)

fig.add_shape(type="rect", x0=1, y0=2, x1=3, y1=4,
    line=dict(color="red", width=2), fillcolor="lightblue", opacity=0.3)
fig.add_shape(type="circle", x0=0, y0=0, x1=1, y1=1, line_color="purple")

fig.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="Threshold")
fig.add_vline(x=3, line_dash="dot")
fig.add_vrect(x0=1, x1=2, fillcolor="green", opacity=0.2)
fig.add_hrect(y0=4, y1=6, fillcolor="red", opacity=0.2)
```

## Responsive Sizing

```python
fig.update_layout(autosize=True)                    # fill the container
fig.write_html("plot.html", config={"responsive": True})
```

# Export and Interactivity

How to get a figure out of Python (image or HTML) and how to tune its
interactive behavior.

```python
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
```

## Static Image Export

Requires Kaleido; v1+ also needs a system Chrome/Chromium.

```bash
uv pip install kaleido
```

Supported: PNG, JPEG, WebP (raster); SVG, PDF (vector).

```python
fig.write_image("chart.png")     # format inferred from extension
fig.write_image("chart.pdf")
fig.write_image("chart.svg")
fig.write_image("chart", format="png")             # explicit

# High-resolution
fig.write_image("chart.png", width=1200, height=800, scale=2)

# As bytes (e.g. to stream or embed)
img_bytes = fig.to_image(format="png")

# Batch (Kaleido v1+)
pio.write_images(fig=[fig1, fig2], file=["a.png", "b.png"])
```

Session defaults:

```python
pio.kaleido.scope.default_format = "png"
pio.kaleido.scope.default_width = 800
pio.kaleido.scope.default_height = 600
pio.kaleido.scope.default_scale = 2
```

## Interactive HTML Export

```python
fig.write_html("chart.html")                 # standalone, plotly.js embedded (~5 MB)
fig.show()                                    # open in browser / render in notebook
```

### Controlling File Size

```python
fig.write_html("chart.html", include_plotlyjs=True)        # embed everything (~5 MB, offline-safe)
fig.write_html("chart.html", include_plotlyjs="cdn")       # ~2 KB, needs internet at view time
fig.write_html("chart.html", include_plotlyjs="directory") # needs plotly.min.js beside the file
fig.write_html("chart.html", include_plotlyjs=False)       # host page already loads plotly.js
```

Pick `True`/embedded for reports that must open offline; pick `"cdn"` only when
the reader is guaranteed online.

### Embedding a Bare Div

```python
html_div = fig.to_html(full_html=False, include_plotlyjs="cdn", div_id="my-plot")
# drop html_div into a Jinja2 / Django template with `| safe`
```

## Interactivity Built In

Every figure supports, with no extra code: hover tooltips, drag-to-pan,
scroll-to-zoom, box/lasso select, click-legend to toggle traces, and
double-click to reset axes.

### Hover

```python
fig.update_layout(hovermode="closest")   # "x", "y", "closest", "x unified", False
fig.update_traces(hovertemplate=(
    "<b>%{x}</b><br>Value: %{y:.2f}<br>Extra: %{customdata[0]}<extra></extra>"))
```

`<extra></extra>` suppresses the secondary trace-name box on the right of the
tooltip.

### Constrain Zoom / Pan

```python
fig.update_xaxes(fixedrange=True)          # disable zoom/pan on this axis
fig.update_xaxes(range=[0, 10], constrain="domain")   # fixed initial window
```

### Rangeslider and Range Selector (time series)

```python
fig = px.line(df, x="date", y="value")
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05, bgcolor="lightgray"))
fig.update_xaxes(rangeselector=dict(buttons=[
    dict(count=1, label="1m", step="month", stepmode="backward"),
    dict(count=6, label="6m", step="month", stepmode="backward"),
    dict(count=1, label="YTD", step="year", stepmode="todate"),
    dict(count=1, label="1y", step="year", stepmode="backward"),
    dict(step="all", label="All"),
]))
```

### Buttons and Dropdowns

```python
fig.update_layout(updatemenus=[dict(type="buttons", direction="left", x=0.1, y=1.15,
    buttons=[
        dict(label="Scatter", method="restyle", args=[{"type": "scatter"}]),
        dict(label="Bar",     method="restyle", args=[{"type": "bar"}]),
    ])])
```

### Sliders

```python
fig.update_layout(sliders=[dict(active=0, x=0.1, y=0, len=0.9, steps=[
    dict(method="update", label="Dataset 1",
         args=[{"visible": [True, False]}, {"title": "Dataset 1"}]),
    dict(method="update", label="Dataset 2",
         args=[{"visible": [False, True]}, {"title": "Dataset 2"}]),
])])
```

## Animations

```python
# Plotly Express — one call
fig = px.scatter(df, x="gdp", y="life_exp",
    animation_frame="year", animation_group="country",
    size="population", color="continent", hover_name="country",
    range_x=[100, 100000], range_y=[25, 90])   # fix ranges so frames align

# Graph objects — explicit frames + play button
fig = go.Figure(
    data=[go.Scatter(x=[1, 2], y=[1, 2])],
    layout=go.Layout(updatemenus=[dict(type="buttons",
        buttons=[dict(label="Play", method="animate", args=[None])])]),
    frames=[go.Frame(data=[go.Scatter(x=[1, 2], y=[2, 3])]),
            go.Frame(data=[go.Scatter(x=[1, 2], y=[3, 4])])])
```

## Click / Selection Callbacks (Jupyter)

```python
fig = go.FigureWidget(data=[go.Scatter(x=[1, 2, 3], y=[4, 5, 6])])

def on_click(trace, points, selector):
    print("clicked:", points.point_inds)

fig.data[0].on_click(on_click)
fig
```

For callback-driven web apps (server state, cross-filtering), use Dash — it
embeds these figures but is a separate framework, out of scope for this skill.

## Save / Load Figures

```python
fig.write_json("figure.json")
fig = pio.read_json("figure.json")
```

## Display Config

Applies to both `fig.show(config=...)` and `fig.write_html(..., config=...)`:

```python
config = {
    "displayModeBar": True,        # True | False | "hover"
    "displaylogo": False,
    "modeBarButtonsToRemove": ["pan2d", "lasso2d"],
    "scrollZoom": True,
    "doubleClick": "reset",        # "reset" | "autosize" | "reset+autosize" | False
    "editable": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "png", "filename": "custom_image",
                             "height": 800, "width": 1200, "scale": 2},
}
fig.show(config=config)
```

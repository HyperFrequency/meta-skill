# Chart Type Catalog

Copy-paste starting points for 40+ chart types, grouped by category. `px` is
`plotly.express`; `go` is `plotly.graph_objects`; `np` is `numpy`.

## Basic

```python
# Scatter (+ optional color/size encoding, + OLS trendline)
fig = px.scatter(df, x="x", y="y", color="category", size="size")
fig = px.scatter(df, x="x", y="y", trendline="ols")

# Line — long-form via color, or wide-form via a y list
fig = px.line(df, x="date", y="value", color="group")
fig = px.line(df, x="date", y=["metric1", "metric2", "metric3"])

# Bar — orientation and barmode
fig = px.bar(df, x="value", y="category", orientation="h")
fig = px.bar(df, x="category", y="value", color="group", barmode="stack")  # or "group"

# Pie / donut
fig = px.pie(df, names="category", values="count", hole=0.4)

# Area
fig = px.area(df, x="date", y="value", color="category")
```

## Statistical

```python
# Histogram, with an optional marginal distribution
fig = px.histogram(df, x="values", nbins=30, marginal="box")  # "violin", "rug"

# 2D histogram / density heatmap
fig = px.density_heatmap(df, x="x", y="y", nbinsx=20, nbinsy=20)

# Box plot — notches, all points
fig = px.box(df, x="category", y="value", color="group", notched=True, points="all")

# Violin, strip, ECDF
fig = px.violin(df, x="category", y="value", box=True, points="all")
fig = px.strip(df, x="category", y="value", color="group")
fig = px.ecdf(df, x="value", color="group")

# Scatter with marginal distributions on the axes
fig = px.scatter(df, x="x", y="y", marginal_x="histogram", marginal_y="box")

# Error bars (px column-driven, or go for full control)
fig = px.scatter(df, x="x", y="y", error_y="error", error_x="x_error")
fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[5, 10, 15],
    error_y=dict(type="data", array=[1, 2, 3], visible=True)))
```

## Scientific

```python
# Heatmap from a matrix
fig = px.imshow(z_matrix, color_continuous_scale="Viridis")
fig = go.Figure(go.Heatmap(z=z_matrix, x=x_labels, y=y_labels, colorscale="RdBu"))

# Contour (filled, labeled)
fig = px.density_contour(df, x="x", y="y")
fig = go.Figure(go.Contour(z=z_matrix,
    contours=dict(coloring="heatmap", showlabels=True)))

# Ternary
fig = px.scatter_ternary(df, a="component_a", b="component_b", c="component_c")

# Log axes; image display
fig = px.scatter(df, x="x", y="y", log_x=True, log_y=True)
fig = px.imshow(img_array)   # numpy / PIL image
```

## Financial

```python
# Candlestick and OHLC
fig = go.Figure(go.Candlestick(x=df.date, open=df.open, high=df.high,
                               low=df.low, close=df.close))
fig = go.Figure(go.Ohlc(x=df.date, open=df.open, high=df.high,
                        low=df.low, close=df.close))

# Waterfall — measure marks each bar relative or total
fig = go.Figure(go.Waterfall(x=categories, y=values,
    measure=["relative", "relative", "total", "relative", "total"]))

# Funnel
fig = px.funnel(df, x="count", y="stage")

# Time series with rangeslider + range-selector buttons
fig = px.line(df, x="date", y="price")
fig.update_xaxes(rangeslider_visible=True,
    rangeselector=dict(buttons=[
        dict(count=1, label="1m", step="month", stepmode="backward"),
        dict(count=6, label="6m", step="month", stepmode="backward"),
        dict(count=1, label="YTD", step="year", stepmode="todate"),
        dict(count=1, label="1y", step="year", stepmode="backward"),
        dict(step="all"),
    ]))
```

## Maps and Geographic

```python
# Geographic-projection scatter
fig = px.scatter_geo(df, lat="lat", lon="lon", color="value", size="size")

# Tile-map scatter / density (open styles need no token)
fig = px.scatter_mapbox(df, lat="lat", lon="lon", color="value", zoom=10,
                        mapbox_style="open-street-map")  # "carto-positron", "carto-darkmatter"
fig = px.density_mapbox(df, lat="lat", lon="lon", z="value", radius=10,
                        zoom=10, mapbox_style="open-street-map")

# Choropleth — ISO country codes or US states
fig = px.choropleth(df, locations="iso_alpha", color="value",
                    hover_name="country", color_continuous_scale="Viridis")
fig = px.choropleth(df, locations="state_code", locationmode="USA-states",
                    color="value", scope="usa")
```

## 3D

```python
fig = px.scatter_3d(df, x="x", y="y", z="z", color="category", size="size")
fig = px.line_3d(df, x="x", y="y", z="z", color="group")

# Surface from a 2D z grid
fig = go.Figure(go.Surface(z=z_matrix, x=x_array, y=y_array))
fig.update_layout(scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z"))

# Triangulated mesh (i/j/k index the vertices)
fig = go.Figure(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k,
                          intensity=intensity, colorscale="Viridis"))

# Vector field
fig = go.Figure(go.Cone(x=x, y=y, z=z, u=u, v=v, w=w,
                        colorscale="Blues", sizemode="absolute", sizeref=0.5))
```

## Hierarchical

```python
# Sunburst / treemap — path is the nesting order, values sizes the wedges
fig = px.sunburst(df, path=["continent", "country", "city"],
                  values="population", color="value")
fig = px.treemap(df, path=["category", "subcategory", "item"],
                 values="count", color="value", color_continuous_scale="RdBu")

# Sankey flow diagram (indices into the node label list)
fig = go.Figure(go.Sankey(
    node=dict(pad=15, thickness=20, label=["A", "B", "C", "D", "E"]),
    link=dict(source=[0, 1, 0, 2, 3], target=[2, 3, 3, 4, 4],
              value=[8, 4, 2, 8, 4])))
```

## Specialized

```python
# Parallel coordinates / categories — multivariate
fig = px.parallel_coordinates(df, dimensions=["d1", "d2", "d3", "d4"],
                              color="target", color_continuous_scale="Viridis")
fig = px.parallel_categories(df, dimensions=["c1", "c2", "c3"], color="value")

# Scatter matrix (SPLOM)
fig = px.scatter_matrix(df, dimensions=["c1", "c2", "c3", "c4"], color="category")

# Gauge / KPI indicator
fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=75,
    delta={"reference": 60},
    gauge={"axis": {"range": [None, 100]},
           "steps": [{"range": [0, 50], "color": "lightgray"},
                     {"range": [50, 100], "color": "gray"}],
           "threshold": {"line": {"color": "red", "width": 4},
                         "thickness": 0.75, "value": 90}}))

# Table
fig = go.Figure(go.Table(header=dict(values=["A", "B", "C"]),
                         cells=dict(values=[col_a, col_b, col_c])))
```

## Domain-Specific (Bio / Omics)

```python
from plotly.figure_factory import create_dendrogram, create_annotated_heatmap

fig = create_dendrogram(data_matrix)
fig = create_annotated_heatmap(z_matrix, x=x_labels, y=y_labels)

# Volcano plot — a scatter with significance guide lines
fig = px.scatter(df, x="log2_fold_change", y="neg_log10_pvalue",
                 color="significant", hover_data=["gene_name"])
fig.add_hline(y=-np.log10(0.05), line_dash="dash")
fig.add_vline(x=-1, line_dash="dash")
fig.add_vline(x=1, line_dash="dash")
```

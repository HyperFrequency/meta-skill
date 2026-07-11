# Mapping and Visualization

Static maps come from matplotlib via `.plot()`; interactive maps come from
folium via `.explore()`. Basemaps (contextily) and cartographic projections
(cartopy) are optional add-ons.

## Basic Plotting

```python
gdf.plot()
gdf.plot(figsize=(10, 10))
gdf.plot(color="blue", edgecolor="black", linewidth=0.5)
```

## Choropleth Maps

Color features by a data column.

```python
gdf.plot(column="population", legend=True)
gdf.plot(column="population", cmap="OrRd", legend=True)
# useful cmaps: viridis, plasma, inferno, YlOrRd, Blues, Greens
```

### Classification schemes

Requires `mapclassify`. Bins continuous values into `k` classes.

```python
gdf.plot(column="pop", scheme="quantiles", k=5, legend=True)
gdf.plot(column="pop", scheme="equal_interval", k=5, legend=True)
gdf.plot(column="pop", scheme="fisher_jenks", k=5, legend=True)  # natural breaks
# also: box_plot, headtail_breaks, max_breaks, std_mean
```

### Legend customization

```python
gdf.plot(column="pop", legend=True,
         legend_kwds={"loc": "upper left", "bbox_to_anchor": (1, 1)})
gdf.plot(column="pop", legend=True,
         legend_kwds={"orientation": "horizontal", "label": "Population"})
```

## Missing Data

```python
gdf.plot(column="pop",
         missing_kwds={"color": "lightgrey", "edgecolor": "red",
                       "hatch": "///", "label": "Missing"})
```

## Multi-Layer Maps

Share one `ax` and control stacking with `zorder`.

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 10))
gdf1.plot(ax=ax, color="lightblue", edgecolor="black", zorder=1)
gdf2.plot(ax=ax, color="red", markersize=5, zorder=2)
gdf3.plot(ax=ax, color="green", alpha=0.5, zorder=3)
plt.show()
```

## Styling

```python
gdf.plot(alpha=0.5)
points.plot(marker="^", markersize=100, color="red")
lines.plot(linestyle="--", linewidth=2)
gdf.plot(column="category", categorical=True, legend=True)  # discrete classes
gdf.plot(markersize=gdf["value"] / 1000)                    # size by column
```

## Map Enhancements

```python
fig, ax = plt.subplots(figsize=(12, 8))
gdf.plot(ax=ax, column="pop", legend=True)
ax.set_title("Population by Region", fontsize=16)
ax.set_axis_off()
plt.tight_layout()
```

## Interactive Maps (`.explore()`)

Requires `folium`. Returns a Leaflet map you can save to HTML.

```python
m = gdf.explore(column="pop", cmap="YlOrRd", legend=True)
m.save("map.html")

gdf.explore(tiles="CartoDB positron")                 # change basemap
gdf.explore(column="pop", tooltip=["name", "pop"])    # hover tooltip
gdf.explore(color="red", style_kwds={"fillOpacity": 0.5, "weight": 2})

# Layer two frames on one map
m = gdf1.explore(color="blue", name="Layer 1")
gdf2.explore(m=m, color="red", name="Layer 2")
import folium
folium.LayerControl().add_to(m)
```

## Basemaps with contextily

Requires `contextily`. Data must be in Web Mercator (`EPSG:3857`) to align with
tile providers.

```python
import contextily as ctx
gdf_wm = gdf.to_crs(epsg=3857)

fig, ax = plt.subplots(figsize=(10, 10))
gdf_wm.plot(ax=ax, alpha=0.5, edgecolor="k")
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
# also: ctx.providers.CartoDB.Positron
```

## Cartographic Projections with cartopy

Requires `cartopy`. Set the axes projection and declare the data's CRS via
`transform`.

```python
import cartopy.crs as ccrs
fig, ax = plt.subplots(subplot_kw={"projection": ccrs.Robinson()},
                       figsize=(15, 10))
gdf.plot(ax=ax, transform=ccrs.PlateCarree(), column="pop", legend=True)
ax.coastlines()
ax.gridlines(draw_labels=True)
```

## Non-Spatial Plots

Standard pandas plot types work on the attribute columns:

```python
gdf["pop"].plot.hist(bins=20)
gdf.plot.scatter(x="income", y="pop")
gdf.boxplot(column="pop", by="region")
```

## Saving Figures

```python
ax = gdf.plot()
fig = ax.get_figure()
fig.savefig("map.png", dpi=300, bbox_inches="tight")
fig.savefig("map.pdf")
fig.savefig("map.svg")
```

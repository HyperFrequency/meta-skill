# Physics plot-type recipes

Complete, copy-paste recipes for each figure type. All assume the publication
`rcParams` and imports from `SKILL.md` are already set (`np`, `plt`). Every
function takes plain arrays so you can drop in your own physics.

---

## 1. Vector field (`quiver`)

```python
def plot_vector_field(ax, X, Y, U, V, normalize=True, cmap="viridis", label=r"$|\mathbf{F}|$"):
    magnitude = np.hypot(U, V)
    if normalize:                       # equal-length arrows: direction only
        U, V = U / (magnitude + 1e-12), V / (magnitude + 1e-12)
    q = ax.quiver(X, Y, U, V, magnitude, cmap=cmap, alpha=0.85, pivot="mid")
    plt.colorbar(q, ax=ax, label=label)
    ax.set_aspect("equal")
    return q
```

- **Grid density**: `quiver` needs a *coarse* grid (15–25 points/axis). A fine
  grid produces an unreadable arrow mat — downsample with `X[::k, ::k]`.
- `normalize=True` decouples arrow length from magnitude and lets color carry the
  strength; use `normalize=False` only when true relative lengths matter and the
  dynamic range is small.
- `scale=`/`scale_units=` control arrow length; smaller `scale` → longer arrows.

## 2. Streamlines (`streamplot`)

Field lines, colored by (log) magnitude. Use a **fine, regular** grid — unlike
`quiver`, `streamplot` requires evenly spaced 1D `x`, `y`.

```python
xf = yf = np.linspace(-3, 3, 200)
Xf, Yf = np.meshgrid(xf, yf)
Uf, Vf = your_field(Xf, Yf)
mag = np.hypot(Uf, Vf)
strm = ax.streamplot(Xf, Yf, Uf, Vf, color=np.log10(mag + 1e-3),
                     cmap="inferno", density=2, linewidth=1, arrowsize=1.5)
plt.colorbar(strm.lines, ax=ax, label=r"$\log_{10}|\mathbf{E}|$")
```

- `density` controls line spacing (scalar or `(nx, ny)` tuple).
- Mark singularities (charges, vortices) explicitly: `ax.plot(xs, ys, "ro")`.
- Streamplot silently skips regions where the field is NaN/inf — clean your array.

## 3. Contour / potential map (`contourf` + `contour`)

Filled color plus labeled iso-lines — the standard for potentials, temperature,
`|ψ|²`. Use a **diverging** colormap with symmetric limits for signed fields.

```python
def plot_contour(ax, X, Y, Z, levels=20, cmap="RdBu_r", symmetric=True, label=""):
    if symmetric:                       # center diverging colormap on 0
        vmax = np.nanmax(np.abs(Z)); vmin = -vmax
    else:
        vmin, vmax = np.nanmin(Z), np.nanmax(Z)
    cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap, vmin=vmin, vmax=vmax)
    cs = ax.contour(X, Y, Z, levels=levels, colors="k", linewidths=0.3, alpha=0.5)
    ax.clabel(cs, inline=True, fontsize=8, fmt="%.1f")
    plt.colorbar(cf, ax=ax, label=label)
    ax.set_aspect("equal")
    return cf
```

For a signed field (potential, charge density) keep `symmetric=True` so zero maps
to the neutral center color. For a strictly positive density (`|ψ|²`) use
`symmetric=False` with a sequential map (`hot`, `viridis`).

## 4. Heatmap (`pcolormesh` / `imshow`)

When you want raw pixels, not iso-lines. `pcolormesh` respects non-uniform grids;
`imshow` is faster for a regular grid but needs `extent` and `origin="lower"`.

```python
pm = ax.pcolormesh(X, Y, Z, cmap="viridis", shading="gouraud")
plt.colorbar(pm, ax=ax, label=r"$T$ [K]")
# imshow equivalent for a regular grid:
# im = ax.imshow(Z, extent=[x0, x1, y0, y1], origin="lower", aspect="auto", cmap="viridis")
```

## 5. 3D surface (`plot_surface`)

Energy/potential landscapes. Keep 3D for *shape intuition*; prefer a 2D contour
when readers must extract quantitative values.

```python
fig = plt.figure(figsize=(9, 7))
ax = fig.add_subplot(111, projection="3d")
x = y = np.linspace(-2, 2, 120)
X, Y = np.meshgrid(x, y)
Z = (X**2 - 1)**2 + Y**2                          # double-well potential
surf = ax.plot_surface(X, Y, Z, cmap="coolwarm", linewidth=0, antialiased=True)
ax.set_xlabel(r"$x$"); ax.set_ylabel(r"$y$"); ax.set_zlabel(r"$V(x,y)$")
fig.colorbar(surf, ax=ax, shrink=0.6, label=r"$V$")
ax.view_init(elev=30, azim=-60)                   # tune viewing angle
```

- `rstride`/`cstride` (or `rcount`/`ccount`) downsample large grids for speed.
- `ax.contour3D` / `ax.plot_wireframe` are alternatives for cleaner line-art.

## 6. Phase space and Poincaré sections

You integrate the trajectory elsewhere (e.g. `scipy.integrate.solve_ivp` or the
`dynamical-systems` skill); here you just render it.

```python
# Phase portrait: state vs its derivative (or two state components)
ax.plot(q, p, lw=0.8)                 # e.g. position vs momentum
ax.set_xlabel(r"$q$"); ax.set_ylabel(r"$p$"); ax.set_aspect("equal")
```

A **Poincaré section** is a scatter of the points where a trajectory crosses a
chosen surface (e.g. `p = 0` with `p` increasing). Detect crossings by sign
change and linearly interpolate the crossing point:

```python
def poincare_section(t, x, y, section, rising=True):
    """Return (x, y) at zero-crossings of `section` (a 1D array, same length)."""
    s = section
    sign_change = (s[:-1] < 0) & (s[1:] >= 0) if rising else (s[:-1] > 0) & (s[1:] <= 0)
    idx = np.nonzero(sign_change)[0]
    frac = -s[idx] / (s[idx + 1] - s[idx])        # linear interp weight in [0,1)
    xc = x[idx] + frac * (x[idx + 1] - x[idx])
    yc = y[idx] + frac * (y[idx + 1] - y[idx])
    return xc, yc

xc, yc = poincare_section(t, x, y, section=vy)     # crossings of vy = 0
ax.scatter(xc, yc, s=4)
```

If your section variable is available directly from a `solve_ivp` run, the cleaner
route is its `events=` callback — see the `dynamical-systems` skill.

## 7. Spectrogram (time–frequency map)

Intensity of a signal's frequency content over time. Use SciPy for the STFT, then
render in dB.

```python
from scipy.signal import spectrogram
f, t, Sxx = spectrogram(signal, fs=sample_rate, nperseg=256, noverlap=192)
pm = ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-12), shading="gouraud", cmap="magma")
ax.set_xlabel(r"$t$ [s]"); ax.set_ylabel(r"$f$ [Hz]")
plt.colorbar(pm, ax=ax, label="Power [dB]")
```

- Trade time vs frequency resolution with `nperseg` (larger → finer frequency,
  coarser time). `noverlap` smooths the time axis.
- Matplotlib's one-call `ax.specgram(signal, NFFT=256, Fs=sample_rate)` is a
  convenient alternative but gives you less control over normalization.
- Log-scale the frequency axis (`ax.set_yscale("log")`) for wide-band signals.

## 8. Multi-panel figure with automatic panel labels

```python
def multi_panel(n_rows, n_cols, figsize=None, sharex=False, sharey=False):
    figsize = figsize or (5 * n_cols, 4 * n_rows)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize,
                             sharex=sharex, sharey=sharey)
    for i, ax in enumerate(np.atleast_1d(axes).flat):
        ax.text(-0.12, 1.05, f"({chr(ord('a') + i)})", transform=ax.transAxes,
                fontsize=14, fontweight="bold", va="top")
    return fig, axes
```

- Use `sharex`/`sharey=True` for a grid comparing the same quantity — it removes
  redundant tick labels and aligns axes.
- Reserve room for the colorbar with `fig.colorbar(mappable, ax=axes.ravel().tolist())`
  or `constrained_layout=True` (pass to `plt.subplots`) to avoid overlap.
- `fig.tight_layout()` (or `constrained_layout`) after plotting prevents clipped
  labels; do not combine `tight_layout` with `constrained_layout`.

---

## Common failure modes

| Symptom | Cause / fix |
|---|---|
| Unreadable arrow mat | `quiver` grid too fine — downsample to ~20/axis |
| `streamplot` errors on grid | needs evenly spaced 1D `x`,`y`; regenerate with `linspace` |
| Blank / white contour | NaN/inf in `Z`, or all-equal values — clean array, check `levels` |
| Diverging map off-center | forgot symmetric `vmin=-vmax` around 0 |
| 3D surface renders slowly | huge grid — set `rcount`/`ccount` or downsample |
| Colorbar overlaps panels | use `constrained_layout=True` or pass `ax=` list to `colorbar` |
| Wavefunction phase lost | plotting `|ψ|²` discards phase — use a cyclic colormap on `angle(ψ)` |

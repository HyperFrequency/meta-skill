# Animating a time-evolving system

For waves, orbits, diffusion, and any field or trajectory that changes with time.
The pattern: build the figure and artists **once**, then update only the data in a
per-frame callback. Assumes `np`, `plt` and the publication `rcParams` from
`SKILL.md`.

## The core pattern (line update, blitting)

```python
from matplotlib.animation import FuncAnimation, PillowWriter

fig, ax = plt.subplots(figsize=(10, 4))
x = np.linspace(0, 10, 500)
line, = ax.plot(x, np.sin(x), lw=2)          # create the artist once
ax.set_ylim(-1.5, 1.5)
ax.set_xlabel(r"$x$"); ax.set_ylabel(r"$u(x,t)$")
time_text = ax.text(0.02, 0.95, "", transform=ax.transAxes)

def update(frame):
    t = frame * 0.05
    line.set_ydata(np.sin(2 * np.pi * (x - t)) * np.exp(-0.1 * t))
    time_text.set_text(f"$t = {t:.2f}$")
    return line, time_text                    # blit needs the changed artists

anim = FuncAnimation(fig, update, frames=200, interval=33, blit=True)
anim.save("wave.gif", writer=PillowWriter(fps=30))
```

Key rules:

- **Create artists outside `update`.** Inside, mutate them (`set_ydata`,
  `set_data`, `set_offsets`, `set_array`) — never call `ax.plot`/`ax.clear` per
  frame (leaks memory, kills blitting).
- With `blit=True`, `update` **must return an iterable of the changed artists**.
  Blitting only redraws those, giving smooth playback; disable it (`blit=False`)
  if axis limits or text-outside-axes change each frame.
- `interval` is milliseconds between frames on-screen; the saved file's speed is
  set by the writer's `fps`, so keep them consistent (`fps = 1000/interval`).
- Keep a reference to `anim` alive until `save()`/`show()` returns — if it is
  garbage-collected the animation silently stops.

## Updating a heatmap / field each frame

```python
im = ax.pcolormesh(X, Y, Z0, cmap="viridis", shading="gouraud")

def update(frame):
    Z = field_at(frame)
    im.set_array(Z.ravel())        # pcolormesh wants a flattened array
    return (im,)
```

For `imshow`, use `im.set_data(Z)` (2D). Fix the color scale across frames with
`vmin`/`vmax` at creation, or the colormap will rescale every frame and flicker.

## Writers and formats

| Output | Writer | Needs |
|---|---|---|
| GIF (portable, lossy, large) | `PillowWriter(fps=...)` | Pillow (bundled) |
| MP4 / H.264 (small, high quality) | `FFMpegWriter(fps=..., bitrate=...)` | `ffmpeg` on PATH |
| WebM | `FFMpegWriter(codec="libvpx-vp9")` | `ffmpeg` |

```python
from matplotlib.animation import FFMpegWriter
anim.save("wave.mp4", writer=FFMpegWriter(fps=30, bitrate=4000))
```

Check ffmpeg is available before relying on MP4:
`matplotlib.animation.FFMpegWriter.isAvailable()` returns `False` if the binary is
missing — fall back to `PillowWriter` and a GIF.

## Performance and failure modes

| Symptom | Cause / fix |
|---|---|
| Animation is choppy | enable `blit=True` and return only changed artists |
| Memory grows every frame | you are re-plotting; mutate artists instead of `ax.plot`/`clear` |
| Saved GIF far too large | reduce `frames`, `figure.dpi`, or use MP4 |
| `MovieWriter ffmpeg unavailable` | install ffmpeg or use `PillowWriter` GIF |
| Colors flicker across frames | set fixed `vmin`/`vmax` at artist creation |
| Blank saved file | you let `anim` be garbage-collected before `save()` |
| Frames render but nothing moves | forgot to actually mutate the artist inside `update` |

For very long or high-resolution runs, render frames to disk as numbered PNGs and
assemble with ffmpeg directly — it is more memory-stable than holding a long
`FuncAnimation` in RAM.

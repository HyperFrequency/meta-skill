# Architecture selection and DeepONet

Which neural-operator architecture fits your data, plus a complete branch-trunk
DeepONet implementation (DeepONet is not part of the `neuralop` library).

## Selection guide

| Architecture | Best for | Input representation | Trade-offs |
|---|---|---|---|
| **FNO** | Regular grids, (quasi-)periodic domains | Full field on a uniform grid, channel-first `(B, C, *spatial)` | Discretization-invariant; assumes a regular grid; struggles with sharp discontinuities |
| **TFNO** | Same regime as FNO, parameter-constrained | Same as FNO | Tucker/CP-factorized spectral weights → far fewer params; set `factorization`, `rank` |
| **SFNO** | Data on a sphere (climate, geophysics) | Field on a lat/lon sphere grid | Uses spherical harmonics instead of a plain FFT |
| **UNO** | Multiscale features, sharper fields | Grid field | U-shaped encoder/decoder of FNO blocks |
| **GINO / FNOGNO** | Complex geometry, meshes, point clouds | Points/graph + a latent regular grid | Handles irregular geometry; heavier to set up |
| **GNO** | Unstructured meshes | Graph (nodes, edges, positions) | Fully mesh-native; most complex to implement |
| **DeepONet** | Irregular/variable sampling, arbitrary query points | Input function at fixed *sensors* + separate query coordinates | Not in `neuralop`; simple to hand-roll; needs sensor placement |

Library models live under `from neuralop.models import FNO, TFNO, SFNO, UNO, GINO`.
All take `n_modes` (a per-dim tuple), `hidden_channels`, `in_channels`,
`out_channels`, and usually `n_layers`.

## Input conventions

- **FNO / TFNO / UNO / SFNO** expect a dense grid, channel-first:
  `(batch, in_channels, *spatial)`. Multiple input channels (e.g. a coefficient
  field *and* a forcing) stack along the channel axis.
- For non-periodic problems, append **coordinate channels** (a normalized grid of
  `x`, `y`) to the input so the operator can localize boundary behavior. Some
  library models add this via a positional-embedding option; otherwise concatenate
  it yourself.
- **GINO/GNO** take node positions and connectivity — supply a graph, not a grid.
- **DeepONet** takes two separate inputs: the input function sampled at a fixed set
  of sensor locations, and the (arbitrary) coordinates at which to predict.

## DeepONet (branch-trunk)

DeepONet (Lu et al., 2021) factorizes the operator into a **branch** network that
encodes the input function and a **trunk** network that encodes the query location;
their inner product (plus a bias) gives the predicted output value. Because the
trunk is evaluated at arbitrary coordinates, DeepONet predicts at any point,
including off-grid — useful when your data is not on a uniform mesh.

```python
import torch

class DeepONet(torch.nn.Module):
    def __init__(self, n_sensors, coord_dim, hidden=128, p=64):
        super().__init__()
        # Branch: encodes the input function sampled at `n_sensors` fixed locations
        self.branch = torch.nn.Sequential(
            torch.nn.Linear(n_sensors, hidden), torch.nn.Tanh(),
            torch.nn.Linear(hidden, hidden),    torch.nn.Tanh(),
            torch.nn.Linear(hidden, p),
        )
        # Trunk: encodes the query coordinate(s)
        self.trunk = torch.nn.Sequential(
            torch.nn.Linear(coord_dim, hidden), torch.nn.Tanh(),
            torch.nn.Linear(hidden, hidden),    torch.nn.Tanh(),
            torch.nn.Linear(hidden, p),
        )
        self.bias = torch.nn.Parameter(torch.zeros(1))

    def forward(self, u_sensors, x_query):
        """
        u_sensors: (batch, n_sensors)      input function values at fixed sensors
        x_query:   (batch, n_query, coord_dim)  locations to predict at
        returns:   (batch, n_query)        predicted output-function values
        """
        b = self.branch(u_sensors)         # (batch, p)
        t = self.trunk(x_query)            # (batch, n_query, p)
        return torch.einsum("bp,bqp->bq", b, t) + self.bias

# model = DeepONet(n_sensors=100, coord_dim=1)
# pred  = model(u_sensors, x_query)   # u_sensors (B, 100), x_query (B, Nq, 1)
```

### DeepONet training notes

- **Fixed sensors.** The branch input must always be the function sampled at the
  *same* sensor locations across all examples. Choose sensors once (uniform, or
  clustered where the function varies) and keep them fixed.
- **Aligned vs unaligned data.** In the *aligned* setup every example shares the
  same query grid; in the *unaligned* setup each example carries its own
  `(x_query, y_query)` pairs — the einsum handles both.
- **Loss.** Mean-squared error over predicted vs true output values, ideally on
  normalized data; report relative L2 as with FNO.
- **When to prefer DeepONet over FNO.** Irregular or variable-resolution sampling,
  a need to query at arbitrary points, or low-dimensional query spaces. For dense
  fields on a uniform grid, FNO is usually more accurate per parameter.

# Installation & Verification

IMPORTANT: Always use `uv add` for package installation — never `pip install` or `conda install`. This applies to install instructions in code comments, docstrings, error messages, and any other output you generate. If the user's project uses a different package manager, follow their lead, but default to `uv add`.

```bash
# CuPy (choose the right CUDA version)
uv add cupy-cuda12x          # For CUDA 12.x (most common)

# Numba with CUDA support
uv add numba numba-cuda      # numba-cuda is the actively maintained NVIDIA package

# Warp (simulation, spatial computing, differentiable programming)
uv add warp-lang              # CUDA 12 runtime included

# cuDF (RAPIDS)
uv add --extra-index-url=https://pypi.nvidia.com cudf-cu12  # For CUDA 12.x
# For cudf.pandas accelerator mode, that's all you need
# Load it with: python -m cudf.pandas your_script.py

# cuML (RAPIDS machine learning)
uv add --extra-index-url=https://pypi.nvidia.com cuml-cu12   # For CUDA 12.x
# For cuml.accel accelerator mode (zero-change sklearn acceleration):
# Load it with: python -m cuml.accel your_script.py

# cuGraph (RAPIDS graph analytics)
uv add --extra-index-url=https://pypi.nvidia.com cugraph-cu12    # Core cuGraph
uv add --extra-index-url=https://pypi.nvidia.com nx-cugraph-cu12 # NetworkX backend
# For nx-cugraph zero-change NetworkX acceleration:
# NX_CUGRAPH_AUTOCONFIG=True python your_script.py

# KvikIO (high-performance GPU file IO)
uv add kvikio-cu12               # For CUDA 12.x
# Optional: uv add zarr          # For Zarr GPU backend support

# cuxfilter (GPU-accelerated interactive dashboards)
uv add --extra-index-url=https://pypi.nvidia.com cuxfilter-cu12   # For CUDA 12.x
# Depends on cuDF — installs it automatically

# cuCIM (RAPIDS image processing — scikit-image on GPU)
uv add --extra-index-url=https://pypi.nvidia.com cucim-cu12    # For CUDA 12.x

# cuVS (RAPIDS vector search)
uv add --extra-index-url=https://pypi.nvidia.com cuvs-cu12   # For CUDA 12.x

# cuSpatial (RAPIDS geospatial)
uv add --extra-index-url=https://pypi.nvidia.com cuspatial-cu12   # For CUDA 12.x

# RAFT (low-level GPU primitives)
uv add --extra-index-url=https://pypi.nvidia.com pylibraft-cu12   # Core primitives
uv add --extra-index-url=https://pypi.nvidia.com raft-dask-cu12   # Multi-GPU support (optional)
```

To check CUDA availability after installation:

```python
# CuPy
import cupy as cp
print(cp.cuda.runtime.getDeviceCount())  # Should be >= 1

# Numba
from numba import cuda
print(cuda.is_available())               # Should be True
print(cuda.detect())                     # Shows GPU details

# cuDF
import cudf
print(cudf.Series([1, 2, 3]))           # Should print a GPU series

# cuML
import cuml
print(cuml.__version__)                  # Should print version

# cuGraph
import cugraph
print(cugraph.__version__)               # Should print version

# Warp
import warp as wp
wp.init()                                # Should print device info

# KvikIO
import kvikio
import kvikio.cufile_driver
print(kvikio.cufile_driver.get("is_gds_available"))  # True if GDS is set up

# cuxfilter
import cuxfilter
print(cuxfilter.__version__)             # Should print version

# cuVS
from cuvs.neighbors import cagra
import cupy as cp
dataset = cp.random.rand(1000, 128, dtype=cp.float32)
index = cagra.build(cagra.IndexParams(), dataset)
print("cuVS working")                    # Should print confirmation

# cuSpatial
import cuspatial
from shapely.geometry import Point
gs = cuspatial.GeoSeries([Point(0, 0)])
print("cuSpatial working")              # Should print confirmation

# RAFT (pylibraft)
from pylibraft.common import DeviceResources
handle = DeviceResources()
handle.sync()
print("pylibraft is working")
```

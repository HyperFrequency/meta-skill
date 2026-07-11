# Setup, Backends, and Execution

Installation, authentication, backend selection, simulators, third-party
providers, job management, execution modes, and error mitigation.

## Installation

```bash
uv pip install qiskit qiskit-ibm-runtime
uv pip install "qiskit[visualization]" matplotlib   # circuit/state plotting
uv pip install qiskit-aer                            # high-performance local simulator
```

Verify:

```python
import qiskit
print(qiskit.__version__)
```

Qiskit tracks a fast release cadence and the core SDK is versioned independently
from the ecosystem packages (`qiskit-ibm-runtime`, `qiskit-aer`,
`qiskit-nature`, `qiskit-machine-learning`, `qiskit-optimization`). Pin versions
in production; ecosystem packages frequently lag the core SDK by a release.

## IBM Quantum authentication

Running on real hardware requires an IBM Quantum Platform account and API key.
Create one at the IBM Quantum Platform, copy the API key and your instance
identifier (a CRN), then save credentials once per machine:

```python
from qiskit_ibm_runtime import QiskitRuntimeService

QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",   # current channel; legacy "ibm_quantum" retired in 2025
    token="<API_KEY>",
    instance="<CRN-or-instance>",
    overwrite=True,
)

service = QiskitRuntimeService()      # later sessions load the saved account
```

You can also skip `save_account` and construct the service with `channel`,
`token`, and `instance` passed directly, or via the `QISKIT_IBM_TOKEN` /
`QISKIT_IBM_INSTANCE` environment variables.

## Selecting a backend

```python
# List backends
for b in service.backends():
    print(b.name, b.num_qubits)

# Filter and fetch
backend = service.backend("ibm_brisbane")
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=5)
```

### Backend properties

```python
backend.name
backend.num_qubits
backend.coupling_map           # physical qubit connectivity (a CouplingMap)
backend.target                 # gate durations, error rates, native gates
backend.target.operation_names # native/basis gates
backend.status()               # .operational, .pending_jobs, .status_msg
```

Prefer `backend.target` over the older `backend.configuration()` /
`backend.properties()` accessors — `Target` is the unified source of truth the
transpiler consumes.

## Local simulators

### StatevectorSampler / StatevectorEstimator (reference primitives, ideal)

Ship with `qiskit.primitives`, need no account, no noise. Best for development.
See `references/primitives.md`.

### Aer (high-performance, optional noise)

```python
from qiskit_aer import AerSimulator

sim = AerSimulator()                        # ideal, multiple methods
noisy = AerSimulator.from_backend(backend)  # mimic a real device's noise model
gpu = AerSimulator(method="statevector", device="GPU")  # if built with GPU support
```

Aer methods include `statevector`, `density_matrix`, `stabilizer`,
`matrix_product_state`, and `extended_stabilizer`; pick per circuit size and
structure (MPS scales to more qubits for low-entanglement circuits).

Test on `AerSimulator.from_backend(backend)` before spending hardware time — it
applies the device's real noise so you see whether results survive noise.

## Running on hardware with Runtime primitives

```python
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler

qc = QuantumCircuit(2)
qc.h(0); qc.cx(0, 1); qc.measure_all()

pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
isa = pm.run(qc)

sampler = Sampler(mode=backend)          # V2 primitives take mode=<backend|session|batch>
job = sampler.run([isa], shots=1024)
result = job.result()
counts = result[0].data.meas.get_counts()
```

`mode=` replaced the older `session=` / positional-`backend` arguments.

## Job management

```python
job_id = job.job_id()          # save this to retrieve later
job.status()                   # 'QUEUED' | 'RUNNING' | 'DONE' | 'ERROR' | 'CANCELLED'
job.cancel()

# retrieve in a later process
later = service.job(job_id)
result = later.result()
```

## Execution modes

- **Single job** — `Sampler(mode=backend)`: one-off experiments.
- **Session** — hold a backend across many dependent jobs; ideal for iterative
  variational loops (VQE/QAOA) so you do not re-queue every iteration.
- **Batch** — submit many *independent* circuits to run efficiently in parallel.

```python
from qiskit_ibm_runtime import Session, Batch, SamplerV2 as Sampler

with Session(backend=backend) as session:
    sampler = Sampler(mode=session)
    for params in schedule:
        job = sampler.run([bind(isa, params)], shots=1024)
        analyze(job.result())

with Batch(backend=backend) as batch:
    sampler = Sampler(mode=batch)
    jobs = [sampler.run([c], shots=1024) for c in isa_circuits]
    results = [j.result() for j in jobs]
```

## Error mitigation (resilience)

Runtime primitives apply mitigation via options on the primitive instance. Exact
option sub-paths are version-specific — check the installed `qiskit-ibm-runtime`
docs — but the shape is:

```python
from qiskit_ibm_runtime import EstimatorV2 as Estimator

estimator = Estimator(mode=backend)
estimator.options.default_shots = 4096
estimator.options.resilience_level = 1     # 0 none, 1 readout, 2 + gate/ZNE, 3 heaviest
# advanced techniques (names vary by version):
# estimator.options.resilience.zne_mitigation = True    # zero-noise extrapolation
# estimator.options.resilience.pec_mitigation = True    # probabilistic error cancellation
```

Resilience raises cost and runtime — heavier mitigation multiplies sampling
overhead. Start low, increase only for final results.

## Third-party providers

Qiskit is backend-agnostic; other hardware plugs in via provider packages. Exact
class names and auth belong to each plugin's docs.

- **IonQ** (`qiskit-ionq`) — trapped-ion, all-to-all connectivity; native gates
  differ (GPI/GPI2/MS), so transpile with the provider's target/basis.
- **Amazon Braket** (`qiskit-braket-provider`) — routes to Rigetti, IonQ, and
  others; transpilation depends on the selected device.

## Troubleshooting

- **"Backend not found"** — `print([b.name for b in service.backends()])`; names
  change as devices are retired.
- **Invalid credentials** — re-run `save_account(..., overwrite=True)`; confirm
  you used the `ibm_quantum_platform` channel and the correct instance/CRN.
- **Long queues** — use `least_busy(...)` or Batch mode; validate on Aer first.
- **"Circuit too large" / rejected** — the circuit was not transpiled to ISA, or
  exceeds the device; transpile at `optimization_level=3` and shrink the circuit.

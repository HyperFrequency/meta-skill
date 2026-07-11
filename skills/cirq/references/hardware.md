# Hardware Integration

Running circuits on real quantum processors: device models, qubit selection from
calibration, provider setup, job management, and hardware-aware optimization.

Golden rule: validate on a simulator first, compile to the device gateset and
connectivity, select good qubits from calibration, then submit. Coherence times
are short, so keep circuits shallow.

## Devices and Validation

A device exposes its qubits, connectivity, and gateset via `metadata`.

```python
import cirq, cirq_google
device = cirq_google.Sycamore

qubits = device.metadata.qubit_set
graph = device.metadata.nx_graph          # networkx graph of allowed 2-qubit edges
list(graph.neighbors(sorted(qubits)[0]))  # qubits coupled to a given qubit

try:
    device.validate_circuit(circuit)
except ValueError as err:
    print("invalid for device:", err)     # bad gateset, disconnected pair, etc.
```

Validation failures almost always mean the circuit uses a non-native gate or a
two-qubit gate on unconnected qubits — fix with the transformers in
[transformation.md](transformation.md).

## Qubit Selection from Calibration

Prefer qubits with the best measured fidelity, and keep them connected.

```python
processor = cirq_google.get_engine().get_processor("weber")
calibration = processor.get_current_calibration()

def best_single_qubit_fidelity(calibration, n):
    scores = {}
    for metric in calibration["single_qubit_rb_average_error_per_gate"]:
        (qubit,) = metric.qubits
        scores[qubit] = 1 - calibration["single_qubit_rb_average_error_per_gate"][metric][0]
    return [q for q, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:n]]
```

Calibration objects are keyed by metric name; index into the metric you care
about (`two_qubit_...` metrics are keyed by qubit pairs). For a connected block,
search the device graph (e.g. `networkx.ego_graph`) for a subgraph of the needed
size. Exact metric keys vary by processor snapshot — inspect
`calibration.keys()`.

## Providers

### Google Quantum AI (`cirq-google`)

```python
# auth: gcloud auth application-default login; export GOOGLE_CLOUD_PROJECT=<id>
engine = cirq_google.get_engine()
for p in engine.list_processors():
    print(p.processor_id)

processor = engine.get_processor("weber")
device = processor.get_device()
qubits = sorted(device.metadata.qubit_set)[:5]
circuit = cirq.Circuit(cirq.H(qubits[0]), cirq.CZ(qubits[0], qubits[1]),
                       cirq.measure(*qubits, key="result"))
device.validate_circuit(circuit)
job = processor.run(circuit, repetitions=1000)
print(job.histogram(key="result"))
```

### IonQ (`cirq-ionq`)

```python
import cirq_ionq
service = cirq_ionq.Service(api_key="...")     # or export IONQ_API_KEY
result = service.run(circuit=circuit, repetitions=1000, target="simulator")  # or "qpu"

# async job handling
job = service.create_job(circuit, repetitions=1000, target="qpu")
job.status(); results = job.results()
```

IonQ uses generic `LineQubit`s (all-to-all connectivity in the abstract model).

### Azure Quantum (`azure-quantum`)

```python
from azure.quantum import Workspace
from azure.quantum.cirq import AzureQuantumService
service = AzureQuantumService(Workspace(resource_id="...", location="eastus"))
for t in service.targets():
    print(t.name)                              # e.g. ionq.qpu, quantinuum.qpu.h1-1
result = service.run(circuit=circuit, repetitions=1000, target="ionq.qpu")
```

### AQT (`cirq-aqt`)

```python
import cirq_aqt
sampler = cirq_aqt.AQTSampler(remote_host="https://gateway.aqt.eu", access_token="...")
result = sampler.run(circuit, repetitions=1000)
```

### Pasqal (`cirq-pasqal`)

```python
import cirq_pasqal
device = cirq_pasqal.PasqalDevice(qubits=cirq.LineQubit.range(10))
sampler = cirq_pasqal.PasqalSampler(remote_host="https://api.pasqal.cloud",
                                    access_token="...", device=device)
result = sampler.run(circuit, repetitions=1000)
```

## Credentials

| Provider | How |
| --- | --- |
| Google | `gcloud auth application-default login`; `GOOGLE_CLOUD_PROJECT` |
| IonQ | `IONQ_API_KEY` env var, or `Service(api_key=...)` |
| Azure | Workspace `resource_id` + `location` (Azure CLI login) |
| AQT | `AQT_TOKEN` / `access_token` |
| Pasqal | `PASQAL_TOKEN` / `access_token` |

Do not hardcode secrets — read tokens from environment variables.

## Hardware-Aware Optimization

```python
def compile_for_device(circuit, gateset):
    circuit = cirq.merge_single_qubit_gates_to_phxz(circuit)
    circuit = cirq.drop_negligible_operations(circuit)
    return cirq.optimize_for_target_gateset(circuit, gateset=gateset)

compiled = compile_for_device(circuit, cirq_google.SycamoreTargetGateset())
device.validate_circuit(compiled)
```

## Batching and Job Management

- Submit many circuits together where the provider supports batch/sweep runs;
  it amortizes queue latency.
- Poll `job.status()` before fetching results; hardware jobs are queued and can
  take minutes to hours.
- Persist results immediately — hardware time is expensive and non-reproducible.

## Readout Error Mitigation

Characterize the measurement confusion matrix by preparing each basis state and
measuring, then invert it against your raw counts. See
[noise.md](noise.md#readout-error-mitigation) for the full procedure.

## Tips

- Always `validate_circuit` before submitting.
- Compile to native gates and route to connectivity before validation.
- Select qubits from fresh calibration; fidelity drifts between snapshots.
- Keep circuits shallow; two-qubit gates and depth drive most hardware error.

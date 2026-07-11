# Quantum Machine Learning

Building hybrid quantum-classical models: choosing an interface, embedding a QNode as a layer in
PyTorch/Keras, and constructing variational classifiers and encodings.

## Interfaces

A QNode differentiates through whatever framework you pick with `interface=`. The tensor type of
your trainable parameters must match.

```python
@qml.qnode(dev, interface="torch")  # or "jax", "tf", "autograd" (default)
def circuit(inputs, weights):
    qml.AngleEmbedding(inputs, wires=range(2))
    qml.BasicEntanglerLayers(weights, wires=range(2))
    return qml.expval(qml.PauliZ(0))
```

Modern `default.qubit` auto-detects the interface from the input tensors, so `interface=` is
often optional — but setting it explicitly avoids surprises. Use the framework's own autodiff to
get gradients (`loss.backward()`, `jax.grad`, `tf.GradientTape`).

## Embed a QNode as a layer (the idiomatic way)

Instead of manually looping the circuit over a batch, wrap it in a framework layer. PennyLane
manages the weight tensors for you.

### PyTorch — `qml.qnn.TorchLayer`

```python
import torch

n_qubits, n_layers = 2, 3
dev = qml.device("default.qubit", wires=n_qubits)

@qml.qnode(dev, interface="torch")
def qnode(inputs, weights):
    qml.AngleEmbedding(inputs, wires=range(n_qubits))
    qml.StronglyEntanglingLayers(weights, wires=range(n_qubits))
    return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

weight_shapes = {"weights": (n_layers, n_qubits, 3)}
qlayer = qml.qnn.TorchLayer(qnode, weight_shapes)

model = torch.nn.Sequential(
    torch.nn.Linear(8, n_qubits),
    qlayer,
    torch.nn.Linear(n_qubits, 2),
)
opt = torch.optim.Adam(model.parameters(), lr=0.01)
# standard torch training loop: opt.zero_grad(); loss.backward(); opt.step()
```

`TorchLayer` handles batching over the first dimension of `inputs`, so you feed it a batch and it
returns a batched tensor — no manual `torch.stack`.

### Keras/TensorFlow — `qml.qnn.KerasLayer`

```python
import tensorflow as tf

@qml.qnode(dev, interface="tf")
def qnode(inputs, weights):
    qml.AngleEmbedding(inputs, wires=range(n_qubits))
    qml.StronglyEntanglingLayers(weights, wires=range(n_qubits))
    return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

qlayer = qml.qnn.KerasLayer(qnode, weight_shapes, output_dim=n_qubits)
model = tf.keras.Sequential([
    tf.keras.layers.Dense(n_qubits, activation="relu"),
    qlayer,
    tf.keras.layers.Dense(2, activation="softmax"),
])
model.compile(optimizer=tf.keras.optimizers.Adam(0.01),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
```

### JAX

JAX has no PennyLane layer wrapper; write the QNode and use `jax.grad` / `jax.jit` directly. Keep
`inputs` and `weights` as `jax.numpy` arrays.

```python
import jax, jax.numpy as jnp

@jax.jit
def loss(weights, x, y):
    return jnp.mean((circuit(x, weights) - y) ** 2)

grad = jax.grad(loss)(weights, x_train, y_train)
```

## Variational classifier (from scratch)

```python
dev = qml.device("default.qubit", wires=2)

@qml.qnode(dev)
def classifier(x, weights):
    qml.AngleEmbedding(x, wires=range(2))          # feature map
    qml.StronglyEntanglingLayers(weights, wires=range(2))
    return qml.expval(qml.PauliZ(0))               # in [-1, 1]

def cost(weights, X, y):                            # y in {0,1}
    preds = (np.stack([classifier(x, weights) for x in X]) + 1) / 2
    return -np.mean(y * np.log(preds) + (1 - y) * np.log(1 - preds))

shape = qml.StronglyEntanglingLayers.shape(n_layers=2, n_wires=2)
weights = np.random.random(shape, requires_grad=True)
opt = qml.AdamOptimizer(0.05)
for _ in range(100):
    weights = opt.step(lambda w: cost(w, X_train, y_train), weights)
```

For multi-class, return one `expval(PauliZ(i))` per class and apply a softmax over the outputs.

## Encoding strategies

The feature map determines what the model can express (see also `references/circuits.md`):

- **Angle** — `qml.AngleEmbedding(x, wires)`: one feature per rotation; cheap, hardware-friendly.
- **Amplitude** — `qml.AmplitudeEmbedding(x, wires, normalize=True)`: packs `2**n` features into
  `n` qubits; expensive state preparation.
- **Basis** — `qml.BasisEmbedding(bits, wires)`: binary features into computational basis.
- **IQP** — `qml.IQPEmbedding(x, wires, n_repeats=k)`: Hadamards + ZZ couplings; a
  classically-hard feature map used in quantum-kernel methods.

Re-uploading data (interleaving encoding and trainable layers) increases expressivity for a fixed
qubit count.

## Transfer learning

Freeze pre-trained layers and train only a final block, or use a classical feature extractor
feeding a quantum classifier (dressed quantum circuit). Keep the classical extractor's output
dimension equal to the number of encoding wires:

```python
extractor = torch.nn.Sequential(torch.nn.Conv2d(3, 16, 3), torch.nn.ReLU(),
                                torch.nn.Flatten(), torch.nn.LazyLinear(n_qubits))
model = torch.nn.Sequential(extractor, qml.qnn.TorchLayer(qnode, weight_shapes),
                            torch.nn.Linear(n_qubits, n_classes))
```

## Practices

1. Start with 2-4 qubits and one or two layers; scale only after the small model trains.
2. Use `TorchLayer`/`KerasLayer` rather than hand-batching — it gets gradients and batching right.
3. Watch for barren plateaus (`references/optimization.md`); small init, shallow depth.
4. Validate on simulators before touching hardware, and switch to `parameter-shift` when you do.

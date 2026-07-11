# Machine Learning

PathML's model layer is plain PyTorch. It ships two nucleus-analysis architectures
(HoVer-Net, HACTNet), the matching loss and post-processing helpers, and public dataset
loaders. You train with an ordinary PyTorch loop (or wrap it with `pytorch-lightning`),
and deploy with TorchScript/ONNX. PathML does not hide the training loop — it gives you
the model, the loss, and the data.

> Module paths and helper names differ across PathML versions. Datasets live in
> `pathml.datasets` (not `pathml.ml.datasets`). Confirm exact imports against your
> installed version's API reference.

## Models

### HoVer-Net

`HoVerNet` performs simultaneous nucleus **instance segmentation** and **classification**
via three decoder branches:

- **NP** — nuclear-pixel (foreground vs background),
- **HV** — horizontal/vertical distance maps that separate touching nuclei,
- **NC** — nucleus-type classification (e.g. the 5 PanNuke types: neoplastic,
  inflammatory, connective, dead, epithelial).

```python
import torch
from pathml.ml import HoVerNet

model = HoVerNet(n_classes=5)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

# outputs is a tuple/list of the three branch tensors (np, hv, nc)
outputs = model(images.to(device))
```

Loss and post-processing come with the model:

```python
from pathml.ml.hovernet import loss_hovernet, post_process_batch_hovernet

loss = loss_hovernet(outputs=outputs, ground_truth=[np_gt, hv_gt, nc_gt], n_classes=5)

# convert branch outputs to labeled instances + per-instance types
preds_detection, preds_classification = post_process_batch_hovernet(outputs, n_classes=5)
```

### HACTNet

`HACTNet` classifies tissue from the hierarchical cell+tissue graph produced by
`pathml.graph` (see `graphs.md`). It consumes `HACTPairData` batches from a PyTorch-
Geometric loader. Construct it with the cell-GNN and tissue-GNN configuration your
version expects, then train with a standard classification loop.

```python
from pathml.ml import HACTNet
# model = HACTNet(<cell/tissue GNN params>)   # verify constructor for your version
```

## Datasets

```python
from pathml.datasets import PanNukeDataModule

pannuke = PanNukeDataModule(
    data_dir="path/to/pannuke",
    download=False,
    batch_size=8,
    nucleus_type_labels=True,   # return type maps for classification
    hovernet_preprocess=True,   # produce NP/HV/NC targets for HoVer-Net
)
train_loader = pannuke.train_dataloader()
valid_loader = pannuke.valid_dataloader()
test_loader  = pannuke.test_dataloader()
```

PanNuke: ~7,900 256x256 H&E patches across 19 tissue types with 5-class nucleus
annotations, split into 3 folds. `pathml.datasets` also provides other loaders (e.g.
DeepFocus) — check the module for what your version ships. For your own data, write a
standard `torch.utils.data.Dataset` returning image + target maps.

## Training loop

A minimal HoVer-Net loop; the pattern generalizes:

```python
import torch
from pathml.ml import HoVerNet
from pathml.ml.hovernet import loss_hovernet, post_process_batch_hovernet
from pathml.datasets import PanNukeDataModule

device = "cuda" if torch.cuda.is_available() else "cpu"
model  = HoVerNet(n_classes=5).to(device)
opt    = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5)
data   = PanNukeDataModule("path/to/pannuke", batch_size=8, hovernet_preprocess=True)

for epoch in range(50):
    model.train()
    for images, masks, hv, types in data.train_dataloader():
        images = images.float().to(device)
        outputs = model(images)
        loss = loss_hovernet(
            outputs=outputs,
            ground_truth=[masks.to(device), hv.to(device), types.to(device)],
            n_classes=5,
        )
        opt.zero_grad(); loss.backward(); opt.step()
```

Practical notes:

- **Fine-tune** rather than train from scratch when you can: load pretrained weights,
  freeze the encoder for a few epochs, then unfreeze at a lower LR.
- **Class imbalance** is the norm — weight the classification loss or oversample rare
  types.
- **Stability** — clip gradients (`torch.nn.utils.clip_grad_norm_`), reduce LR, or use
  mixed precision (`torch.cuda.amp`) if training is unstable or OOMs.

## PyTorch Lightning

For checkpointing, early stopping, and multi-GPU without hand-rolling the loop, wrap
the model in a `LightningModule` and let `pytorch-lightning` drive it — put `model(x)`
in `forward`, `loss_hovernet(...)` in `training_step`/`validation_step`, and log the
per-branch losses. See the `pytorch-lightning` skill for the trainer/callback setup.

## Evaluation

Instance-segmentation-and-classification is scored with pathology-specific metrics, not
plain accuracy:

- **Dice** — pixel overlap; `pathml.ml.utils` provides `dice_score` / `dice_loss`.
- **AJI** (Aggregated Jaccard Index) — instance-level overlap that penalizes
  over/under-segmentation.
- **PQ** (Panoptic Quality = SQ × RQ) — the standard joint segmentation+detection
  metric for HoVer-Net-style outputs.

Compute AJI/PQ from post-processed instances (`post_process_batch_hovernet`) versus
ground-truth instances using the standard HoVer-Net evaluation formulas; PathML's
utilities cover Dice, and the AJI/PQ implementations from the HoVer-Net reference code
are the accepted baseline.

## Inference and deployment

Batch inference over a slide: tile the WSI, run the model per batch of tiles,
post-process, and stitch instance/type maps back to slide coordinates (see
`data_management.md` for stitching).

Export to ONNX for a framework-independent runtime:

```python
import torch
dummy = torch.randn(1, 3, 256, 256)
torch.onnx.export(
    model, dummy, "hovernet.onnx",
    input_names=["input"], output_names=["np", "hv", "nc"],
    dynamic_axes={"input": {0: "batch"}},
    opset_version=11,
)
```

Then run with `onnxruntime` and apply the same `post_process_batch_hovernet` step to the
raw branch outputs. HoVer-Net's HV branch is what separates touching nuclei — keep the
post-processing step; the raw NP mask alone under-segments clusters.

## External references

- PathML ML API: https://pathml.readthedocs.io/en/latest/api_ml_reference.html
- HoVer-Net: Graham et al., "HoVer-Net," Medical Image Analysis, 2019.
- PanNuke: https://warwick.ac.uk/fac/cross_fac/tia/data/pannuke
- ONNX Runtime: https://onnxruntime.ai/

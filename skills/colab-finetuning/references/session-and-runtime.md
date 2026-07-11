# Colab session, runtime, and VRAM budget

The Colab-specific constraints that shape any fine-tuning run. The trainer code itself lives in
the `unsloth` / `trl-fine-tuning` siblings — this file is only the environment envelope.

## Pick and confirm the runtime FIRST

A fresh notebook defaults to CPU. Nothing GPU-related works until you switch:

- **Runtime → Change runtime type → Hardware accelerator → GPU** (pick the tier — see table).
- Confirm the actual device before you build the image or load a model:

```python
!nvidia-smi                    # shows the card + total/used VRAM; empty output = no GPU attached
import torch; print(torch.cuda.get_device_name(0), torch.cuda.is_available())
```

If `nvidia-smi` errors or `is_available()` is `False`, you are on CPU — stop and fix the runtime
type. Do not "just start training"; it will silently fall back to CPU and crawl.

## GPU tiers (approximate — verify current allocation)

Colab does **not** guarantee which card you get; it allocates dynamically by demand and tier.
Prices and allocations drift — treat this as orientation, not a contract.

| Tier            | Typical GPU        | VRAM   | Practical ceiling (QLoRA 4-bit)      |
|-----------------|--------------------|--------|--------------------------------------|
| Free            | Tesla T4           | 16 GB  | up to ~8-9B model, seq ≤ 2048, bs 1-2 |
| Free (variable) | sometimes none     | —      | may get CPU-only if GPUs are busy    |
| Pro             | L4 / V100 / T4     | 16-24 GB | ~13B model, longer seq              |
| Pro / Pro+      | A100 (40 GB)       | 40 GB  | ~30B QLoRA, or 7-13B 16-bit LoRA     |

Free tier is single-GPU only — there is no multi-GPU on Colab free. For sharded/multi-node work
use `distributed-training`.

## Timeouts and disconnects (the reason persistence is mandatory)

These are the hard limits that kill runs. Design around them, do not fight them:

- **Idle timeout ~90 min** — if the browser tab is closed/inactive and nothing is executing, the
  VM is reclaimed. Free tier especially.
- **Max lifetime ~12 h** (free) — the VM is recycled even under active use. Pro/Pro+ extend this
  (up to ~24 h) but it is still finite.
- **Preemption** — free VMs can be reclaimed early when demand is high, with little warning.
- **Everything under `/content` is wiped** on disconnect, including `/content/sample_data` and any
  checkpoints you left there. Only Google Drive and the HF Hub survive — see
  `persistence-and-checkpointing.md`.

### Background execution (Pro+ only)

Colab Pro+ keeps a notebook running after you close the tab. On free/Pro, closing the tab starts
the idle clock. Do **not** rely on browser "keep-alive" hacks (auto-clicking JS in the console) —
they violate the ToS, are unreliable, and do not extend the 12 h cap. If a run must survive a
closed laptop and you are not on Pro+, move it to `modal-ml-training` or a reserved GPU host.

## `!pip install` pitfalls

Colab ships a large, pinned preinstalled stack (a specific torch/CUDA, transformers, etc.).
Installing training libs on top routinely conflicts:

- **A restart may be forced.** After a big install Colab shows "RESTART SESSION". You must restart
  (Runtime → Restart) *and re-run* the mount/secrets cells — a restart wipes Python state but not
  `/content`.
- **Do not blindly `pip install torch`.** It can pull a wheel mismatched with Colab's CUDA driver.
  Prefer the framework's Colab-tested install line (Unsloth publishes one; see the `unsloth`
  skill) and let it manage torch.
- **Pin what you add**, and install in one cell early, before importing anything, so a forced
  restart happens before you have spent GPU time.
- `%pip` (magic) installs into the running kernel more reliably than `!pip` (shell) in some
  environments — either works, but be consistent.

## Secrets — never hardcode tokens in a shared notebook

Notebooks get shared and committed. Put tokens in the Colab **Secrets** panel (key icon, left
sidebar), grant the notebook access, then read them at runtime:

```python
from google.colab import userdata
import os
os.environ["HF_TOKEN"]        = userdata.get("HF_TOKEN")       # gated repos + push_to_hub
os.environ["WANDB_API_KEY"]   = userdata.get("WANDB_API_KEY")  # optional monitoring
```

`userdata.get` raises `SecretNotFoundError` if the secret is missing and
`NotebookAccessError` if you have not toggled notebook access for that secret — catch these and
print a clear "add your HF_TOKEN in the Secrets panel" message rather than letting the stack trace
confuse a first-time user.

## T4 VRAM budgeting (the 16 GB reality)

On free T4, 16 GB fills fast. In rough order of impact:

- **QLoRA 4-bit is effectively mandatory** above ~3B params. Load a pre-quantized `-bnb-4bit`
  checkpoint so you never materialize fp16 weights.
- **`per_device_train_batch_size = 1-2`**, recover effective batch size with
  `gradient_accumulation_steps` (8-16). Grad-accum costs time, not memory.
- **Gradient checkpointing on** — with Unsloth use `use_gradient_checkpointing = "unsloth"` for
  its memory-optimized variant (biggest single lever for long sequences).
- **`max_seq_length`** drives activation memory quadratically-ish — start at 1024-2048 on T4, only
  raise it if `nvidia-smi` shows headroom.
- **Watch VRAM live**: `!nvidia-smi` in a separate cell mid-run, or
  `torch.cuda.max_memory_allocated()/1e9` after a step. If you are within ~1 GB of the ceiling you
  will OOM on a long batch — shrink seq length or batch first.

See `failure-modes.md` for the OOM recovery ladder and other symptom→fix pairs.

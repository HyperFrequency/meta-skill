# Persistence, checkpointing, and export on Colab

The single rule: **nothing under `/content` survives a disconnect.** Every artifact you care about
must land on Google Drive or the HF Hub *before* the session dies. This file covers the three
durable-output patterns and the resume flow.

## Mount Google Drive (durable scratch)

```python
from google.colab import drive
drive.mount("/content/drive")          # opens an OAuth consent popup the first time
OUT = "/content/drive/MyDrive/finetune/run-2026-07-10"
import os; os.makedirs(OUT, exist_ok=True)
```

Notes:
- The mount can hang if the OAuth popup is blocked — allow popups for `colab.research.google.com`.
- Drive I/O is **slow** (network filesystem). Write checkpoints there, but keep the *active*
  training loop reading/writing the fast local disk (`/content`) and only sync checkpoints out at
  `save_steps`. Streaming every step to Drive will bottleneck the trainer.
- Drive has a per-account quota. A few full-model checkpoints (10s of GB) can fill it — prefer
  saving **LoRA adapters** (tens of MB), not merged weights, for intermediate checkpoints.

## Checkpoint to Drive + resume (survive the 12 h cap)

Point `output_dir` at Drive and save periodically; if the VM recycles at hour 6, a new session
resumes from the last checkpoint instead of from zero.

```python
from transformers import TrainingArguments
args = TrainingArguments(
    output_dir              = OUT,          # on Drive → survives disconnect
    save_strategy           = "steps",
    save_steps              = 50,           # tune vs. Drive write cost, not a round number
    save_total_limit        = 2,            # keep Drive from filling with old checkpoints
    per_device_train_batch_size = 2,
    gradient_accumulation_steps = 8,
    # ... lr, scheduler, etc. — see the trainer skill
)
trainer = ...                              # SFTTrainer / GRPOTrainer from the unsloth/trl skill
trainer.train(resume_from_checkpoint=True) # True = auto-detect latest ckpt in output_dir
```

On a fresh session after a disconnect: re-run the install, mount, and secrets cells, rebuild the
`trainer` with the **same `output_dir`**, and call `train(resume_from_checkpoint=True)`. Maximum
lost progress equals your `save_steps` interval. `resume_from_checkpoint=True` no-ops cleanly on
the first run (no checkpoint yet), so the same cell works cold and warm.

## Save the final adapter (small, always do this)

LoRA adapters are tens of MB — save them the instant training finishes, before doing anything
that might crash:

```python
model.save_pretrained(f"{OUT}/adapter")          # local/Drive copy
tokenizer.save_pretrained(f"{OUT}/adapter")
model.push_to_hub(f"user/my-model-lora", token=os.environ["HF_TOKEN"])   # Hub copy = safest
```

Push to the **Hub** as the primary durable store when you can — it is independent of your Drive
quota and survives even a Google account issue.

## Merge / export (16-bit and GGUF)

Adapters need a base model to run. Export a standalone artifact only at the end (it is large and
slow). With Unsloth:

```python
# merged 16-bit (for vLLM / HF inference)
model.save_pretrained_merged(f"{OUT}/merged_16bit", tokenizer, save_method="merged_16bit")
model.push_to_hub_merged("user/my-model", tokenizer, save_method="merged_16bit",
                         token=os.environ["HF_TOKEN"])

# GGUF (for llama.cpp / Ollama) — compiles llama.cpp on first call, can take several minutes
model.push_to_hub_gguf("user/my-model-gguf", tokenizer,
                       quantization_method=["q4_k_m", "q8_0"], token=os.environ["HF_TOKEN"])
```

GGUF export pitfalls specific to Colab:
- The first GGUF call **builds llama.cpp from source** in the VM — it is CPU-bound and eats
  minutes; do it once at the end, not per checkpoint.
- Merged/GGUF files can be many GB and blow the T4 VM's ~78 GB disk or your Drive quota — push
  straight to the Hub rather than staging a merged copy on `/content` when disk is tight.
- Do the merge/export **before** the 12 h cap, not at 11:55 — a recycle mid-export loses it.

## Ordering checklist (do these in order, every run)

1. Set GPU runtime, `!nvidia-smi` confirms the card.
2. Install (one cell, early); restart + re-run if Colab forces it.
3. Mount Drive, load secrets.
4. Build trainer with `output_dir` on Drive, `save_steps` set.
5. `train(resume_from_checkpoint=True)`.
6. On finish: save adapter → push to Hub → (optional) merge/GGUF export.

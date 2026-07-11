# Colab fine-tuning failure modes (symptom → fix)

The problems that actually stop Colab runs, and the fastest fix for each. OOM and session-death
dominate; the rest are setup traps.

| Symptom | Likely cause | Fix |
|---|---|---|
| `CUDA out of memory` early | Model too big for 16 GB, or not 4-bit | Load a pre-quantized `-bnb-4bit` checkpoint (`load_in_4bit=True`); this is mandatory above ~3B on T4. |
| `CUDA out of memory` after N steps | Sequence length / batch too large | Drop `max_seq_length` (2048→1024), set `per_device_train_batch_size=1`, raise `gradient_accumulation_steps`, enable `use_gradient_checkpointing="unsloth"`. |
| OOM only on some batches | A few long samples spike activation memory | Filter/pack by length, or lower `max_seq_length`; grad-accum does not help here (per-sample, not per-accum). |
| Training crawls / no GPU util | Runtime is CPU, or fell back to CPU | Runtime → Change runtime type → GPU; confirm with `!nvidia-smi` and `torch.cuda.is_available()`. Re-run after switching. |
| Session died mid-train, all gone | Checkpoints were under `/content` (ephemeral) | Point `output_dir` at `/content/drive/...`; `train(resume_from_checkpoint=True)` on the new session. See `persistence-and-checkpointing.md`. |
| Disconnected after ~90 min idle | Idle timeout on a closed/inactive tab | Keep the tab active, or use Pro+ background execution; for unattended long runs move to `modal-ml-training`. Do not use JS keep-alive hacks. |
| VM recycled at ~12 h | Free-tier max lifetime | Resume from the last Drive checkpoint; if runs routinely exceed 12 h, upgrade tier or move off Colab. |
| `drive.mount` hangs / no popup | OAuth popup blocked | Allow popups for `colab.research.google.com`; re-run the mount cell. |
| "RESTART SESSION" after install | pip upgraded a preinstalled package | Runtime → Restart, then **re-run** the mount + secrets + import cells (state is wiped, `/content` is not). |
| `ImportError` / torch/CUDA mismatch after install | `pip install torch` pulled an incompatible wheel | Use the framework's Colab-tested install line (Unsloth publishes one); do not hand-install torch. |
| `SecretNotFoundError` / `NotebookAccessError` | Secret missing or notebook access not granted | Add the token in the Secrets panel (key icon) and toggle notebook access; then re-run. |
| `No space left on device` | `/content` VM disk (~78 GB) full from merged/GGUF exports or datasets | Push merged/GGUF straight to the Hub instead of staging locally; delete intermediate files; clear the dataset cache. |
| Push to Hub 401 / gated repo error | `HF_TOKEN` missing or no write scope | Load `HF_TOKEN` via `userdata.get`; ensure the token has **write** access and you accepted the base model's license. |
| GGUF export "takes forever" | First call compiles llama.cpp from source | Expected — it is CPU-bound; run it once at the end, not per checkpoint. |
| Everything slower than a local RTX card | Free T4 is a modest GPU; shared VM | Accept it for small QLoRA jobs; for real throughput use a rented A100/H100 (`modal-ml-training`, or a reserved host). |

## The two habits that prevent most losses

1. **`output_dir` on Drive + `save_steps` set** — turns "session died, start over" into "resume,
   lose one interval."
2. **Save the adapter and push to the Hub the moment training finishes** — before any
   merge/export step that could crash the VM. The adapter is tiny; losing it is inexcusable.

## When to leave Colab entirely

Colab free is right for learning, small QLoRA jobs (≤ ~8B, a few hours), and prototyping. Stop
fighting it and move off when: runs need > 12 h unattended, you need multiple GPUs, you need a
guaranteed card, or you are paying Pro+ for what a spot A100 hour elsewhere does cheaper. Route to
`modal-ml-training` (disconnect-safe serverless GPU) or `distributed-training` (multi-GPU), and
sanity-check the economics with `model-economics`.

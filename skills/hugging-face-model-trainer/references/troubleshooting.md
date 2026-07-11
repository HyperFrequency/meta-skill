# Troubleshooting & Reliability

Symptom → cause → fix for TRL-on-Jobs training, plus the reliability rules that
push job success rate from "often fails" to "just works". Following these before
submitting is far cheaper than debugging a failed GPU job.

## Training hangs at "Starting training..."

**Cause:** `eval_strategy="steps"` or `"epoch"` is set but no `eval_dataset` was
passed to the trainer. The loop waits forever — it never progresses and never
times out on its own.

**Fix — provide the split** (recommended):

```python
split = dataset.train_test_split(test_size=0.1, seed=42)
SFTTrainer(train_dataset=split["train"], eval_dataset=split["test"],
           args=SFTConfig(eval_strategy="steps", eval_steps=50, ...))
```

**Or disable eval:** `SFTConfig(eval_strategy="no")` and pass no `eval_dataset`.

## Out of memory (OOM)

Walk this ladder in order; stop when it fits:

1. **Smaller batch:** `per_device_train_batch_size=1`.
2. **Grad accumulation** to keep the effective batch: `gradient_accumulation_steps=8`
   (effective = per-device × accumulation × num_gpus; ~128 is a good target).
3. **Drop eval** (`eval_strategy="no"`, no `eval_dataset`) — saves ~40% for demos.
4. **LoRA/PEFT:** `peft_config=LoraConfig(r=8, lora_alpha=16)` — smaller rank,
   less memory.
5. **Gradient checkpointing:** `gradient_checkpointing=True` (slower, big saving).
6. **Mixed precision:** `bf16=True` (or `fp16=True`).
7. **Bigger GPU:** t4-small → l4x1 → a10g-large → a100-large.

VRAM rough fit: T4 16 GB → <1B LoRA; A10G 24 GB → 1–3B LoRA (or <1B full);
A100 40 GB → 7B LoRA (or 3B full).

## Job times out

Default 30 min is too short. Increase `--timeout` (`"3h"`) with a 20–30% buffer;
or reduce `num_train_epochs` / dataset size / `max_steps`; or use a smaller model
or LoRA. Enable checkpointing (`save_strategy="steps"`, `hub_strategy="every_save"`)
so a timeout doesn't cost everything and you can `resume_from_checkpoint`. Check
actual runtime in `hf jobs logs <id>` to right-size next time.

## Model not on the Hub after training

All work lost unless pushed. Check every box:

- `push_to_hub=True` in the config
- `hub_model_id="username/model-name"` (with namespace)
- `--secrets HF_TOKEN` on the job
- token has **write** scope (`hf auth whoami`)
- script calls `trainer.push_to_hub()` at the end
- you have write access to the target namespace

If the model saved but isn't visible: it may be private (check your profile), the
namespace may be wrong, or the push is still in flight — wait a few minutes. See
[hub-and-monitoring.md](hub-and-monitoring.md).

## `TypeError: ... unexpected keyword argument 'max_seq_length'`

Recent TRL configs use **`max_length`**, not `max_seq_length`:

```python
SFTConfig(max_length=512)     # correct
DPOConfig(max_length=2048)    # correct
# SFTConfig(max_seq_length=512)  # TypeError
```

Default is `max_length=1024` (right-truncation), fine for most training — set it
only to change context length. For **vision models**, use `max_length=None` so
image tokens aren't cut. Field names drift by version; pin TRL in the header and
confirm with `hf_doc_fetch("https://huggingface.co/docs/trl/sft_trainer")`.

## Dataset format error

1. Check the method's expected columns (SFT: `messages`/`text`/`prompt`+`completion`;
   DPO: `prompt`/`chosen`/`rejected`; GRPO: prompt-only).
2. Validate before training (CPU, pennies) — see
   [training-methods.md](training-methods.md) for the inspect + remap pattern.
3. Confirm the split exists: `load_dataset("name", split="train[:5]")`.
4. Format spec: `hf_doc_fetch("https://huggingface.co/docs/trl/dataset_formats")`.

## Import / ModuleNotFoundError

The PEP 723 header is missing the package or malformed. Delimiters must be exactly
`# /// script` … `# ///` (space after `#`), and names must be valid PyPI packages:

```python
# /// script
# dependencies = ["trl>=0.12.0", "peft>=0.7.0", "transformers>=4.36.0"]
# ///
```

Test the resolve locally first with `uv run train.py`.

## Authentication errors

`hf auth whoami` to confirm identity; ensure the token is **write** (not
read-only) at https://huggingface.co/settings/tokens; confirm `--secrets HF_TOKEN`
is on the job; for org repos, confirm membership + write access.

## Job stuck "pending" / not starting

GPU queues or account/billing (Jobs needs a paid plan). Typical startup: CPU
10–30 s, GPU 30–90 s; over ~3 min means queued or stuck. Try a different flavor,
check https://huggingface.co/jobs, verify billing.

## Loss not decreasing

Learning rate off (try 2e-5–5e-5, or lower if diverging); inspect a few examples
for data quality; the model may be too small for the task; needs more epochs/data;
or the dataset format is wrong (degrades training silently).

## Logs not appearing

Initial logs lag 30–60 s. Use `hf jobs logs <id>`, `hf jobs inspect <id>`, or
Trackio for live metrics.

---

## Reliability rules (prevention beats debugging)

1. **Verify before use.** Never assume a repo/dataset exists —
   `hub_repo_details([...], repo_type=...)` first. A typo fails the job after you
   pay to start it; the check costs seconds.
2. **Reliability over performance.** Default to what succeeds, not what's
   fastest. Skip `torch_compile` (fails on T4/A10G) unless on H100; use
   `optim="adamw_torch"`; build with CMake not `make`. Optimize only after a
   proven run.
3. **Atomic, self-contained scripts.** All deps pinned in the PEP 723 header, all
   system packages installed by the script, no reliance on pre-existing setup.
   Don't trim "unneeded" deps — `sentencepiece`/`protobuf` fail **silently** when
   missing (see [gguf-conversion.md](gguf-conversion.md)).
4. **Clear error context.** Wrap `subprocess.run(..., capture_output=True,
   text=True)` in try/except and print `stdout`/`stderr`; validate env vars early
   with explicit messages; log the config at start.
5. **Test the happy path first.** Prove new code on known-good small inputs
   (`Qwen/Qwen2.5-0.5B` + `trl-lib/Capybara`) before production data — if the
   test passes and production fails, you know it's the inputs, not the code.

## See also

- [training-methods.md](training-methods.md) · [jobs-and-hardware.md](jobs-and-hardware.md) · [hub-and-monitoring.md](hub-and-monitoring.md) · [gguf-conversion.md](gguf-conversion.md)
- `hf_doc_search("your issue", product="trl")` · HF forums: https://discuss.huggingface.co/

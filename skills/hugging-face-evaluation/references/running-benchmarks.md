# Running Benchmarks (lighteval / inspect-ai)

Produce the scores you will publish, either on a local GPU or on Hugging Face
Jobs. Two frameworks are supported; pick one, run it, then feed the numbers into
the write path in `references/model-index-format.md`.

| | lighteval | inspect-ai |
|---|---|---|
| Author | Hugging Face | UK AI Safety Institute |
| Task syntax | `suite\|task\|num_fewshot` | task name (`mmlu`, `gsm8k`, …) |
| Backends | `vllm`, `accelerate` | `vllm`, `hf` (Transformers) |
| Strength | Open LLM Leaderboard parity | safety/agentic evals, clean logs |

Both evaluate **any** HF model on your own hardware (offline after download),
versus inference-provider evals which hit a hosted API and bill per token.

## lighteval

Task strings are `suite|task|num_fewshot`:

- `leaderboard|mmlu|5` — MMLU, 5-shot
- `leaderboard|gsm8k|5` — GSM8K, 5-shot
- `leaderboard|arc_challenge|25` — ARC-Challenge, 25-shot
- `lighteval|hellaswag|0` — HellaSwag, zero-shot

Common suites: `leaderboard` (Open LLM Leaderboard tasks), `lighteval`,
`bigbench`, `original`. The full task list ships in the lighteval repo at
`examples/tasks/all_tasks.txt`, one `suite|task|num_fewshot|version` per line —
drop the trailing version field when you pass a task.

```bash
# local GPU, vLLM backend
lighteval vllm \
  "model_name=meta-llama/Llama-3.2-1B" \
  "leaderboard|mmlu|5"

# multiple tasks, comma-separated
lighteval vllm \
  "model_name=meta-llama/Llama-3.2-1B" \
  "leaderboard|mmlu|5,leaderboard|gsm8k|5"

# accelerate (HF Transformers) backend instead of vLLM
lighteval accelerate \
  "model_name=meta-llama/Llama-3.2-1B" \
  "leaderboard|mmlu|5"
```

For instruction-tuned models, enable the chat template (lighteval exposes
`use_chat_template`/`--use-chat-template` depending on version) so prompts are
formatted correctly; do **not** enable it for base models with no template.

> lighteval's CLI has shifted across releases (argument style, model-args
> syntax). Run `lighteval --help` and `lighteval vllm --help` on the installed
> version and follow it rather than assuming flag names.

## inspect-ai

Standard tasks live in the `inspect-evals` package. Run with `inspect eval`,
selecting a model provider/backend via `--model`:

```bash
# vLLM backend
inspect eval inspect_evals/mmlu --model vllm/meta-llama/Llama-3.2-1B

# HF Transformers backend
inspect eval inspect_evals/mmlu --model hf/meta-llama/Llama-3.2-1B
```

Frequently used tasks: `mmlu`, `gsm8k`, `hellaswag`, `arc_challenge`,
`truthfulqa`, `winogrande`, `humaneval`. Consult the `inspect-evals` registry
for the full set and exact task ids on your installed version.

Multi-GPU: pass tensor parallelism through to vLLM (`-M tensor_parallel_size=4`
or the model-args form your version expects) for models too large for one card.

## Running on Hugging Face Jobs

No Dockerfile or Space needed — submit a `uv`-runnable script and HF provisions
the hardware, installing PEP 723 dependencies at launch. Pass `HF_TOKEN` as a
secret, never as a plain arg:

```bash
hf jobs uv run scripts/lighteval_vllm.py \
  --flavor a10g-small \
  --secrets HF_TOKEN=$HF_TOKEN \
  -- --model meta-llama/Llama-3.2-1B \
     --tasks "leaderboard|mmlu|5"
```

The `--` separates job/hardware flags (left) from your script's args (right).

## Hardware sizing

Pick a flavor by model size; scale up on OOM.

| Model size   | Flavor        |
|--------------|---------------|
| < 3B params  | `t4-small`    |
| 3B – 13B     | `a10g-small`  |
| 13B – 34B    | `a10g-large`  |
| 34B+         | `a100-large`  |

Non-CPU flavors require a payment method on the HF account.

## Troubleshooting

- **CUDA / vLLM OOM** — use a larger flavor, lower `gpu_memory_utilization`, or
  shard with `tensor_parallel_size` across GPUs.
- **"Architecture not supported by vLLM"** — switch to the Transformers path
  (`hf/...` in inspect-ai, `lighteval accelerate`).
- **"Trust remote code required"** (Phi, some Qwen) — pass the framework's
  `trust_remote_code` / `--trust-remote-code` option.
- **Chat template missing** — only enable chat templating for instruction-tuned
  models that actually ship one; base models will error.
- **Payment required for hardware** — add a payment method to use non-CPU HF Job
  flavors.

## After the run

Collect each task's headline metric, map benchmark → `type`
(see `references/model-index-format.md`), set `source.name` to the framework
(`lighteval` / `inspect-ai`) and `source.url` to the model page, then publish via
the write path. Record `num_fewshot` in the metric `name` (e.g. `MMLU (5-shot)`)
so the shot count is not lost.

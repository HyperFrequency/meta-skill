# Converting Trained Models to GGUF

After training, convert to **GGUF** (GPT-Generated Unified Format) to run the
model locally with llama.cpp, Ollama, LM Studio, Jan, or GPT4All. GGUF supports
quantization (4/5/8-bit), shrinking a 7B model from ~14 GB to ~2–8 GB, and runs
on CPU or GPU.

**Convert when** you want local/offline inference, CPU deployment, edge devices,
or a smaller shareable artifact. **Skip** if you'll only serve on the Hub or a
GPU endpoint.

## Run it as a Job

Conversion is CPU/GPU work best done on a Jobs runner (an `a10g-large` converts a
0.5B model in ~15–25 min, 7B in ~45–60 min). LoRA adapters are merged into the
base model first, then converted and quantized, then all variants are uploaded.

**Verify the inputs exist before submitting** (a typo wastes the whole job):

```python
hub_repo_details(["username/my-finetuned-model"], repo_type="model")
hub_repo_details(["Qwen/Qwen2.5-0.5B"], repo_type="model")
```

Submit with the base/adapter/output repos passed as env vars:

```bash
hf jobs uv run --flavor a10g-large --timeout 45m --secrets HF_TOKEN \
  --env ADAPTER_MODEL=username/my-finetuned-model \
  --env BASE_MODEL=Qwen/Qwen2.5-0.5B \
  --env OUTPUT_REPO=username/my-model-gguf \
  "https://huggingface.co/USER/scripts/resolve/main/convert_to_gguf.py"
```

## Four things that make conversion reliable

These come from real production failures — each prevents a silent or cryptic
break:

1. **Install build tools BEFORE cloning llama.cpp.** The quantizer needs a C
   toolchain:

   ```python
   subprocess.run(["apt-get", "update", "-qq"], check=True)
   subprocess.run(["apt-get", "install", "-y", "-qq", "build-essential", "cmake"], check=True)
   ```

2. **Build with CMake, not `make`.** CMake gives a consistent binary path:

   ```python
   subprocess.run(["cmake", "-B", "/tmp/llama.cpp/build", "-S", "/tmp/llama.cpp",
                   "-DGGML_CUDA=OFF"], check=True)   # CUDA off: faster build, not needed to quantize
   subprocess.run(["cmake", "--build", "/tmp/llama.cpp/build",
                   "--target", "llama-quantize", "-j", "4"], check=True)
   # binary at: /tmp/llama.cpp/build/bin/llama-quantize
   ```

3. **Include every dependency** in the PEP 723 header — do **not** trim to
   "simplify". `sentencepiece` and `protobuf` are required for tokenizer
   conversion and their absence causes **silent** failure:

   ```python
   # /// script
   # dependencies = [
   #   "transformers>=4.36.0", "peft>=0.7.0", "torch>=2.0.0",
   #   "accelerate>=0.24.0", "huggingface_hub>=0.20.0",
   #   "sentencepiece>=0.1.99", "protobuf>=3.20.0", "numpy", "gguf",
   # ]
   # ///
   ```

4. **Verify names before use** (see the `hub_repo_details` calls above).

## Conversion steps (what the script does)

1. Load base model + LoRA adapter, **merge** them.
2. `apt-get install build-essential cmake` (before cloning).
3. Clone llama.cpp, install its Python deps.
4. Convert the merged model to an **FP16 GGUF** with llama.cpp's converter.
5. Build `llama-quantize` with CMake.
6. Quantize to **Q4_K_M, Q5_K_M, Q8_0** (give users options).
7. Upload all variants + a generated README to `OUTPUT_REPO`.

Wrap each `subprocess.run(..., capture_output=True, text=True)` in
try/except and print `stdout`/`stderr` on failure — build errors are otherwise
opaque.

## Quantization options (7B reference)

| Format | ~Size (7B) | Quality | When |
|--------|-----------|---------|------|
| **Q4_K_M** | ~4 GB | good | **default** — best size/quality balance |
| **Q5_K_M** | ~5 GB | better | slightly larger, higher quality |
| **Q8_0** | ~7 GB | very high | near-original |
| **F16** | ~14 GB | original | full precision, largest |

## Using the GGUF

**Ollama** (auto-detects GPU):

```bash
hf download username/my-model-gguf model-q4_k_m.gguf
echo "FROM ./model-q4_k_m.gguf" > Modelfile
ollama create my-model -f Modelfile && ollama run my-model
```

**llama.cpp:**

```bash
./llama-cli -m model-q4_k_m.gguf -p "Your prompt"          # CPU
./llama-cli -m model-q4_k_m.gguf -ngl 32 -p "Your prompt"  # offload 32 layers to GPU
```

**LM Studio:** download the `.gguf`, import, chat.

## Common failures

| Symptom | Fix |
|---------|-----|
| OOM during merge | bigger GPU (`a10g-large`/`a100-large`), `device_map="auto"`, `dtype=torch.float16`/`bfloat16` |
| Architecture unsupported | ensure llama.cpp supports it (Qwen/Llama/Mistral OK); clone latest llama.cpp |
| Quantize fails | build tools missing, or used `make` — install `build-essential cmake`, build with CMake; check FP16 GGUF exists first |
| Missing-sentencepiece / silent tokenizer fail | add `sentencepiece` + `protobuf` to the header |
| Upload times out | raise `--timeout` (>2 GB models); upload variants separately |

## See also

- llama.cpp: https://github.com/ggerganov/llama.cpp
- GGUF spec: https://github.com/ggerganov/ggml/blob/master/docs/gguf.md
- [hub-and-monitoring.md](hub-and-monitoring.md) — the trained model must be on the Hub first
- [jobs-and-hardware.md](jobs-and-hardware.md) — flavors, timeouts, `--env` handling

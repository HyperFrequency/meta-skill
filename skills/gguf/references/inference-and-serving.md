# GGUF Inference, Serving, and Hardware

Python bindings, server mode, hardware tuning, and tool integration. See `../SKILL.md` for the
lean overview and `advanced-usage.md` for batching/speculative decoding/grammars/LoRA.

## Python usage (llama-cpp-python)

### Text completion

```python
from llama_cpp import Llama

llm = Llama(
    model_path="./model-q4_k_m.gguf",
    n_ctx=4096,          # Context window
    n_gpu_layers=35,     # GPU offload (0 for CPU only)
    n_threads=8          # CPU threads
)

output = llm(
    "What is machine learning?",
    max_tokens=256,
    temperature=0.7,
    stop=["</s>", "\n\n"]
)
print(output["choices"][0]["text"])
```

### Chat completion

```python
llm = Llama(
    model_path="./model-q4_k_m.gguf",
    n_ctx=4096,
    n_gpu_layers=35,
    chat_format="llama-3"  # Or "chatml", "mistral", etc.
)

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Python?"}
]

response = llm.create_chat_completion(messages=messages, max_tokens=256, temperature=0.7)
print(response["choices"][0]["message"]["content"])
```

### Streaming

```python
llm = Llama(model_path="./model-q4_k_m.gguf", n_gpu_layers=35)

for chunk in llm("Explain quantum computing:", max_tokens=256, stream=True):
    print(chunk["choices"][0]["text"], end="", flush=True)
```

## Server mode

### Start an OpenAI-compatible server

```bash
# Native binary
./build/bin/llama-server -m model-q4_k_m.gguf \
    --host 0.0.0.0 --port 8080 -ngl 35 -c 4096

# Or with Python bindings
python -m llama_cpp.server \
    --model model-q4_k_m.gguf --n_gpu_layers 35 \
    --host 0.0.0.0 --port 8080
```

### Use with the OpenAI client

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="local-model",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256
)
print(response.choices[0].message.content)
```

## Hardware optimization

### Apple Silicon (Metal)

Metal is enabled by default on macOS builds. Offload all layers for best throughput.

```bash
./build/bin/llama-cli -m model.gguf -ngl 99 -p "Hello"
```

```python
llm = Llama(model_path="model.gguf", n_gpu_layers=99, n_threads=1)  # Metal handles parallelism
```

### NVIDIA CUDA

```bash
# Build: cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release
./build/bin/llama-cli -m model.gguf -ngl 35 -p "Hello"

# Pin a specific GPU
CUDA_VISIBLE_DEVICES=0 ./build/bin/llama-cli -m model.gguf -ngl 35
```

### CPU

```bash
./build/bin/llama-cli -m model.gguf -t 8 -p "Hello"  # -t = physical cores
```

```python
llm = Llama(
    model_path="model.gguf",
    n_gpu_layers=0,      # CPU only
    n_threads=8,         # Match physical cores
    n_batch=512          # Batch size for prompt processing
)
```

## Integration with tools

### Ollama

```bash
cat > Modelfile << 'EOF'
FROM ./model-q4_k_m.gguf
TEMPLATE """{{ .System }}
{{ .Prompt }}"""
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
EOF

ollama create mymodel -f Modelfile
ollama run mymodel "Hello!"
```

### LM Studio

1. Place the GGUF file in `~/.cache/lm-studio/models/`
2. Open LM Studio and select the model
3. Configure context length and GPU offload
4. Start inference

### text-generation-webui

```bash
cp model-q4_k_m.gguf text-generation-webui/models/
python server.py --model model-q4_k_m.gguf --loader llama.cpp --n-gpu-layers 35
```

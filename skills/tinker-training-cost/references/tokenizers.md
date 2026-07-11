# Tokenizer Selection Reference

Accurate cost estimates depend on counting tokens with the base model's **own**
tokenizer. A generic tokenizer will give a different count for the same text and
skew the estimate. Load tokenizers from Hugging Face with `AutoTokenizer`.

## Model-to-tokenizer mapping

| Model                       | Hugging Face tokenizer                       | Note              |
| --------------------------- | -------------------------------------------- | ----------------- |
| Qwen3-4B-Instruct-2507      | `Qwen/Qwen3-4B`                              | `trust_remote_code` |
| Qwen3-8B                    | `Qwen/Qwen3-8B`                              | `trust_remote_code` |
| Qwen3-30B-A3B               | `Qwen/Qwen3-30B-A3B`                         | `trust_remote_code` |
| Qwen3-32B                   | `Qwen/Qwen3-32B`                             | `trust_remote_code` |
| Qwen3-235B-Instruct-2507    | `Qwen/Qwen3-235B-A22B-Instruct`             | `trust_remote_code` |
| Qwen3-VL-* (30B, 235B)      | `Qwen/Qwen2.5-VL-7B-Instruct`               | **proxy**, text-only |
| Llama-3.2-1B                | `meta-llama/Llama-3.2-1B-Instruct`          | gated             |
| Llama-3.2-3B                | `meta-llama/Llama-3.2-3B-Instruct`          | gated             |
| Llama-3.1-8B                | `meta-llama/Llama-3.1-8B-Instruct`          | gated             |
| Llama-3.1-70B               | `meta-llama/Llama-3.1-70B-Instruct`         | gated             |
| DeepSeek-V3.1               | `deepseek-ai/DeepSeek-V3`                   | `trust_remote_code` |
| GPT-OSS-120B / GPT-OSS-20B  | `Qwen/Qwen3-8B`                             | **proxy**         |
| Kimi-K2-Thinking            | `moonshotai/Kimi-K2-Instruct`               |                   |

### Proxy tokenizers (approximate)

- **GPT-OSS** maps to the Qwen3-8B tokenizer as a compatible stand-in. GPT-OSS
  actually uses a different (o200k/harmony-style) vocabulary, so counts here are
  approximate — expect drift on code and non-English text. Swap in the real
  GPT-OSS tokenizer if you have access and need a tight estimate.
- **Qwen3-VL** maps to the Qwen2.5-VL text tokenizer. It counts text tokens
  only; image tokens are not included, so multimodal datasets will under-count.

## Accurate counting: apply the chat template

For chat-format rows, the number of tokens Tinker actually processes includes the
role markers and special tokens the chat template inserts. Counting the raw
concatenated `content` under-counts. Prefer the chat template when the tokenizer
defines one:

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", trust_remote_code=True)

messages = [
    {"role": "user", "content": "Summarize the report."},
    {"role": "assistant", "content": "The report covers ..."},
]

# tokenize=True returns token ids; length is the accurate per-example count
n = len(tok.apply_chat_template(messages, tokenize=True))
```

If the tokenizer has no chat template (some base, non-instruct checkpoints),
`apply_chat_template` raises. The bundled script catches this and falls back to
`tok.encode(" ".join(contents))`, which is an under-count but keeps the run
going. For text and instruction formats there is no template — plain `encode`
is the right call.

## trust_remote_code

Qwen and DeepSeek tokenizers require `trust_remote_code=True` because they ship
custom tokenizer code. Only enable it for repositories you trust.

## Gated models

Meta Llama tokenizers (and some others) are gated: accept the model license on
its Hugging Face page and set an access token before downloading.

```bash
export HF_TOKEN=hf_...          # or: huggingface-cli login
```

Without it, `from_pretrained` fails with a 401/403 for gated repos.

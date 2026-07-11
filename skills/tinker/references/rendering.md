# Rendering to Tokens

Renderers convert messages ↔ tokens for training and inference. **Never hand-build chat formats** —
use a renderer so tokens match the model's expected template exactly.

## Get a renderer

```python
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.renderers import get_renderer
from tinker_cookbook.tokenizer_utils import get_tokenizer

model_name    = "meta-llama/Llama-3.1-8B"
renderer_name = get_recommended_renderer_name(model_name)
renderer      = get_renderer(name=renderer_name, tokenizer=get_tokenizer(model_name))
```

**Renderer names:** `qwen3`, `qwen3_disable_thinking`, `qwen3_instruct`, `qwen3_vl`,
`qwen3_vl_instruct`, `llama3`, `deepseekv3`, `deepseekv3_thinking`, `kimi_k2`, `gpt_oss_no_sysprompt`,
`gpt_oss_low_reasoning`, `gpt_oss_medium_reasoning`, `gpt_oss_high_reasoning`, `role_colon`.

## HuggingFace compatibility

Default renderers emit **identical tokens** to HF `apply_chat_template`:

| Renderer | HF equivalent |
|----------|---------------|
| `qwen3` | `apply_chat_template(..., enable_thinking=True)` |
| `qwen3_disable_thinking` | `apply_chat_template(..., enable_thinking=False)` |
| `llama3` | `apply_chat_template(...)` (omits the "Cutting Knowledge Date" preamble) |
| `deepseekv3` | `apply_chat_template(...)` |

## Core methods

### build_supervised_example (training)

Returns `(model_input, weights)` — `weights` are 0.0 on prompt tokens, 1.0 on trained tokens.

```python
from tinker_cookbook.renderers import TrainOnWhat
model_input, weights = renderer.build_supervised_example(
    messages, train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES)
```

**Default is `LAST_ASSISTANT_MESSAGE`** if you omit `train_on_what` — always pass it explicitly.

### build_generation_prompt (inference)

```python
prompt = renderer.build_generation_prompt([
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "What is 2+2?"},
])   # -> ModelInput ready to sample
```

### get_stop_sequences / parse_response

```python
sampling_params = SamplingParams(max_tokens=100, stop=renderer.get_stop_sequences())
message, ok = renderer.parse_response(result.sequences[0].tokens)   # -> {"role": "assistant", "content": ...}
```

## TrainOnWhat

```python
TrainOnWhat.ALL_ASSISTANT_MESSAGES   # every assistant turn weighted 1
TrainOnWhat.LAST_ASSISTANT_MESSAGE   # only the final assistant turn weighted 1
```

Use `LAST` for classification, reward modeling, and preference learning where only the final answer
should be trained.

## Vision (multimodal)

Messages carry a `content` list of typed parts:

```python
messages = [
    {"role": "user", "content": [
        {"type": "image", "image": image_bytes},
        {"type": "text",  "text": "What's in this image?"}]},
    {"role": "assistant", "content": "A cat."},
]
```

Build a VLM renderer with an image processor:

```python
from tinker_cookbook.image_processing_utils import get_image_processor
from tinker_cookbook import renderers

model_name      = "Qwen/Qwen3-VL-235B-A22B-Instruct"
tokenizer       = get_tokenizer(model_name)
image_processor = get_image_processor(model_name)
renderer        = renderers.Qwen3VLInstructRenderer(tokenizer, image_processor)
prompt          = renderer.build_generation_prompt(messages)
```

## conversation_to_datum

One call from messages to a training `Datum`:

```python
from tinker_cookbook.supervised.data import conversation_to_datum
datum = conversation_to_datum(messages=messages, renderer=renderer,
                              max_length=2048, train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES)
```

`ChatDatasetBuilder` auto-creates `self.renderer` from `common_config`, so `map_fn` can call
`conversation_to_datum(..., renderer=self.renderer, ...)` directly.

## Troubleshooting

- **Wrong format** → use `get_recommended_renderer_name(model_name)`.
- **High loss** → verify weights (0.0 prompt, 1.0 completion).
- **Generation won't stop** → pass `renderer.get_stop_sequences()` into `SamplingParams`.

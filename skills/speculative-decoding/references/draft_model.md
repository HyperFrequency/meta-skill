# Draft-Model Speculative Decoding

Based on Leviathan et al. (ICML 2023) and Chen et al. (DeepMind, 2023). This is
the classic "small drafter verifies against large target" scheme that the
`transformers` `assistant_model=` path and vLLM `speculative_config` implement.

## Overview

**Idea**: Use a small, fast *draft* model to propose K candidate tokens, then
have the large, slow *target* model verify all K in a single parallel forward
pass. Accepted tokens are kept; the first rejection resamples from the target's
corrected distribution. The output distribution is provably identical to
sampling from the target model alone (zero quality loss).

## Algorithm

1. Draft model autoregressively generates K speculative tokens.
2. Target model evaluates all K tokens in one forward pass (parallel).
3. Accept each token where draft and target agree (modified rejection sampling).
4. On the first disagreement, reject and resample from the target distribution,
   then continue.

```python
def speculative_decode(target_model, draft_model, prompt, K=4):
    """Speculative decoding core loop (illustrative)."""
    # 1. Generate K draft tokens
    draft_tokens = draft_model.generate(prompt, max_new_tokens=K)

    # 2. Target model evaluates all K tokens in one forward pass
    target_logits = target_model(draft_tokens)  # Parallel!

    # 3. Accept/reject based on probability match
    accepted = []
    for i in range(K):
        p_draft = softmax(draft_model.logits[i])
        p_target = softmax(target_logits[i])

        # Acceptance probability: min(1, p_target / p_draft)
        if random.random() < min(1, p_target[draft_tokens[i]] / p_draft[draft_tokens[i]]):
            accepted.append(draft_tokens[i])
        else:
            break  # Reject -> resample from target's corrected distribution

    return accepted
```

**Performance**:
- Speedup: 1.5-2× with a well-matched draft model.
- Zero quality loss (mathematically equivalent to the target model).
- Best when the draft is 5-10× smaller than the target and shares its tokenizer.

## Choosing a Draft Model

The draft and target should share the **same tokenizer/vocabulary** and ideally
the same model family (so distributions correlate, raising the acceptance rate).

```python
def select_draft_model(target_model_size, target):
    """Heuristic: draft should be 5-10x smaller than the target."""
    if target_model_size == "70B":
        return "7B"   # 10x smaller
    elif target_model_size == "33B":
        return "7B"   # ~5x smaller
    elif target_model_size == "13B":
        return "1B"   # 13x smaller
    else:
        return None   # Target too small -> use Medusa/Lookahead instead

# Example: draft = select_draft_model("70B", target_model) -> "7B"
```

A higher draft/target agreement rate matters more than raw draft speed: a draft
that is fast but frequently rejected yields little net speedup.

## Hyperparameter Tuning

```python
# K = number of speculative tokens proposed per step
K = 4  # Good default
K = 2  # Conservative (higher per-token acceptance)
K = 8  # Aggressive (lower acceptance, but more tokens when accepted)

# Rule: Larger K -> more potential speedup IF the draft model is accurate.
# If acceptance is low, large K wastes draft compute.
```

## Hybrid: Medusa Heads as the Drafter

A Medusa-augmented small model can serve as the drafter, combining Medusa's
draft-free speed with a large target model's quality. See `medusa.md`.

```python
draft_medusa = MedusaModel.from_pretrained("medusa-vicuna-7b")
target_model = AutoModelForCausalLM.from_pretrained("vicuna-33b")

# Medusa proposes multiple candidates; target verifies in one forward pass.
outputs = target_model.generate(
    prompt,
    assistant_model=draft_medusa,
    max_new_tokens=256,
)
```

## Production Deployment (vLLM)

vLLM exposes speculative decoding through a `speculative_config` dict (the older
top-level `speculative_model=` / `use_v2_block_manager=` kwargs are deprecated;
verify the exact schema for your installed vLLM version before relying on it).

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-2-70b-hf",
    speculative_config={
        "model": "meta-llama/Llama-2-7b-hf",  # Draft model
        "num_speculative_tokens": 5,
    },
)

sampling_params = SamplingParams(temperature=0.7, max_tokens=256)
outputs = llm.generate(["Tell me about AI:"], sampling_params)
for output in outputs:
    print(output.outputs[0].text)
```

## When Draft-Model Speculative Is the Wrong Choice

- No smaller model with the same tokenizer exists -> use Medusa or Lookahead.
- Target model is already small (<7B): draft overhead can outweigh gains.
- Workload is throughput-bound at large batch sizes: speculative decoding helps
  latency at low batch sizes most; gains shrink as the batch saturates compute.

## Resources

- Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (ICML 2023): https://arxiv.org/abs/2211.17192
- Chen et al., "Accelerating LLM Decoding with Speculative Sampling" (DeepMind, 2023): https://arxiv.org/abs/2302.01318
- Transformers assisted generation: https://huggingface.co/docs/transformers/en/llm_optims
- vLLM speculative decoding: https://docs.vllm.ai/en/latest/features/spec_decode.html

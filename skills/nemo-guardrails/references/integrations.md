# Integration Guide

NeMo Guardrails ships a catalog of pre-built guardrails ("community" and
"library" rails) that you enable by adding their **flow names** to `config.yml`.
Most integrations are configured declaratively — you do not instantiate
integration classes in Python. Provider-specific settings go under `rails.config`.

## LlamaGuard (Meta content moderation)

Runs Meta's Llama Guard model as a separate moderation LLM. Declare it as an
extra model and enable the catalog flows:

```yaml
models:
  - type: main
    engine: openai
    model: gpt-4o
  - type: llama_guard
    engine: vllm_openai
    parameters:
      openai_api_base: "http://localhost:5123/v1"
      model_name: "meta-llama/LlamaGuard-7b"

rails:
  input:
    flows:
      - llama guard check input
  output:
    flows:
      - llama guard check output
```

Llama Guard is typically served via vLLM (or another OpenAI-compatible endpoint)
and returns a "safe"/"unsafe" verdict plus violated category codes.

## Presidio (PII detection & masking)

Uses Microsoft Presidio for entity detection and masking. Install the extra
(`pip install nemoguardrails[sdd]` plus a spaCy model) and enable the masking
flows:

```yaml
rails:
  input:
    flows:
      - mask sensitive data on input
  output:
    flows:
      - mask sensitive data on output
  retrieval:
    flows:
      - mask sensitive data on retrieval

  config:
    sensitive_data_detection:
      input:
        entities:
          - PERSON
          - EMAIL_ADDRESS
          - PHONE_NUMBER
          - US_SSN
          - CREDIT_CARD
```

Use the `mask sensitive data ...` flows to redact, or `detect sensitive data ...`
flows to block on detection.

## Built-in self-check rails

The fastest path to input/output safety needs no external model — just prompts:

```yaml
rails:
  input:
    flows:
      - self check input
  output:
    flows:
      - self check output
```

Provide the judging prompts in `prompts.yml` under `self_check_input` and
`self_check_output`. The optional `self_check_facts` and `self_check_hallucination`
rails verify output against the retrieved knowledge base.

## Other catalog integrations

- **ActiveFence** — managed toxicity/abuse moderation (`activefence moderation`).
- **Clavata** — policy checks (`clavata check input` / `clavata check output`).
- **Got It AI / Patronus / AlignScore** — hallucination and factuality checks.
- **Cleanlab** — trustworthiness scoring of LLM outputs.
- **Jailbreak detection** — heuristics + optional model server
  (`jailbreak detection heuristics`).

Each lives under the guardrails catalog; enable by flow name and add any
provider keys/endpoints under `rails.config`.

## Custom Python actions

For logic not covered by the catalog, register an action and call it from Colang:

```python
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.actions import action

@action()
async def check_input_toxicity(context: dict):
    user_message = context.get("user_message")
    return toxicity_detector(user_message) < 0.5  # True == safe

config = RailsConfig.from_path("./config")
rails = LLMRails(config)
rails.register_action(check_input_toxicity, name="check_input_toxicity")
```

## References

- Guardrails catalog: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html
- Llama Guard guide: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/community/llama-guard.html
- Presidio / sensitive data: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html#sensitive-data-detection

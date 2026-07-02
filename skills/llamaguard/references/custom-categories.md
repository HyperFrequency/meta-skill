# Custom Safety Categories

LlamaGuard's policy is supplied in the prompt, so you can constrain or extend
the active categories at inference time without retraining, and fine-tune for
fully domain-specific taxonomies.

## Prompt-level customization (no training)

The chat template injects the category definitions into the prompt. With
LlamaGuard 3 you can pass only the categories you care about via the
`categories` argument of `apply_chat_template`, which suppresses the rest:

```python
input_ids = tokenizer.apply_chat_template(
    conversation,
    categories={
        "S9": "Indiscriminate Weapons.",
        "S11": "Suicide & Self-Harm.",
    },
    return_tensors="pt",
)
```

This excludes (`excluded_category_keys`) or restricts the taxonomy so the model
only flags the hazards relevant to your product, reducing false positives on
content you intentionally allow.

## Standard taxonomies

- **LlamaGuard 1 (7B)** — 6 categories: S1 Violence & Hate, S2 Sexual Content,
  S3 Guns & Illegal Weapons, S4 Regulated Substances, S5 Suicide & Self-Harm,
  S6 Criminal Planning.
- **LlamaGuard 3 (8B)** — 14-category MLCommons taxonomy: S1 Violent Crimes,
  S2 Non-Violent Crimes, S3 Sex-Related Crimes, S4 Child Sexual Exploitation,
  S5 Defamation, S6 Specialized Advice, S7 Privacy, S8 Intellectual Property,
  S9 Indiscriminate Weapons, S10 Hate, S11 Suicide & Self-Harm,
  S12 Sexual Content, S13 Elections, S14 Code Interpreter Abuse.

## Fine-tuning for new domains

For categories outside the built-in taxonomy (e.g. financial-advice compliance,
medical misinformation), fine-tune the base model:

1. **Build a labeled dataset** of `(conversation, safe/unsafe, category)` rows
   that follow LlamaGuard's exact output format (`safe` or `unsafe\n<key>`).
2. **Define the new category keys and descriptions** and embed them in the
   training prompt so the model learns to ground its verdict in the policy text.
3. **Train with LoRA/QLoRA** (PEFT) on top of `meta-llama/Llama-Guard-3-8B` to
   keep memory low (INT4 QLoRA fits ~4GB VRAM); full fine-tune only if you have
   a large, high-quality dataset.
4. **Validate** on a held-out set per category — watch for regressions on the
   original taxonomy, since fine-tuning can shift the base behavior.

Keep the output schema identical to stock LlamaGuard so downstream parsing
(`result.startswith("unsafe")` and `result.split("\n")[1]`) keeps working.

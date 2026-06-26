# Pine Language Tooling Verification Checklist

Use the lightest check that can prove the claim. Record commands and artifacts when the answer depends on runtime behavior.

## Always Check

- Current branch and dirty files before editing.
- Whether the target path is inside the parent repo or a nested repo/submodule.
- Whether the relevant deep-tool-wiki or KB page exists before citing it as complete.
- Whether current docs are needed for third-party API/version claims.

## Pine Conversion Checks

- Check the parser/tokenizer, semantic core, language service, LSP server, and host adapter as separate layers.
- Do not fix an adapter symptom until a parser/core fixture proves the language behavior.
- Confirm zero-based LSP ranges, UTF-16 character offsets, and file URI normalization when diagnostics move.
- Run parser/LSP diagnostics before semantic conversion claims.
- Preserve source Pine behavior, timeframe assumptions, and order execution semantics.
- For PineTS/OpenAlgo conversion, treat `strategy.*`, `request.*`, `varip`, and broker/fill semantics as explicit limitations unless tested.
- Split syntax translation, vectorized validation, and event-driven validation into separate stages.

# Colang DSL Guide

Colang is the modeling language NeMo Guardrails uses to define rails (flows). Two
syntaxes coexist: **Colang 1.0** (mature, default in most examples) and **Colang
2.0** (newer, `colang_version: "2.x"` in `config.yml`). Pick one per config — they
do not mix.

## Project layout

A guardrails configuration is a directory, loaded with
`RailsConfig.from_path("./config")`:

```
config/
  config.yml        # models, rails wiring, options
  rails/*.co        # Colang flow definitions
  actions.py        # optional custom Python actions
  kb/               # optional knowledge base for fact-checking/RAG
```

You can also inline everything with `RailsConfig.from_content(yaml_content=..., colang_content=...)`.

## Colang 1.0 core constructs

- `define user <intent>` — canonical form for user messages, with example
  utterances used for embedding-based intent matching.
- `define bot <intent>` — canonical bot responses, with one or more example
  messages (one is chosen / paraphrased at runtime).
- `define flow <name>` — an ordered sequence of user/bot turns and logic.
- `define subflow <name>` — a reusable flow invoked with `do <subflow>`.

```colang
define user express greeting
  "hello"
  "hi there"

define bot express greeting
  "Hello! How can I help?"

define flow greeting
  user express greeting
  bot express greeting
```

### Variables, branching, actions

- `$var = execute <action_name>` runs a registered Python action.
- `if`/`else`, `when`, and `stop` control flow.
- `...` matches "anything" (used as `user ...` to catch any input).

```colang
define flow self check input
  user ...
  $allowed = execute self_check_input
  if not $allowed
    bot refuse to respond
    stop
```

## Colang 2.0 core constructs

Colang 2.0 replaces `define flow` with `flow`, uses `import` for standard
libraries (`core`, `llm`, `guardrails`, `avatars`), `await` for actions/flows,
`activate` to start background flows, and `abort` instead of `stop`.

```colang
import core
import llm
import guardrails

flow main
  activate llm continuation
  activate greeting

flow greeting
  user said "hi" or user said "hello"
  bot say "Hello world!"

flow input rails $input_text
  $input_safe = await check user utterance $input_text
  if not $input_safe
    bot say "I'm sorry, I can't respond to that."
    abort

flow check user utterance $input_text -> $input_safe
  $is_safe = ..."Is '{$input_text}' appropriate? Answer True or False."
  return $is_safe
```

The `...` "LLM prompt" syntax (`$x = ..."<instruction>"`) issues a direct LLM
call and is unique to Colang 2.0.

## Wiring rails in config.yml

Flows are activated by listing their names under the `rails` section. NeMo runs
them at the input, output, and (for RAG) retrieval stages:

```yaml
models:
  - type: main
    engine: openai
    model: gpt-4o

rails:
  input:
    flows:
      - self check input
  output:
    flows:
      - self check output
  retrieval:
    flows:
      - check retrieval
```

## Tips

- Intent matching is embedding-based; provide 3-5 varied example utterances per
  `define user` block for robust coverage.
- Keep dialog flows small and composable; push imperative logic into Python
  actions (`actions.py`) rather than large Colang branches.
- Use `colang_version: "2.x"` in `config.yml` to opt into Colang 2.0; otherwise
  1.0 is assumed.

## References

- Colang 1.0 language reference: https://docs.nvidia.com/nemo/guardrails/latest/colang-language-syntax-guide.html
- Colang 2.0 docs: https://docs.nvidia.com/nemo/guardrails/latest/colang-2/overview.html

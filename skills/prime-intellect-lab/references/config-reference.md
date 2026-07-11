# Configuration Reference

RL training runs are described by a `.toml` file passed to `prime rl run`. Confirm
the current field set with `prime rl --help`; the fields below reflect the common
schema.

## Full field reference

```toml
# ---- Top-level (required unless noted) ----
model = "Qwen/Qwen3-4B-Instruct-2507"   # base model from the supported list
max_steps = 200                          # total training steps
batch_size = 16                          # prompts per batch
rollouts_per_example = 8                 # completions per prompt = GRPO group size

[sampling]                               # rollout generation controls
temperature = 0.7                        # higher = more exploration (0.6-1.0)
top_p = 0.95                             # nucleus sampling
max_tokens = 2048                        # max output tokens per rollout

# ---- Environments: ALWAYS [[env]] (double brackets) ----
# This is TOML array-of-tables syntax. A single [env] block will NOT be parsed
# as an environment and the run will behave as if no env were configured.
[[env]]
id = "primeintellect/alphabet-sort"      # environment ID (owner/name), required
args = { min_turns = 3, max_turns = 5 }  # environment-specific arguments

[wandb]                                  # optional but recommended
project = "my-project"
name = "run-name"
enabled = true
# entity = "my-team"                     # optional W&B team/org

[eval]                                   # periodic eval during training
interval = 50                            # eval every N steps
n_samples = 100                          # eval examples per checkpoint
```

The single most common configuration bug is writing `[env]` instead of `[[env]]`.
Environment `args` must match the parameters that specific environment accepts —
check the environment's own documentation or `prime env` output.

## Size presets

Copy one preset into the top-level fields. Runtimes are order-of-magnitude only
and depend on model size, environment, and queue.

```toml
# SMALL — quick iteration / prototyping (low cost)
max_steps = 50
batch_size = 8
rollouts_per_example = 4

# MEDIUM — solid training
# max_steps = 200
# batch_size = 16
# rollouts_per_example = 8

# LARGE — full training
# max_steps = 1000
# batch_size = 32
# rollouts_per_example = 16
```

## Multi-environment training

Add multiple `[[env]]` blocks with `weight` to co-train across tasks. Weights set
the sampling mix; they need not sum to 1.0 but are easiest to reason about when
they do.

```toml
model = "Qwen/Qwen3-30B-Instruct-2507"
max_steps = 500
batch_size = 256
rollouts_per_example = 8

[[env]]
id = "primeintellect/gsm8k"
weight = 0.5

[[env]]
id = "primeintellect/alphabet-sort"
weight = 0.3

[[env]]
id = "primeintellect/reverse-text"
weight = 0.2

[sampling]
max_tokens = 512
```

# Training Workflow — Detailed Commands

Verify flags against `prime <subcommand> --help`; the CLI evolves. Every command
below assumes you have run `prime login` and `prime lab setup` in the workspace.

## 1. Install an environment

```bash
prime env list                              # browse the Environments Hub
prime env install primeintellect/alphabet-sort
```

## 2. Baseline evaluation (do this before training)

Establish a pre-training number so any gain is measurable and falsifiable.

```bash
prime eval run primeintellect/alphabet-sort \
  -m Qwen/Qwen3-4B-Instruct-2507 \
  -n 20 \       # number of eval examples
  -r 1          # rollouts per example
```

## 3. Launch training

```bash
# Hosted — managed infrastructure
prime rl run configs/rl/alphabet-sort.toml

# Self-hosted — your own GPUs (requires `prime lab setup --prime-rl`)
uv run prime-rl configs/prime-rl/wiki-search.toml
```

Before an expensive run, project the spend (verify the exact flag with
`prime rl --help`):

```bash
prime rl estimate --config configs/rl/alphabet-sort.toml
```

## 4. Monitor

```bash
prime rl status                # current run state
prime rl status --verbose      # detail when a run is stuck "pending"
prime rl logs --follow         # stream logs
# plus the W&B dashboard if [wandb] enabled = true
```

## 5. Review and export

```bash
prime rl list                                  # completed runs
prime rl download <run-id> --output ./adapter  # pull the LoRA adapter
prime rl cancel <run-id>                        # stop a run

# Post-training eval — prove the gain against the baseline from step 2.
# Use the SAME base model the adapter was trained on (here, the step-2 model);
# a LoRA adapter is only valid on its own base, so comparing against a
# different base would make the baseline delta meaningless.
prime eval run primeintellect/alphabet-sort \
  -m Qwen/Qwen3-4B-Instruct-2507 \
  --adapter ./adapter \
  -n 100
```

## Recommended sequence for a fresh task

1. `prime env list` → pick the environment closest to the task.
2. `prime env install <env>`.
3. Baseline eval with a small model (step 2).
4. Copy a size preset from `config-reference.md`; start SMALL.
5. `prime rl estimate` → present cost → get approval.
6. `prime rl run` → `prime rl logs --follow`.
7. Download the adapter, re-eval with `--adapter`, compare to baseline.

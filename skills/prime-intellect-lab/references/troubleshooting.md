# Troubleshooting and Command Quick-Reference

## Common failure modes

**`ModuleNotFoundError: No module named 'prime'`**
```bash
uv tool install prime        # recommended
# or, inside a virtualenv:
pip install prime
```

**Authentication failed**
```bash
prime login                  # or: prime config set-api-key
```
Confirm the key is present without printing it:
`[ -n "$PRIME_API_KEY" ] && echo set || echo missing`.

**Reward stuck at 0.0** — the rubric never fires or the model can't produce valid
outputs. Test the rubric alone: `prime eval run <env> -m <model> -n 10`. Verify
the model can format outputs the rubric parses, raise `sampling.temperature`
slightly, and check the environment `args` are correct.

**Reward stuck at 1.0** — the task is too easy, or the rubric always returns 1.0.
Use a harder environment / tighter constraints, and re-inspect the reward
function.

**`pydantic` version errors** — `prime` needs pydantic v2. Build a clean env:
```bash
python3.12 -m venv ~/prime-env && source ~/prime-env/bin/activate
pip install prime verifiers
```

**Model not available** — `prime models list` for the current supported set.

**Training OOM** — reduce `batch_size`, `rollouts_per_example`, or
`sampling.max_tokens`; drop to a smaller model for the first pass.

**Run stuck in "pending"**
```bash
prime rl status --verbose
prime rl cancel <run-id>
```

**Environment `args` not taking effect** — you almost certainly wrote `[env]`
instead of `[[env]]` (TOML array-of-tables). Args must also match the
environment's expected parameters.

## Command quick-reference

| Command | Description |
| --- | --- |
| `prime login` | Authenticate |
| `prime config view` | Show current configuration |
| `prime config set-api-key` | Manually set the API key |
| `prime models list` | List supported models |
| `prime env list` | List Hub environments |
| `prime env install <id>` | Install an environment |
| `prime eval run <env> -m <model>` | Run an evaluation |
| `prime rl run <config.toml>` | Launch hosted RL training |
| `prime rl estimate --config <toml>` | Project run cost (verify flag) |
| `prime rl status [--verbose]` | Check run status |
| `prime rl logs --follow` | Stream training logs |
| `prime rl list` | List completed runs |
| `prime rl download <id> --output <dir>` | Download the LoRA adapter |
| `prime rl cancel <id>` | Cancel a run |
| `prime gepa run <config.toml>` | Run GEPA prompt optimization |
| `prime lab setup [--prime-rl]` | Initialize a Lab workspace |
| `prime compute availability` | Check GPU availability |
| `prime compute provision` | Provision GPU pods |
| `prime compute delete <pod-id>` | Tear down a pod |

Flags drift between CLI versions — when a command errors on an unknown flag,
check `prime <subcommand> --help`.

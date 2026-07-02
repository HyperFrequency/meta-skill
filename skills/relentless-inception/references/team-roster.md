# Team roster

This skill spawns a typed cast of subagents. Defaults come from `agents/` files; the
user's spec in the parent monorepo's `docs/SPEC-original.md` is the source of truth for
any role tuning. Models all run at 1M-context variants; effort flags route through
codex/openrouter.

| Role                       | Default model            | Default effort   | When fired                                                       |
|----------------------------|--------------------------|------------------|------------------------------------------------------------------|
| `planner`                  | opus-latest              | xhigh            | every plan-mode entry; pairs with architecture-analyzer          |
| `architecture-analyzer`    | gpt-pro-latest (router)  | xhigh            | inverse-engineers similar codebases via git-nexus                |
| `dev-worker`               | opus-latest              | high             | per-unit build inside worktrees                                  |
| `adversarial-review`       | gpt-5.5 (router)         | high (xhigh rescue) | every plan + phase + summarization gate                          |
| `nexus-graph-writer`       | opus-4.7                 | high             | writes graph artifacts inline as work proceeds                   |
| `nexus-graph-synthesizer`  | gpt-latest (router)      | xhigh            | folds parallel graph writes into a coherent view                 |
| `uv-dagger-deploy`         | opus-latest              | high             | builds + ships via Dagger pipelines                              |
| `uv-package`               | opus-latest              | high             | turns workspace members into installable wheels                  |
| `uv-workspaces`            | opus-latest              | high             | workspace-level fixes (members, sources, lockfile)               |
| `test-harness-designer`    | gpt-5.5 (router)         | xhigh            | designs simulated-user personas + scenarios + assertions         |
| `temporal-tester`          | opus-4.7                 | high             | drives Temporal workflows + Temporal-gated integration tests     |
| `test-evaluator`           | opus-4.7                 | xhigh            | reads outputs, decides pass/fail against acceptance criteria      |
| `background-agent`         | codex-latest             | medium           | watches for stalls, drives the rescue path                       |
| `rescue-agent`             | gpt-latest (router)      | xhigh            | fresh context, reads full session log, repairs the harness       |

Read `agents/<role>.md` for the prompt template each role uses. Each file is
self-contained so the orchestrator can dispatch without re-deriving instructions.
`agents/<role>.md` files are loaded per-spawn; the orchestrator doesn't read them all up
front.

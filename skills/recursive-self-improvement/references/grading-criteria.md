# Grading criteria — what "good" looks like per target type

Graders score each target on the criteria below. Scores are 0–10; every
score must be backed by at least one resolvable log citation (see
`consortium-protocol.md` → Validation gates).

## Orchestrator (`/neuro-link` dispatcher)

- **Routing correctness** — did each request reach the right subcommand?
  Penalize misroutes and silent fallbacks.
- **Tool-choice quality** — was the chosen tool the cheapest one that
  could satisfy the request? Penalize reaching for heavy tools when a
  symbolic/cached lookup would do.
- **Output-contract adherence** — did the dispatcher return the declared
  schema (status, artifact paths) so downstream skills can chain?

## Downstream skills (`neuro-scan`, `neuro-surgery`, etc.)

- **Completion rate** — fraction of invocations that reached a terminal
  success state vs. abandoned/looped.
- **HITL-protocol adherence** — did the skill stop at the gates it is
  required to stop at, and never write to `02-KB-main/` or
  `03-Ontology-main/` without approval?
- **Log hygiene** — append-only, timestamped, every significant action
  recorded so the next grading cycle can audit it.

## Learning grade (did yesterday's change help?)

- **Metric movement** — the change must move the specific metric it
  claimed it would, measured A/B (invocations before vs. after the change).
- **No regressions** — adjacent metrics did not degrade.
- **Attribution** — the movement is plausibly caused by the change, not
  by an unrelated shift in workload.

## Per-executor-target acceptance bar

These mirror the Phase 4 executor table in `SKILL.md`.

| Target type | "Good" means |
|---|---|
| Agent topology | Edit is schema-valid for `03-Ontology-main/agents/by-agent/<name>.md`; cross-links to other agents still resolve. |
| Workflow ontology | Node/edge changes keep the workflow graph acyclic where required; no orphaned nodes. |
| Skill body | Frontmatter stays valid (name matches dir, version present, description ≤1024 with WHEN/WHEN-NOT); disclosure stays lean. |
| Prompt template | Variables referenced by the prompt still exist; tone/contract unchanged unless that was the change. |
| Config knob | Only the named frontmatter key in `config/neuro-link.md` changed; body untouched. |

A proposal that cannot state its acceptance bar in these terms is too
vague and is rejected back to the grader.

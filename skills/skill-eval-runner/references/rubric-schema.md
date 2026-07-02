# Rubric schema — reading and versioning `rubric-v1.json`

The rubric is a **released artifact**, not a comment in a workflow. It has its own
SemVer, its own file, and every scorecard is stamped with the version that graded
it. This is the whole point of the skill: make THE FRONTIER AGENT-SKILL RUBRIC —
which today lives only implicitly in meta-skill heal runs and git history —
explicit, machine-readable, and diffable.

## File layout

`references/rubric-v1.json` is the v1 release. Top-level keys:

| Key | Meaning |
|-----|---------|
| `rubric_id` | Stable identifier: `frontier-agent-skill`. Never changes across versions. |
| `rubric_version` | SemVer of *this* rubric release (independent of the skill's own `version`). |
| `scale` | `{min:0, max:5}` — the per-dimension scoring range. |
| `pass_threshold` | `4` — a dimension at or above this passes. |
| `pass_rule` | Prose statement of the gate: `min(all dimension scores) >= pass_threshold`. **No averaging.** |
| `dimensions[]` | The five graded dimensions, in `ordinal` order. |
| `scorecard_contract` | The shape `eval_skill.py` emits and `gate.py` consumes. |

### Dimension record

Each `dimensions[]` entry has:

- `id` — machine key (`format`, `depth`, `completeness`, `structured_disclosure`,
  `frontier_guidelines`). Scripts key on this; do not rename in a MINOR/PATCH bump.
- `ordinal`, `title` — human ordering and label.
- `auto_scorable` — `true` (FORMAT), `false` (judged), or `"partial"`
  (STRUCTURED DISCLOSURE: size is auto, the rest is judged).
- `criteria` — the one-sentence definition.
- `checks[]` — sub-criteria, each with `id`, `auto` (`true`/`false`/`"heuristic"`),
  `severity` (`hard`/`soft`), and a `desc`. Hard-check failures cap a dimension at
  2; soft weaknesses cap it at 4. Some checks carry a bound (`max_chars: 1024`,
  `target_bytes: 12288`) that the deterministic pass reads directly.
- `anchors` — calibrated descriptions for scores 5/4/3/2/0. The judge picks the
  anchor that matches reality; the FORMAT auto-scorer mirrors these bands
  deterministically in `eval_skill.py::_score_format`.

## The pass rule, precisely

```
PASS  ⇔  every dimension score >= 4
FAIL  ⇔  any dimension score < 4
```

A single 3 fails the whole skill even if the other four are 5. This is
intentional: a skill with brilliant depth but a broken trigger routes wrong, and
a skill with a perfect router but shallow content wastes the model's time. The
weakest dimension is the skill's real quality.

## Versioning the rubric

Bump `rubric_version` under SemVer, keyed to how a bump changes *scores of
already-graded skills*:

- **PATCH** (`1.0.0 → 1.0.1`) — wording/typo fixes, clearer anchor prose, a new
  `desc` that does not change how anything scores. Baselines stay valid; no
  re-grade needed.
- **MINOR** (`1.0.x → 1.1.0`) — a new *soft* check, or a tightened heuristic that
  can only *lower* borderline scores. Re-grade is advisable but old baselines
  remain comparable within a dimension. Re-baseline opportunistically.
- **MAJOR** (`1.x → 2.0.0`) — a new dimension, a removed/renamed dimension, a
  changed `pass_threshold`, or a hard-check change that moves many scores. This
  is a new rubric: ship it as **`references/rubric-v2.json`** (keep v1 on disk so
  old scorecards stay interpretable), point the scripts' `RUBRIC_PATH` at it, and
  **re-baseline every gated skill**. The `gate.py` version guard will refuse to
  compare a v2 scorecard against a v1 baseline.

Rule of thumb: **if a bump could turn a green skill red, it is MAJOR.** Do not
tighten a hard check inside `rubric-v1.json` in place — that silently invalidates
every committed baseline. Cut a new version file instead.

## Adding `rubric-v2.json` without breaking baselines

1. Copy `rubric-v1.json` → `rubric-v2.json`, set `rubric_version: "2.0.0"`, make
   the change.
2. Update `RUBRIC_PATH` in `scripts/eval_skill.py` (and the doc references) to the
   new file. Leave v1 on disk.
3. Re-grade each gated skill under v2 and replace its baseline. Until then, the
   gate's version guard skips regression checks for that skill and warns.
4. Note the change in this file's history so the diff between rubric versions is
   auditable.

## Why not just average the five scores?

Averaging hides exactly the failures the rubric exists to catch: a 5/5/5/5/**2**
averages to 4.4 and would "pass," shipping a skill with a misleading trigger or
an invented API. The `min` rule makes every dimension a veto — which is what
"frontier" means here.

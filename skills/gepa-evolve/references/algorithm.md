# GEPA algorithm — concepts and paper→code mapping

Source: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning", arXiv 2507.19457
(ICLR 2026 Oral). Rust implementation: `gepa` crate at `~/neuro-centrifuge-repos/gepars`.

## The one-paragraph mental model

Reinforcement-learning prompt tuning (GRPO and friends) treats the score as a scalar reward and pushes
the model with thousands of rollouts. GEPA instead treats each **failure as text to reflect on**: it
shows a teacher LM the inputs, the current instruction, the produced outputs, and feedback, then asks
the teacher to **rewrite the instruction**. Because a single good reflection can encode a lesson that
RL would need many gradient steps to learn, GEPA reaches comparable or better quality with **up to ~35x
fewer rollouts** and **+6% average** over GRPO in the paper. The second idea is **diversity**: instead
of keeping one average-best prompt, GEPA keeps, *for every validation example*, the candidate that does
best on it (the per-instance Pareto front). Specialists survive, and a later **merge** step recombines
their complementary strengths.

## Why a Pareto front (not just argmax)

A single "best average" prompt is a local optimum: it may be mediocre-everywhere while a rejected
candidate was the *only* one that solved a hard cluster. GEPA's **instance-level frontier**
(`FrontierType::Instance`, the paper's default, Algorithm 2) records, per validation example, the set
of candidate indices achieving the top score there. Selecting a base candidate from this frontier
(weighted by how many instances it wins) keeps exploration anchored to genuinely useful specialists
and preserves the material that `merge` later fuses. This is the structural reason GEPA outperforms a
plain keep-if-better hill-climb (which is exactly what `neuro-code/prompt-optimize` does).

## The three algorithms the crate implements

- **Algorithm 2 — Pareto candidate selection.** `ParetoCandidateSelector`: sample a base candidate
  from the instance frontier, frequency-weighted. Alternatives: `CurrentBestSelector` (pure exploit),
  `EpsilonGreedySelector` (exploit `CurrentBest` w.p. `1−ε`, else random).
- **Algorithm 3 — Reflective mutation.** `ReflectiveMutationProposer`: select component(s) to update
  (`RoundRobin` advances one per iteration; `All` updates every component), sample a minibatch,
  evaluate **with traces**, build a reflective dataset, and prompt the reflection LM with the
  Appendix-C meta-prompt to produce a rewritten component. The child is accepted only if its summed
  minibatch score beats the parent's.
- **Algorithm 4 — System-aware merge.** `MergeProposer` (`use_merge = true`): periodically take two
  complementary Pareto candidates and build a child by picking, per component, the version that
  performs best on shared validation instances. Gated by `max_merge_invocations` and
  `val_overlap_floor` (minimum shared validation IDs before a merge is attempted).

## Reflective mutation — the meta-prompt

The built-in teacher prompt (`META_PROMPT_TEMPLATE`, the paper's Appendix C) has two slots:

- `<curr_param>` — the current component text.
- `<side_info>` — the reflective dataset (input/output/feedback records) rendered as markdown.

It instructs the teacher to infer the task from the inputs, harvest domain-specific facts and
generalizable strategies from the feedback, and emit a new instruction inside a fenced block. Component
**kind** swaps the template: `ComponentKind::Text` → `META_PROMPT_TEMPLATE`; `Code` →
`CODE_META_PROMPT_TEMPLATE` (targeted edits, preserve syntax); `Config` → `CONFIG_META_PROMPT_TEMPLATE`
(key-value / numeric-range aware). Set kind via `component_metadata` (see adapter-guide). Override
entirely with `reflection_prompt_template` (`PromptTemplateConfig::Single` or `PerComponent`).

## Rollout accounting — where the ~35x comes from

"Rollout" = one per-example metric evaluation. GEPA is frugal because:

- It reflects on a **minibatch** (`minibatch_size`, default 3), not the whole trainset, per iteration.
- It only pays for a **full valset evaluation** when a mutation is *accepted*.
- With `cache_evaluation = true`, repeated (candidate, example) pairs are free and do not consume
  `max_metric_calls`.
- `skip_perfect_score` skips reflection when the whole minibatch already hits `perfect_score`.

The budget you set (`max_metric_calls`) is denominated in these per-example calls, which is the same
unit the paper counts — so the 35x comparison is apples-to-apples against GRPO rollouts.

## When the sample-efficiency claim holds (and when it doesn't)

- **Holds** when the score exposes *diagnosable* structure — the reflection LM can read failures and
  articulate a fix (reasoning tasks, extraction, classification with explainable errors).
- **Weakens** when the metric is nearly random or gives no textual signal to reflect on (pure
  preference noise), when the valset is too small to define a meaningful frontier, or when a single
  instruction genuinely cannot express the needed behavior (then you need code evolution → alpha-evolve,
  or model training).

## Relation to the sibling skills

- `neuro-code/prompt-optimize` — single scalar metric, one edit/round, keep-if-better, **no** reflection
  LM and **no** Pareto front. GEPA is a strict superset in machinery; use prompt-optimize when you want
  the lighter loop and don't need diversity or multi-objective trade-offs.
- `neuro-code/alpha-evolve` — evolves **runnable program/model code** as SEARCH/REPLACE diffs in a
  MAP-Elites archive across islands. Different artifact (code, not prompt text) and different diversity
  mechanism (behavioral archive vs. per-instance Pareto). Use it when the thing that must change is
  code that executes, not instruction text.

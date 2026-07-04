# Bandit suggestions (behavioral spec)

The suggestion engine ranks which skills to surface by **learning, per signal,
how much that signal predicts a *useful* skill load** — a multi-armed bandit over
ranking signals, rewarded by real outcomes. In neuro-centrifuge this is the D12
loop-4 skill-selection learner. Clean-room; constants are parity targets.

## The 8 arms (`SignalType`)

Each arm is one ranking signal whose weight the bandit tunes:

1. **Bm25** — lexical relevance of the query to the skill.
2. **Embedding** — semantic (hash-embedding) relevance.
3. **Trigger** — match against the skill's declared trigger phrases.
4. **Freshness** — recency / update time of the skill.
5. **ProjectMatch** — skill's project-type affinity vs the detected project.
6. **FileTypeMatch** — match against file types in the working context.
7. **CommandPattern** — match against recent command patterns.
8. **UserHistory** — the user's own prior use of the skill.

`SignalType::all()` enumerates exactly these eight, in this order. The bandit
learns a **weight per arm**; final skill ranking is the signal scores combined by
the learned `SignalWeights` (which normalize to sum 1.0 over the eight arms).

## Learning: Thompson (Beta) + UCB bonus

Each `BanditArm` holds a **Beta distribution** (`α`, `β`) plus a decay factor and
a running UCB estimate. Two mechanisms combine:

- **Thompson sampling.** To pick weights, sample each arm's success probability
  from its `Beta(α, β)` and rank/weight by the samples. The RNG is explicit and
  seedable — this is the *only* stochastic component of the whole engine.
- **UCB exploration bonus.** On `update(signal, reward, context)` the arm records
  the observation and recomputes:

  ```
  bonus = sqrt( ln(total_observations) / arm_observations ) * exploration_factor
  ucb   = clamp( estimated_prob + bonus, 0.0, 1.0 )
  ```

  with `exploration_factor = 0.1` by default (`BanditConfig`). Arms with few
  observations get a larger bonus, so under-tried signals still get explored.

`observe(reward, prior)` updates the Beta parameters toward success/failure with
a configurable **decay factor** so old evidence fades (nonstationarity: what
predicts a good skill drifts as the library and the user change). Reward is the
binary `Reward::{Success, Failure}` at the bandit boundary, derived from a richer
feedback signal (below).

The bandit state is **persisted** (`save`/`load` to a path) so learning survives
across sessions.

## Rewards from real outcomes (`SkillFeedback`)

`compute_reward(feedback) -> f32 ∈ [0,1]` turns an observed outcome into a scalar
that maps onto Success/Failure at the arm boundary:

| Feedback | Reward |
|---|---|
| `ExplicitHelpful` | 1.0 |
| `UsedDuration { minutes > 5 }` | 0.8 |
| `UsedDuration { minutes 0..=5 }` | 0.4 + (minutes/5)·0.4 (scales 0.4→0.8) |
| `LoadedOnly` (minimal interaction) | 0.3 |
| `Ignored` (suggested, not loaded) | 0.1 |
| `NotHelpful` / quick-unload | 0.0 |
| `Rating { 1..=5 }` | scaled from the star rating |
| `TaskCompleted { success, time }` | outcome-derived |

The design principle: **reward what actually got used successfully**, not what
merely got surfaced. This closes the loop the frontier-rubric class-1 gate cares
about — a skill that "passes" the rubric but is never usefully loaded accrues
low reward and gets down-ranked (and flagged to loop-4 for heal/retire).

A **cooldown** layer (`cooldown` / `cooldown_storage`) prevents the same skill
from being re-suggested too frequently regardless of its arm weights.

## Contextual variant (28-dim features)

Beyond the plain per-arm bandit, a **contextual** bandit conditions weights on a
`ContextFeatures` vector of **28 dimensions**:

- **Project type** one-hot — 18 dims.
- **Time** — cyclical `[hour_sin, hour_cos, day_sin, day_cos]` — 4 dims.
- **Activity** — `[files_ratio, tools_present, has_git]` — 3 dims.
- **History** — `[skill_frequency, recency, session_depth]` — 3 dims.

`UserHistory` (persisted per user) supplies `skill_frequency(id)` and
`skill_recency(id)` (both normalized `[0,1]`, higher recency = more recent) and
records each load. A `FeatureExtractor` trait builds the vector from the working
context + history; the contextual arms take a dot product of features with learned
weights. Cyclical time encoding avoids the midnight discontinuity a raw hour would
introduce.

## Wiring into neuro-centrifuge (loop-4)

- Bandit **outcome data validates that "passing" skills actually get used** —
  one of the class-1 meta-loop checks in the autoresearch spec.
- Low-reward or never-suggested skills are inputs to loop-4's DETECT step
  (uncovered/underperforming skills), alongside anti-pattern hits (loop-3) and
  trace mining.
- Priors are updated when a skill clears the loop-4 commit gate, so a freshly
  healed skill starts with an informed (not cold) prior.
- Rewards flow from harness telemetry (`SkillFeedback` derived from OTel spans +
  task outcomes), so the whole learner runs on first-party logs — no external
  feedback service.

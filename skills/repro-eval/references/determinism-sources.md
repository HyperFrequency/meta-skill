# Sources of nondeterminism — classifying a delta

A nonzero reproduction delta is a *symptom*, not a verdict. This file is the
taxonomy the gate uses to answer the core question after a `drifted` result:
**which provenance dimension leaked, and is this benign reproduction noise, a
provenance defect, or a real regression?** Work it as an elimination loop
(`anomaly-investigation`): each candidate below has a signature that either
implicates or exonerates it.

## The taxonomy

### 1. Provider sampling (the usual suspect)
- **Mechanism:** `temperature > 0`, `top_p < 1`, or a provider that ignores the
  `seed` param makes token sampling stochastic. Two runs of the same prompt
  differ legitimately.
- **Signature:** deltas cluster within the recorded variance band; the mean over
  `n ≥ 3` trials overlaps the recorded distribution.
- **Verdict:** **benign** if within band → `reproduced`. Only `drifted` if the
  *mean* shifts beyond the band.
- **Defect variant:** the record has **no** `provider_sampling_params` for a
  stochastic call → the run was never reproducible. Provenance defect: fix the
  logging, do not paper over it with a wide band.

### 2. Seed leaks
- **Mechanism:** a stochastic source (sampler, dataset shuffle, tie-break) was
  not seeded, or one global seed was used for multiple sources so restoring it
  does not restore all of them.
- **Signature:** deterministic-looking target (temp 0) still drifts; item order
  or tie-breaks differ between runs.
- **Verdict:** provenance **defect** — mark non-reproducible until each stochastic
  source is independently seeded and re-logged.

### 3. Model-version drift (external, not the harness's fault)
- **Mechanism:** the provider silently updated the model behind the same id since
  the original run.
- **Signature:** deltas persist even at `temperature = 0` with all seeds pinned
  and the ScriptedJudge control byte-identical (so the runner is proven clean);
  the shift correlates with a known provider release date.
- **Verdict:** **external drift** — annotate the original result as reproducible
  only under the pinned model snapshot; footnote any leaderboard entry. Not a
  harness regression, not a provenance defect. Prefer providers/records that pin
  a concrete model *snapshot* id so this is detectable rather than mysterious.

### 4. Cache replay mismatch
- **Mechanism:** the original run read/wrote an inference cache (tensorzero
  `CacheKey`, streaming chunk replay); the re-execution's cache mode differs, so
  it hits fresh model calls where the original replayed cached chunks (or vice
  versa).
- **Signature:** delta appears only for cache-eligible calls; disappears when the
  re-execution's cache mode matches the record's.
- **Verdict:** **runner-config defect** — re-execute with the recorded cache mode.
  If the record does not log its cache mode, that is a completeness defect.

### 5. Clock / RNG in workflow code (must be impossible if authored correctly)
- **Mechanism:** wall-clock reads or unsourced `rand` inside workflow (not
  activity) code make the run non-replayable.
- **Signature:** delta correlates with wall-time or is fully random across runs;
  a Temporal replay of the workflow history throws a nondeterminism error.
- **Verdict:** **hard defect in the experiment's authoring** — the harness bans
  this (lightspeed replay-safety: `workflow_time` only, no I/O in workflow code,
  `request_fingerprint` sha256; class 9 temporal-authoring gate). Route the fix
  to the workflow author; the experiment is void until it replays cleanly.

### 6. Tool nondeterminism
- **Mechanism:** a tool call hit a live, changing external resource (network
  fetch, time-varying data source) that was not captured/pinned.
- **Signature:** delta isolates to items whose trajectory shows the offending
  tool; the model layer is clean.
- **Verdict:** **provenance defect** — tool outputs must be captured in the
  trajectory/CAS and replayed, or the tool declared nondeterministic and its
  score component tagged `Believed` with a band. Live tools that cannot be pinned
  make the experiment reproducible only in distribution, not exactly.

### 7. Floating-point / ordering nondeterminism
- **Mechanism:** parallel reductions, hash-map iteration order, or non-associative
  float accumulation change low-order bits between runs/architectures.
- **Signature:** deltas are in the last few significant digits only; no semantic
  change.
- **Verdict:** **benign** — covered by the `Known`-class bit-tolerance in the
  delta gate. Only escalate if it crosses a decision threshold (e.g. flips a
  boolean assertion) — then treat as a real regression at that boundary.

## The elimination procedure

1. **Prove the runner first.** If the ScriptedJudge control drifted, stop — it is
   the runner (source 5-adjacent or a chassis bug), not the experiment.
2. **Isolate the layer.** Does the delta survive at `temperature = 0` with all
   seeds pinned? If yes → it is *not* sources 1–2; suspect 3 (model), 4 (cache),
   6 (tool), or 7 (float). If no → it is sampling/seed related (1–2).
3. **Localize by trajectory.** Diff the fresh vs recorded `.traj` trajectories:
   the first diverging step names the layer (a tool step ⇒ source 6; a model call
   with matched inputs but different output ⇒ source 3 or 1).
4. **Confirm one cause.** A reproduction root-cause is accepted only when exactly
   one source explains the delta and re-pinning it collapses the delta into
   tolerance (positive confirmation, not just elimination).
5. **Record the cause** as the `drifted` verdict's annotation, feeding the
   meta-class audit and any leaderboard footnote.

## The rule of thumb

- **Benign (→ `reproduced`):** sources 1 (in-band) and 7 (low-order) — inherent,
  bounded, declared.
- **Provenance defect (→ fix logging, re-log):** sources 2, 4, 6, and the missing-
  param variant of 1 — the record was incomplete; widening tolerance is never the
  fix.
- **External (→ annotate, footnote):** source 3 — real but outside the harness.
- **Real regression (→ hand to owning eval class):** delta survives full pinning
  and no source above explains it — the system under test genuinely changed.

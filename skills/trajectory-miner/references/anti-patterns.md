# Anti-pattern taxonomy & detectors

Each detector reads one session's normalized `TurnEvent[]` (see
`transcript-schemas.md`) and emits **incidents**:

```json
{
  "session_id": "…", "source": "claude|codex",
  "mode": "loop|error_cascade|rate_limit_stall|no_progress_stall|
           refusal|hallucinated_result|goal_drift|context_rot|truncation",
  "turn_range": [start_seq, end_seq],
  "signature": "normalized string for clustering",
  "severity": "low|med|high",
  "evidence": "minimal excerpt proving the incident"
}
```

Every incident MUST cite a `turn_range` that exists in the file. Thresholds
below are defaults — expose them so a caller can tune sensitivity per corpus.

---

## 1. Loop / repeated action  (`mode: loop`)
The agent re-runs the same call or re-emits the same output without progress.

- **Detector:** slide over `tool_call` events; count runs of identical
  `input_sig`. Flag when the *same* `input_sig` occurs `>= 3` times, OR an
  alternating cycle of 2–3 signatures repeats `>= 3` times (A,B,A,B,A,B).
- **Edit thrash:** `>= 3` `Edit`/`Write` calls to the same file path with no
  passing `tool_result` in between.
- **Signature:** `loop:{tool}:{input_sig}` (or the cycle's sorted sig set).
- **Severity:** high if the loop never breaks before session end; med if it
  self-recovers.

## 2. Tool-error cascade  (`mode: error_cascade`)
Consecutive failing tool calls — the agent is fighting the environment.

- **Detector (Claude):** run of `tool_result` with `ok=false`
  (`is_error:true`) of length `>= 3`, especially same `tool`.
- **Detector (Codex):** `function_call_output` whose `output` indicates failure —
  nonzero `exit_code`, non-empty `stderr`, or an `error`/`code` field — in a run
  of `>= 3`. Codex has no `is_error`; classify from the output payload.
- **Signature:** `error_cascade:{tool}:{normalized_error}` where
  `normalized_error` strips digits, paths, and hex so "file X not found" and
  "file Y not found" cluster together.
- **Severity:** high if the cascade ends the session; med otherwise.

## 3. Rate-limit / overload stall  (`mode: rate_limit_stall`)
Progress blocked by 429s / overload / retry backoff.

- **Detector:** `tool_result`/error text or assistant text matching
  `(?i)(rate.?limit|429|overloaded|quota|too many requests|retry.?after|
  temporarily unavailable|529)`. Corroborate with a **timestamp gap**: `ts`
  delta to the next event `> 60s` with no intervening tool activity.
- **Signature:** `rate_limit_stall:{provider_or_tool}`.
- **Severity:** med (environmental, not a reasoning failure) — but high blast
  radius if it recurs across many sessions.

## 4. No-progress / idle stall  (`mode: no_progress_stall`)
The run stops advancing without an error to blame.

- **Detector:** a `ts` gap `> N` (default 300s) between consecutive events with
  no `tool_call` since the last user turn; OR `>= 5` assistant turns in a row
  with zero `tool_call`/no file mutation while a task is open (talking, not
  doing). Distinguish from `rate_limit_stall` (which has the limit signature).
- **Signature:** `no_progress_stall:{last_tool_or_'none'}`.
- **Severity:** high if session ends stalled.

## 5. Refusal  (`mode: refusal`)
Model declines the task (real refusal, not a hedge mid-solution).

- **Detector:** `assistant_text` matching
  `(?i)^\W*(i'?m (sorry|unable|not able)|i (can'?t|cannot|won'?t) (help|assist|
  provide|do that|comply)|as an ai|i (must|have to) decline)` in a turn that
  produces **no** subsequent `tool_call` toward the goal. Anchor to line start /
  short messages to avoid matching "I can't reproduce the bug" mid-work.
- **Signature:** `refusal:{first_8_normalized_words}` (fuzzy-clustered later).
- **Severity:** high — a refusal usually kills the whole task.

## 6. Hallucinated / never-produced result  (`mode: hallucinated_result`)
The agent claims success/artifacts that the tool record does not support.

- **Detector:** `assistant_text` asserting completion —
  `(?i)(tests? (pass|are passing|green)|all (checks|tests) pass|created|wrote|
  saved|generated|successfully (ran|built|deployed)|done|✅)` — for which there
  is **no corroborating** `tool_result` with `ok=true` in a preceding window
  (e.g. claims "tests pass" but no test-runner `tool_call` ever ran; claims a
  file was written but no `Write`/`Edit` to that path). Also flag references to a
  file/path that never appears as the target of a successful write.
- **Signature:** `hallucinated:{claim_class}` (tests|file|build|deploy|generic).
- **Severity:** high — downstream turns build on a fabrication.
- **Caution:** this detector is the most false-positive-prone. Require the
  *absence* of corroboration within the window, and keep the excerpt so a human
  can confirm. When unsure, downgrade to `low` rather than drop.

## 7. Goal drift  (`mode: goal_drift`)
The agent ends up working on something other than the original ask.

- **Detector:** compare `goal_text` (first user turn) against the trailing 20%
  of the session's assistant/tool activity. Lexical proxy: token/keyword overlap
  (Jaccard on content words, or TF-IDF cosine) between goal and tail. Flag when
  overlap `< 0.1` **and** no intervening user turn redirected the task (an
  explicit user pivot is legitimate, not drift). Prefer embedding cosine when an
  embedder is available (see clustering doc).
- **Signature:** `goal_drift:{tail_topic_keywords}`.
- **Severity:** med–high depending on how far off.

## 8. Context rot  (`mode: context_rot`)
Related to drift but caused by lost/forgotten constraints, not a new topic.

- **Detector:** the agent re-asks for or re-derives information already
  established earlier in the same session (same question/file re-read `>= 3x`
  with no change), contradicts an earlier confirmed fact, or restates the goal
  incorrectly vs. `goal_text`. Long sessions (`> ~150` turns / near-context-limit
  token totals) with rising re-reads are the strong signal.
- **Signature:** `context_rot:{forgotten_entity}`.
- **Severity:** med.

## 9. Truncation / length cutoff  (`mode: truncation`)
Turn cut off by the token limit — often the trigger for rot/loops downstream.

- **Detector (Claude):** assistant line `stop_reason == "max_tokens"`, or a
  final assistant turn with high `usage.output_tokens` and no `end_turn`.
- **Detector (Codex):** `token_count` approaching the model window near a turn
  that ends without `task_complete`.
- **Signature:** `truncation:{tool_context}`.
- **Severity:** low on its own; note it as a **cause tag** on nearby loop/rot
  incidents rather than a headline mode.

---

## Detector hygiene

- **Windowing:** hallucination/drift/rot compare across turns — bound the
  look-back window (e.g. 40 events) so cost stays linear in session length.
- **Sidechains:** run detectors per `sessionId` but keep `is_sidechain` on each
  incident; a subagent's loop is a subagent-harness problem, report it distinctly.
- **Overlap:** one turn range can trip multiple detectors (a cascade that ends in
  a stall). Emit all incidents; the clustering step deduplicates and lets a
  cause tag (`truncation`, `rate_limit_stall`) annotate the primary mode.
- **Tuning:** every threshold (`>=3`, `300s`, `0.1`, `40`) is a knob. Report the
  values used in the run header so results are reproducible.

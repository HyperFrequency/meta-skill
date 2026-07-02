---
name: trajectory-miner
version: 0.1.0
description: "Batch scanner over a directory of LLM session transcripts (Claude Code *.jsonl, Codex rollout *.jsonl) or agent logs that mines for recurring ANTI-PATTERNS and FAILING TRAJECTORIES — loops, context rot, goal drift, hallucinated/never-produced results, tool-error cascades, rate-limit stalls, and refusals — clusters them, and emits a report of anti-patterns plus representative failing trajectories to feed harness improvement. Use when you have many past sessions/logs and want to find SYSTEMIC failure modes across the corpus, build a reflective dataset for prompt/harness evolution, or answer 'what keeps going wrong in my agent runs'. Do NOT use to rescue ONE live stuck node (use background-rescue), to run the improvement loop that consumes this report (use recursive-self-improvement / autonomous-orchestrator), or to debug a single known bug in one transcript — this is corpus-level, read-only mining, not a fix."
license: HyperFrequency original. Optional GEPA handoff wraps the MIT-licensed `gepa`/gepars crate.
---

# Trajectory Miner

Read a **corpus** of agent transcripts and surface the failure modes that recur
across it. You are a read-only miner: you parse many sessions, detect
anti-pattern *incidents*, cluster them into named failure modes, rank by
frequency and severity, and emit a report with representative failing
trajectories. You never edit the agent, never rescue a live run, and never
fabricate an incident the logs don't support.

The output feeds a *different* system — a harness-improvement loop, a reflective
prompt optimizer, or a human reviewer. Your job ends at the report.

## When to use vs. when not

Use this skill when:
- You point at a directory of `*.jsonl` transcripts (or agent logs) and ask
  "what keeps going wrong", "find recurring failures", "mine my sessions".
- You want a **reflective dataset** of failing trajectories to feed prompt/harness
  evolution (see `references/gepa-handoff.md`).
- You are triaging a benchmark run or an overnight autonomous run *after the fact*.

Do NOT use this skill for:
- **One live stuck node** — re-grounding a single diverged run is `background-rescue`.
- **Running the fix loop** that consumes this report — that is
  `recursive-self-improvement` (consortium-graded, HITL) or
  `autonomous-orchestrator` (harness hill-climbing).
- **Debugging one known bug in one transcript** — just read it; this is
  corpus-level statistics, not single-case debugging.

## Inputs

- `path` — a directory (scanned recursively) or a glob of transcript files.
- `format` — `claude` (Claude Code `~/.claude/projects/<slug>/<uuid>.jsonl`),
  `codex` (Codex `~/.codex/**/rollout-*.jsonl`), or `auto` (sniff per file).
- `since` / `until` — optional timestamp bounds to restrict the corpus.
- `min_support` — minimum incident count for a cluster to be reported (default 2;
  a one-off is noise, a pattern repeats).

Both transcript schemas — every field you parse — are documented in
`references/transcript-schemas.md`. Do not guess field names; they differ
sharply between the two formats.

## Procedure

Work in this order. Do not jump to clustering before the corpus is parsed and
normalized, or the clusters will be built on the wrong fields.

### 1. Enumerate and sniff the corpus
List every candidate file under `path`. For `format: auto`, sniff each file by
its first non-empty line: a Claude line has top-level `type` in
`{user,assistant,system,summary}`; a Codex line has top-level `type` in
`{session_meta,response_item,event_msg,turn_context}`. Skip files that parse as
neither. Record file count, total lines, and any unparseable files — report
them; never silently drop a whole session.

### 2. Normalize each session to a turn stream
Reduce each file to an ordered list of typed events: `user_text`,
`assistant_text`, `thinking`, `tool_call` (name + canonicalized input),
`tool_result` (ok/error + content), plus timestamps. The mapping from raw
blocks to this stream — including how tool errors, token counts, and stop
reasons surface in each format — is in `references/transcript-schemas.md`.
Capture the **first user turn** verbatim per session: it is the ground-truth
goal that drift and hallucination are measured against.

### 3. Detect anti-pattern incidents per session
Run the detectors in `references/anti-patterns.md` over each turn stream. Each
detector emits zero or more **incidents** anchored to a session id and a turn
range, with an `evidence` excerpt and a normalized `signature`. The taxonomy and
concrete heuristics (loop/cycle detection on tool-call signatures, error-cascade
runs, rate-limit/timestamp-gap stalls, refusal and hallucination regexes,
goal-drift scoring) live there. **Never invent an incident** — every one must
cite a turn range that actually exists in the file.

### 4. Cluster incidents into failure modes
Group incidents across sessions using the two-stage method in
`references/clustering-and-report.md`: first a deterministic bucket by
`(failure_mode, tool, normalized_signature)`, then optional embedding-based
merge for the fuzzy modes (refusals, drift) where surface text varies. Drop
clusters below `min_support`.

### 5. Rank and pick representatives
Score each cluster by frequency x severity x blast-radius (sessions affected).
For each surviving cluster, select the single most representative failing
trajectory — the incident whose evidence most cleanly shows the mode — and cut a
minimal excerpt (goal + the diverging turns), not the whole session.

### 6. Emit the report
Write both a machine-readable `trajectory-report.json` and a human
`trajectory-report.md` using the schema in
`references/clustering-and-report.md`: per cluster, its name, count, severity,
affected sessions, one representative excerpt, and a recommended harness fix.
Do not apply the fix — hand the report off.

### 7. (Optional) Emit a reflective dataset
When the caller wants to *drive* prompt/harness evolution, also emit the failing
trajectories as GEPA reflective records (`{inputs, generated_outputs,
feedback}`) that the MIT `gepa`/gepars `ReflectiveMutationProposer` consumes.
Mechanics and the exact record shape are in `references/gepa-handoff.md`.

## Boundaries and failure modes of the miner itself

- **Read-only.** Never modify transcripts, agent config, prompts, or skills.
- **Evidence-bound.** No incident without a real, citable turn range. A cluster
  you cannot point at is not reported.
- **Corpus, not case.** A single failure below `min_support` is not an
  anti-pattern; report it only in an appendix, never as a headline cluster.
- **Schema drift.** Transcript formats evolve (new block types, renamed fields).
  If a large fraction of lines fail to normalize, stop and report the parse rate
  rather than mining a corrupt stream.
- **Redaction.** Excerpts can contain secrets/PII from tool output. Truncate and
  scrub obvious credentials before writing them into the report (see the
  redaction note in `references/clustering-and-report.md`).
- **Privacy of the handoff.** The GEPA reflective dataset carries raw trajectory
  text; treat it as sensitive, same as the transcripts it came from.

## References

- `references/transcript-schemas.md` — Claude Code and Codex JSONL field maps;
  how to normalize both to one turn stream; parse commands.
- `references/anti-patterns.md` — the failure-mode taxonomy and a concrete
  detector (heuristic + regex + threshold) for each mode.
- `references/clustering-and-report.md` — two-stage clustering, severity
  scoring, report/JSON schema, redaction.
- `references/gepa-handoff.md` — wrapping the MIT gepars crate: turning mined
  failing trajectories into a GEPA reflective dataset.

## Related skills

- **background-rescue** — re-grounds ONE stuck/rotted/looping node live. This
  skill finds those nodes in BATCH, after the fact, across many sessions.
- **recursive-self-improvement** — consortium-graded, HITL improvement loop; a
  natural consumer of this report.
- **autonomous-orchestrator** — hill-climbs the harness itself; feed it the
  mined anti-patterns as its improvement targets.

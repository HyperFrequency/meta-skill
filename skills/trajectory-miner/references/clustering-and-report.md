# Clustering, scoring & report format

Incidents (from `anti-patterns.md`) become **clusters** = named failure modes
recurring across the corpus. Then rank, pick representatives, and emit.

---

## 1. Two-stage clustering

**Stage A — deterministic bucketing (do this first, always).**
Group incidents by the exact key `(mode, tool, normalized_signature)`. This
alone resolves the crisp modes — loops, error cascades, rate-limit stalls,
truncation — because their signatures already normalize away volatile tokens
(digits, paths, hex). Cheap, reproducible, no model needed.

Normalize signatures before bucketing:
- lowercase; collapse whitespace;
- strip digits, hex ids, absolute paths, tmp names, line/col numbers;
- keep the stable error phrase ("file not found", "connection refused").

**Stage B — embedding merge (only for fuzzy modes).**
`refusal`, `goal_drift`, `context_rot`, and `hallucinated_result` vary in
surface text, so Stage-A buckets fragment. Merge them:
1. Embed each incident's `evidence` (any sentence embedder; if none is
   available, fall back to TF-IDF cosine — do **not** block on an API).
2. Cluster within each `mode` by cosine similarity — HDBSCAN (`min_cluster_size
   = min_support`) or a similarity-threshold union-find at `>= 0.75`.
3. Name each cluster from its centroid / most-central evidence.

Drop any cluster with `count < min_support` (default 2) into an **appendix** of
one-offs — never a headline finding.

---

## 2. Severity & ranking

Per cluster:

```
priority = frequency_weight * severity_weight * blast_radius
```

- `frequency_weight` = number of incidents.
- `severity_weight` = max incident severity mapped `low=1, med=2, high=4`.
- `blast_radius` = distinct `session_id`s affected (a mode hitting 20 sessions
  beats one hitting 40 times in a single session).

Rank clusters by `priority` descending. Tag each with cause annotations from
overlapping incidents (e.g. "loop, preceded by `truncation`").

---

## 3. Representative selection

For each cluster pick ONE representative incident: the one whose `evidence` most
cleanly exhibits the mode (highest severity, then closest to the centroid for
fuzzy modes). Cut a **minimal excerpt**: the session `goal_text` + the diverging
turn range only — not the whole session. Include `session_id` and `turn_range`
so a reader can open the source.

---

## 4. Output schema

Emit both files to the caller's output dir.

`trajectory-report.json`:

```json
{
  "run": {
    "generated_at": "…", "corpus_root": "…",
    "files_scanned": 0, "files_unparseable": 0, "sessions": 0,
    "parse_rate": 0.0, "thresholds": { "min_support": 2, "loop_repeats": 3, "…": 0 }
  },
  "clusters": [
    {
      "id": "loop-bash-git-status",
      "mode": "loop",
      "name": "Repeated `git status` with no state change",
      "count": 12, "sessions_affected": 5,
      "severity": "high", "priority": 96.0,
      "cause_tags": ["truncation"],
      "signature": "loop:Bash:…",
      "representative": {
        "session_id": "…", "turn_range": [42, 60],
        "goal": "…", "excerpt": "…(scrubbed)…"
      },
      "recommended_fix": "Add a stop condition: after 2 identical Bash calls, force a plan step."
    }
  ],
  "appendix_oneoffs": [ { "mode": "…", "session_id": "…", "turn_range": [ ] } ]
}
```

`trajectory-report.md` — human view of the same: a ranked table (mode, name,
count, sessions, severity, priority), then one section per cluster with the
representative excerpt and the recommended fix. Lead with the top 3–5;
`recommended_fix` is a *suggestion for the harness owner*, not an action this
skill takes.

---

## 5. Redaction (before writing any excerpt)

Excerpts come from raw tool output and can carry secrets/PII.

- Truncate each excerpt (e.g. `<= 1500` chars) — you need the shape of the
  failure, not the payload.
- Scrub obvious credentials: strings matching `(?i)(api[_-]?key|token|secret|
  password|authorization|bearer|aws_[a-z_]*|-----BEGIN [A-Z ]*PRIVATE KEY)` and
  long high-entropy tokens → replace with `«redacted»`.
- Never echo `.env`, `~/.aws`, `~/.ssh`, or `settings.json` contents that a
  scanned Bash call may have printed. When in doubt, drop the line.

The report and the reflective dataset are as sensitive as the transcripts they
came from — store them beside the corpus, not in a shared location.

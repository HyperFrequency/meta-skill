# Gate envelope — the `antipattern-review` ApprovalRequest

This skill is invoked because a `trajectory-miner` scan workflow **parked** on a
shared gate. The park/resume handshake uses one envelope type — `ApprovalRequest`
— defined in the shared `hitl.proto`. Every HITL gate in the neuro-centrifuge
harness (surgery approvals, capital sign-off, this review) rides the same
envelope; the `kind` field discriminates. For this skill `kind` is always
`"antipattern-review"`.

Do not invent your own request shape. Consume the envelope you were handed,
validate it, and emit the matching response envelope. If a field named here is
absent, that is a contract violation — surface it, do not paper over it.

## The request envelope

```proto
// hitl.proto (shared across all neuro-centrifuge gates)
message ApprovalRequest {
  string request_id     = 1;  // stable id for this gate instance
  string kind           = 2;  // "antipattern-review" for this skill
  string workflow_run   = 3;  // the trajectory-miner scan run that parked
  double review_threshold = 4; // confidence below which a finding needs a human
  google.protobuf.Timestamp created_at = 5;
  google.protobuf.Timestamp expires_at = 6; // gate timeout; past it → timeout path
  IssueBatch payload    = 7;  // the findings to adjudicate
}
```

- `review_threshold` is the single gating knob (default `0.75`). A finding at or
  above it is auto-confirmed without a question; below it is asked. It arrives on
  the envelope so the miner and the reviewer agree on one number — never
  hard-code your own.
- `expires_at` drives the timeout path (see SKILL.md failure modes and
  `evidence-events.md`). A gate parked past `expires_at` must not silently
  auto-confirm anything that could drive a deletion.

## The issue-batch payload

The payload is a slice of `trajectory-miner`'s output. It maps **directly** onto
that skill's `trajectory-report.json` `clusters[]` — this is why the two skills
are tightly coupled: this envelope's `payload.findings[]` *is* that report's
clusters, wrapped for review.

```proto
message IssueBatch {
  string corpus_root = 1;
  repeated AntiPatternFinding findings = 2;
}

message AntiPatternFinding {
  string id            = 1;  // e.g. "loop-bash-git-status" (== cluster.id)
  string mode          = 2;  // loop | error_cascade | context_rot | goal_drift |
                             // hallucinated_result | rate_limit_stall | refusal
  string name          = 3;  // human-readable cluster name
  int32  count         = 4;  // incidents in the cluster
  int32  sessions_affected = 5;
  string severity      = 6;  // low | med | high
  double confidence    = 7;  // miner's confidence the cluster is REAL (0..1)
  repeated Evidence evidence = 8; // trace links + excerpts (see review-protocol)
  string proposed_fix  = 9;  // miner's recommended_fix (a SUGGESTION, not applied)
  string proposed_diff = 10; // optional before/after if the fix is concrete
}
```

Field-mapping note (miner report → envelope):

| `trajectory-report.json` cluster field | `AntiPatternFinding` field |
| --- | --- |
| `id`, `mode`, `name`, `count` | same names |
| `sessions_affected`, `severity` | same names |
| `priority` (freq×sev×blast) | folded into review order; not adjudicated |
| `representative.{session_id,turn_range,goal,excerpt}` | into `evidence[]` |
| `recommended_fix` | `proposed_fix` |
| (miner's per-cluster confidence) | `confidence` |

`priority` orders the review queue (highest first) but is **not** a thing the
human votes on — the human votes on whether the finding is real (`confidence`),
its label (`mode`/`name`), and its scope (`sessions_affected` / boundary).

## The response envelope

You return one `ApprovalResponse` per gate, carrying one verdict per finding:

```proto
message ApprovalResponse {
  string request_id = 1;   // echoes the request
  repeated FindingVerdict verdicts = 2;
  ResumeSummary resume = 3; // compact block for the scan workflow to continue on
}

message FindingVerdict {
  string finding_id = 1;
  string verdict    = 2;   // CONFIRM | REJECT | LABEL | BOUNDARY | UNRESOLVED
  string label      = 3;   // set when verdict==LABEL (corrected mode/name)
  Boundary boundary = 4;   // set when verdict==BOUNDARY (scope correction)
  double  confidence_after = 5; // finding confidence after this evidence event
  string  tier      = 6;   // auto-apply | manual  (see risk-tiering.md)
  string  source    = 7;   // human | default-on-timeout | auto-confirm
}
```

Every `FindingVerdict` is also written out-of-band as an evidence event, an
Align-Evals few-shot record, and an `_llm_scores` annotation row — see
`evidence-events.md`. The envelope is the *control-plane* return; those stores
are the *durable record*.

## Park / resume handshake

1. The scan workflow reaches its review stage, builds the `ApprovalRequest`, and
   **parks** — it suspends and waits on `request_id`.
2. This skill is invoked with that request. It validates the envelope (all
   required fields present, every `evidence` trace resolvable), triages by
   `review_threshold`, adjudicates the below-threshold findings, and records
   evidence events.
3. This skill returns the `ApprovalResponse`. The scan workflow **resumes** on
   `request_id`, threading the verdicts into whatever it does next (typically
   handing confirmed findings to `recursive-self-improvement` / `neuro-surgery`).
4. If the gate hits `expires_at` first, the timeout path in SKILL.md applies:
   safe-default verdicts for defaultable findings, `UNRESOLVED` for the rest, and
   the gate stays open for the next human touch.

## Validation before you ask anything

- **Envelope well-formed?** `request_id`, `kind=="antipattern-review"`,
  `review_threshold`, and a non-empty `payload.findings[]`. If not, return an
  error response — do not fabricate a batch.
- **Every referenced trace resolvable?** Each finding's `evidence[]` must point at
  a real session/turn range in `corpus_root`. A finding whose evidence cannot be
  resolved is auto-verdicted `REJECT` with reason `insufficient-evidence` (see
  `review-protocol.md`) — never CONFIRM on unseen evidence.
- **One ledger of record.** All verdicts for one `workflow_run` land in one
  evidence-event log — never fork a second store per re-invocation.

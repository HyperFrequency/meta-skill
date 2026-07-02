# INGEST & SCRUB (Loop-3 stage 1)

Ingest is the ONLY place raw agent runs enter the pipeline, and the ONLY place
they are scrubbed. **Scrub runs before storage** — an unscrubbed run is never
persisted to the mining corpus. Everything downstream (segment, scan, cluster,
act) reads the scrubbed, normalized stream, never the raw source.

```
sources ──▶ adapter ──▶ TurnEvent[] / SpanTree ──▶ SCRUB ──▶ corpus store
(4 kinds)   (per fmt)   (one contract)              (secrets,
                                                     injection,
                                                     PII)
```

The four authoritative sources normalize into **one** contract (`TurnEvent[]`,
§5). Adapters differ; the contract does not. Do not let a scanner branch on
source format — if it must, the adapter is leaking and should be fixed instead.

---

## 1. OTel spans (LLM/agent traces)

Observability backends (Langfuse, Phoenix/Arize, OpenLLMetry, Traceloop) export
**OpenTelemetry GenAI** spans as OTLP/JSON or a span-export file. One **trace**
(`trace_id`) ≈ one session; spans within it, ordered by `startTimeUnixNano`, are
the turn stream.

Map by the GenAI semantic-convention attributes:

| Span shape (attributes)                                             | → TurnEvent `kind` |
|--------------------------------------------------------------------|--------------------|
| `gen_ai.operation.name = "chat"` / `"generate_content"`            | `assistant_text` (+ `thinking` if a reasoning child span) |
| span/event with `gen_ai.prompt.*` role=user                        | `user_text`        |
| `gen_ai.operation.name = "execute_tool"`, `gen_ai.tool.name = X`  | `tool_call` (tool=X, input from `gen_ai.tool.call.arguments`) |
| the tool span's status / `gen_ai.tool.call.result` / span `ERROR` | `tool_result` (`ok = status != ERROR`) |

- Tokens: `gen_ai.usage.input_tokens` / `output_tokens` → `tokens`.
- Model / provider: `gen_ai.request.model`, `gen_ai.system`.
- `ts` = span `startTimeUnixNano` (→ ISO). Nested tool spans pair by parent/child
  span_id, so call↔result linkage is structural — no id-matching needed.
- Session id = `trace_id` (or `session.id` / `gen_ai.conversation.id` when set).

Cost lives here for free: sum child-span token usage per phase for the
cost-anomaly scanner.

## 2. First-party `.traj` artifact (proto schema)

neuro-centrifuge agents emit their own trajectory artifact — a length-prefixed
protobuf stream (`*.traj`), the canonical first-party record. Sketch:

```proto
message Trajectory {
  string session_id = 1;
  string agent = 2;                 // producing harness/skill
  string model = 3;
  int64  started_unix_ms = 4;
  string goal_text = 5;             // first user ask, verbatim
  repeated Step steps = 6;
  map<string,string> meta = 7;      // cwd, git_branch, run_id, parent_session
}
message Step {
  int32  seq = 1;
  int64  ts_unix_ms = 2;
  Role   role = 3;                  // USER|ASSISTANT|SYSTEM|TOOL
  string text = 4;                  // assistant/user/thinking text or tool output
  bool   thinking = 5;
  ToolCall   call = 6;              // set on tool_call steps
  ToolResult result = 7;            // set on tool_result steps
  Usage  usage = 8;                 // in/out tokens for assistant steps
  int32  depth = 9;                 // subagent recursion depth (0 = root)
}
message ToolCall   { string id = 1; string name = 2; string arguments_json = 3; }
message ToolResult { string call_id = 1; bool ok = 2; string content = 3; int32 exit_code = 4; }
message Usage      { int32 input_tokens = 1; int32 output_tokens = 2; }
```

Decode with the generated stubs; map `Step` → `TurnEvent` field-for-field.
`depth` feeds the infinite-recursion scanner directly. This is the richest
source — prefer it when both a `.traj` and a derived log exist for the same run.

## 3. Claude Code session `*.jsonl`

`~/.claude/projects/<cwd-slug>/<session-uuid>.jsonl` — one JSON object per line;
not every line is a turn.

- **Top-level `type`:** `user`, `assistant`, `system`, `summary`, plus non-turn
  bookkeeping (`queue-operation`, `attachment`, `last-prompt`, `mode`). Only
  `user`/`assistant`/`system` carry a `message`; keep the rest **only** for
  timestamp gaps.
- **Top-level keys:** `uuid`, `parentUuid`, `timestamp` (ISO-8601), `sessionId`,
  `cwd`, `gitBranch`, `version`, `isSidechain` (bool — subagent thread),
  `requestId` (assistant), `message`, `toolUseResult` (on the `user` line that
  carries a tool result).
- **`message.content` blocks:** `text`; `thinking`; `tool_use`
  (`{id,name,input}`, name ∈ `Bash|Read|Edit|Write|Agent|WebFetch|mcp__srv__tool…`);
  `tool_result` (`{tool_use_id,content,is_error}`, appears inside a **user**-role
  message; `is_error:true` = failed call). Assistant `message` also carries
  `model`, `stop_reason`, `usage`.
- **Pairing:** `tool_result.tool_use_id` → `tool_use.id`. `isSidechain:true`
  lines are subagents — group by `sessionId`, tag `is_sidechain` so a subagent
  loop is not blamed on the parent.

Sniff (first non-empty line): `type ∈ {user,assistant,system,summary}`.

## 4. lightspeed / forgecode session logs

Two additional coding-agent log formats (lightspeed session logs; ForgeCode
`forge` run logs). Both are JSON-per-line or a JSON run object with a
`messages`/`events` array of `{role, content, tool_calls[], tool_results[],
timestamp}`. They carry the same primitives as the others — user/assistant text,
tool call+result pairs, token usage — just under different keys.

> These two are **adapter points**: confirm the exact field names against a real
> sample from the corpus before trusting them, and encode the mapping in the
> adapter, not the scanners. If a field is absent (e.g. no per-turn tokens),
> leave the `TurnEvent` field null rather than inventing a value — the cost
> scanner degrades gracefully, a fabricated token count corrupts the median.

*(Codex `~/.codex/**/rollout-*.jsonl` — `payload`-wrapped `response_item`s with
`function_call`/`function_call_output` pairs, errors inside `output` (no
`is_error`) — is supported by the same contract via its own adapter. Do not read
`~/.codex/session_index.jsonl`; it is an index, not a transcript.)*

---

## 5. Normalized `TurnEvent` contract (target of every adapter)

```json
{
  "session_id": "…",
  "source": "otel|traj|claude|lightspeed|forgecode|codex",
  "is_sidechain": false,
  "depth": 0,                    // subagent recursion depth (traj/OTel child spans)
  "seq": 0,                      // 0-based order in the session
  "ts": "2026-07-02T…Z",
  "kind": "user_text|assistant_text|thinking|tool_call|tool_result",
  "tool": "Bash",               // tool_call / tool_result only
  "input": { … },               // tool_call only, parsed
  "input_sig": "Bash:sha1(canonical)",  // §6 — drives doom-loop detection
  "ok": true,                    // tool_result only
  "text": "…",                  // *_text/thinking, or result content
  "tokens": {"in":0,"out":0},
  "stop_reason": "end_turn",     // where the source exposes it
  "quarantined": false           // set by the injection scrubber (§7)
}
```

`goal_text` = the first `user_text` per session, stored separately — the anchor
for drift, context-degradation, and cluster grouping.

## 6. `input_sig` (canonical tool signature)

Canonicalize the tool input, then hash: `input_sig = tool + ":" + sha1(canonical)`.
Canonicalize = sort object keys; for `Bash`/shell strip volatile tokens
(timestamps, tmp paths, PIDs, uuids, absolute home paths) so a re-run of the same
command collapses to one signature. Stability here is load-bearing — a leaky
canonicalizer makes doom loops invisible (every repeat looks distinct) and cost
noise look like a pattern.

---

## 7. SCRUB pipeline (runs before persistence — three stages, in order)

Every text-bearing field (`text`, `input`, tool output) passes all three. Raw
values that trip a rule are replaced **in place**; the original is never written
to the corpus store.

**(a) Secret scanner.** Regex + Shannon-entropy pass (detect-secrets / gitleaks
rule style): API keys, bearer/OAuth tokens, `aws_[a-z_]*`, `-----BEGIN … PRIVATE
KEY-----`, `.env`/`~/.aws`/`~/.ssh`/`settings.json` dumps a Bash step may have
printed, and long high-entropy strings. Match → `«redacted:secret»`. When a whole
tool output is a credential dump, drop the field, keep the event shell.

**(b) Prompt-injection quarantine.** Tool results and other *external* content
(web fetches, file reads, MCP output) can carry injected instructions
("ignore previous instructions", "you are now…", tool output that issues
imperatives at the agent, known injection signatures). Flag the event
`quarantined:true` and route the raw text to a **separate quarantine store** — it
is kept out of the mining corpus and out of any LLM-judged step so an injection
cannot poison downstream reasoning. Quarantine is also a *signal*: it is the
upstream source for the context-poisoning detector (see `scanners.md` §3), so
record the quarantine hit as provenance, don't just discard it.

**(c) Anonymizer.** PII (emails, usernames, IPs, hostnames, absolute home paths)
→ **stable pseudonyms** using a per-corpus salt: `danrepaci157@…` → `user_7f3a`
every time. Stable so cross-session correlation still works (same person → same
token, needed for blast-radius counting) without leaking identity. Salt is
per-corpus and never stored with the output.

**Invariant:** the corpus store, the report, the reflective records, and the
anti-pattern registry are all downstream of this scrub. Nothing sensitive from
the raw run reaches the transcript, a shared store, or a judge model. Store the
scrubbed corpus **beside its source**, not in a shared location.

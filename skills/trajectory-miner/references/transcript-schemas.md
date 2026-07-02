# Transcript schemas & normalization

Two source formats. Their field names differ sharply — do **not** assume Claude
fields exist in Codex logs or vice versa. Normalize both into one `TurnEvent`
stream (below), then all detectors run format-agnostic.

---

## 1. Claude Code — `~/.claude/projects/<cwd-slug>/<session-uuid>.jsonl`

One JSON object per line. Not every line is a conversation turn.

**Top-level `type` values seen:** `user`, `assistant`, `system`, `summary`,
plus non-turn bookkeeping lines: `queue-operation`, `attachment`, `last-prompt`,
`mode`. Only `user` / `assistant` / `system` carry a `message`; skip the rest
for turn extraction but keep them for timestamp gaps.

**Common top-level keys:** `type`, `uuid`, `parentUuid`, `timestamp` (ISO-8601),
`sessionId`, `cwd`, `gitBranch`, `version`, `isSidechain` (bool — subagent
threads), `requestId` (assistant only), `message`, `toolUseResult` (present on
the `user` line that carries a tool result).

**`message` object:** `{ role, content, ... }`. On assistant lines `message`
also carries `model`, `stop_reason`, and `usage` (`input_tokens`,
`output_tokens`, cache fields) — used for truncation and token-burn detection.

**`message.content` is a list of blocks:**
- `{"type":"text","text": "..."}` — visible assistant/user text.
- `{"type":"thinking","thinking": "..."}` — extended-thinking block.
- `{"type":"tool_use","id","name","input"}` — a tool call. `name` is the tool
  (`Bash`, `Read`, `Edit`, `Agent`, `WebFetch`, `mcp__server__tool`, …);
  `input` is the argument object.
- `{"type":"tool_result","tool_use_id","content","is_error"}` — appears inside a
  **`user`**-role message. `is_error: true` marks a failed tool call. `content`
  is a string or a list of `{type:text,text}` blocks. The richer typed result
  also lands on the line's top-level `toolUseResult`.

**Pairing:** match `tool_result.tool_use_id` back to the `tool_use.id` to link a
call to its outcome. `isSidechain: true` lines belong to spawned subagents —
group them by `sessionId` but tag them so a subagent loop isn't blamed on the
parent.

Sniff test (first non-empty line): `type ∈ {user,assistant,system,summary}`.

---

## 2. Codex CLI — `~/.codex/**/rollout-*.jsonl` (and `archived_sessions/`)

Do **not** use `~/.codex/session_index.jsonl` — that is only an index
(`id, thread_name, updated_at`), not a transcript.

One JSON object per line with top-level `type` ∈ `session_meta`,
`response_item`, `event_msg`, `turn_context`. The turn data is under
**`payload`**.

**`payload.type` (or `payload.role`) values:**
- `user_message` / `message` with `role:user` — user turn.
- `agent_message` / `message` with `role:assistant` — assistant text.
- `reasoning` — model reasoning (Codex analogue of `thinking`).
- `function_call` — a tool call: `{name, arguments (JSON string), call_id}`.
- `function_call_output` — its result: `{call_id, output}`. Tool **errors**
  surface inside `output` (often an object/string with `exit_code`, `stderr`, or
  an error field) — there is no top-level `is_error` flag, so classify errors
  from the output payload (see anti-patterns → error cascade).
- `token_count` — usage accounting (`event_msg`); use for token-burn/stall.
- `task_started` / `task_complete` — turn lifecycle markers.

**`session_meta`** (first line) carries session id, cwd, model, and start time.

**Pairing:** match `function_call_output.call_id` to `function_call.call_id`.

Sniff test: `type ∈ {session_meta,response_item,event_msg,turn_context}`.

---

## 3. Normalized `TurnEvent` stream (target)

Reduce each session to an ordered list. This is what every detector reads.

```json
{
  "session_id": "…",           // sessionId | session_meta id
  "source": "claude|codex",
  "is_sidechain": false,        // Claude isSidechain; false for Codex
  "seq": 0,                      // 0-based position in the stream
  "ts": "2026-07-02T…Z",        // line timestamp (ISO)
  "kind": "user_text|assistant_text|thinking|tool_call|tool_result",
  "tool": "Bash",               // tool_call/tool_result only
  "input": { … },               // tool_call only, parsed (Codex: JSON.parse arguments)
  "input_sig": "Bash:sha1(canonical)",  // see below
  "ok": true,                    // tool_result only
  "text": "…",                  // *_text/thinking; or result content
  "tokens": {"in":0,"out":0},   // assistant turns where available
  "stop_reason": "end_turn"      // Claude assistant lines
}
```

**`input_sig` (drives loop detection):** canonicalize the tool input, then hash.
Canonicalize = sort object keys, and for `Bash` strip volatile tokens
(timestamps, tmp paths, PIDs, uuids) so "the same command re-run" collapses to
one signature. Keep it stable: `input_sig = tool + ":" + sha1(canonical_json)`.

**First user goal:** the first `user_text` event per session, stored separately
as `goal_text` — the anchor for drift/hallucination detectors.

---

## 4. Parse commands (starting points)

Enumerate + sniff:

```bash
find "$ROOT" -name '*.jsonl' -type f \
  | while read -r f; do
      head -c 400 "$f" | grep -qE '"type"\s*:\s*"(session_meta|response_item|event_msg|turn_context)"' \
        && echo "codex	$f" || echo "claude	$f";
    done
```

Extract Claude tool-call/result pairs with `jq` (per file):

```bash
jq -c 'select(.type=="assistant" or .type=="user")
       | .message.content[]?
       | select(.type=="tool_use" or .type=="tool_result")
       | {t:.type, id:(.id // .tool_use_id), name:.name, is_error:.is_error}' "$f"
```

Extract Codex calls/outputs:

```bash
jq -c 'select(.type=="response_item")
       | .payload
       | select(.type=="function_call" or .type=="function_call_output")
       | {t:.type, id:.call_id, name:.name}' "$f"
```

For anything beyond counting, do the normalization in a small Python pass
(`json.loads` per line, build `TurnEvent[]`); `jq` alone gets unwieldy for
cross-line pairing and signature hashing.

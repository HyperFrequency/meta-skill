# Codex adversarial review — initial implementation (2026-05-19)

Performed by codex (via `codex:codex-rescue` subagent) immediately after the
first build of `/relentless-inception`. The findings drove a patch pass on
the same day; entries below are kept verbatim for traceability + the patch
status is appended at the end.

## Verdict

`major-rework` — written design is strong, but the executable layer is
mostly scaffold and the actual leave-the-laptop loop is not yet implemented.

## Findings

```json
{
  "blocking_issues": [
    {
      "area": "Orchestrator runtime",
      "issue": "The entrypoint explicitly scaffolds state and exits instead of driving the loop it claims to drive.",
      "evidence": "scripts/orchestrator.py:4-16 + scripts/orchestrator.py:190-201",
      "patch_status": "scope-correction. Honest scope section added to SKILL.md; orchestrator.py renamed conceptually to a state-management helper for the LLM-side orchestrator. A real autonomous Python loop is out of scope for this skill — the LLM is the orchestrator; scripts manage state."
    },
    {
      "area": "Rescue mode",
      "issue": "scripts/rescue.sh does not exist",
      "evidence": "references/rescue-mode.md:132",
      "patch_status": "FIXED — scripts/rescue.sh now exists as a state-machine that claims a trigger, scaffolds the cycle dir, builds the inputs bundle, generates the RELENTLESS-INBOX prompt, and routes it through the relay."
    },
    {
      "area": "Trigger polling",
      "issue": "No code reads trigger files",
      "evidence": "agents/background-agent.md:41 + references/rescue-mode.md:134",
      "patch_status": "FIXED — scripts/rescue.sh atomically claims the oldest trigger from $RELENTLESS_INCEPTION_HOME/triggers/ and moves it to processed/. Invocation cadence still relies on the LLM-side orchestrator OR an outer wrapper invoking rescue.sh; that gap is now documented in SKILL.md."
    },
    {
      "area": "Role design",
      "issue": "6 of 14 listed roles have no agents/<role>.md",
      "evidence": "SKILL.md:38-44 lists 14 roles; agents/ had 8",
      "patch_status": "FIXED — added nexus-graph-writer, nexus-graph-synthesizer, uv-package, uv-workspaces, uv-dagger-deploy, temporal-tester. All 14 listed roles now have prompts."
    },
    {
      "area": "Shipping",
      "issue": "scripts/shipping/ does not exist",
      "evidence": "SKILL.md:137-139 + references/shipping.md:17,51,87",
      "patch_status": "FIXED — scripts/shipping/{uv_package,uv_workspaces,dagger_deploy}.sh added as functional stubs (real ladders implemented; cloud-deploy variants are placeholders matching DEPLOY_TARGET env)."
    }
  ],
  "high_priority_issues": [
    {
      "area": "Triple gate implementation",
      "issue": "Summarize gate passed reviewers with verdict==pass but recommendation != approve",
      "evidence": "agents/adversarial-review.md:63 + scripts/adversarial_review.sh:111 (original)",
      "patch_status": "FIXED — gate aggregation now requires verdict==pass AND recommendation==approve from all three reviewers. Adds unanimity + dissent_reasons fields for downstream consumers."
    },
    {
      "area": "Triple gate robustness",
      "issue": "Malformed JSON treated as a usable verdict",
      "evidence": "scripts/adversarial_review.sh:78-83 (original)",
      "patch_status": "FIXED — every reviewer output is validated via jq for a string-typed verdict field; malformed output is rewritten as an explicit fail JSON."
    },
    {
      "area": "Triple gate liveness",
      "issue": "No timeout on codex calls",
      "evidence": "scripts/adversarial_review.sh:71-73 + :99 (original)",
      "patch_status": "FIXED — REVIEWER_TIMEOUT (default 180s) wraps each codex call via `timeout`. On timeout, an explicit fail JSON is written."
    },
    {
      "area": "Rescue detection",
      "issue": "stall_watchdog.sh only compares elapsed since last Stop; doesn't track agent output / tool calls",
      "evidence": "scripts/stall_watchdog.sh:43-48",
      "patch_status": "DEFERRED — accurate Stop-event tracking is sufficient for the dominant stall mode (no Stop = orchestrator still busy or stalled mid-tool). Enhancement to track tool-calls.jsonl tracked as a Slice-2 item."
    },
    {
      "area": "Safety/budget enforcement",
      "issue": "Documented caps not enforced in code",
      "evidence": "SKILL.md:237-246 vs scripts/orchestrator.py:160-167",
      "patch_status": "ACKNOWLEDGED — SKILL.md now explicitly notes that caps are honored by the LLM-side orchestrator following the documented contract, not enforced by a daemon. Kill switch IS enforced by orchestrator.py and is checked at every script invocation."
    },
    {
      "area": "Runtime type contract",
      "issue": "Planner's manifest shape doesn't match orchestrator package's RunManifest dataclass",
      "evidence": "agents/planner.md:53-75 vs packages/orchestrator/src/orchestrator/manifest.py:18-28",
      "patch_status": "DEFERRED — the planner is the authoritative source for the runtime manifest shape (it's what gets persisted); the companion dataclass is a sketch for Slice-E integration. Tracked as a Slice-2 alignment task."
    },
    {
      "area": "Import fallback",
      "issue": "Import-orchestrator succeeds on any non-ImportError; doesn't verify expected symbols",
      "evidence": "scripts/orchestrator.py:128-135",
      "patch_status": "DEFERRED — current scaffold doesn't actually depend on the import at runtime; flagged for Slice-2 hardening when the loop is real."
    }
  ],
  "medium_priority_issues": [
    {
      "area": "Settings contract",
      "issue": "RELENTLESS_INCEPTION_HOME documented but ignored by orchestrator.py",
      "patch_status": "FIXED — orchestrator.py + rescue.sh now honor $RELENTLESS_INCEPTION_HOME. Other scripts (stall_watchdog, status_line) still hardcode the default path; tracked."
    },
    {
      "area": "Model/default consistency",
      "issue": "dev-worker effort defaults conflict across docs and packages/orchestrator/roles.py",
      "patch_status": "FIXED — reconciled to xhigh in packages/orchestrator/src/orchestrator/roles.py."
    },
    {
      "area": "Prereq enforcement",
      "issue": "MCP availability shown as warnings despite SKILL.md saying refuse",
      "patch_status": "ACKNOWLEDGED — MCP availability isn't auto-detectable cheaply from a shell script; the warning model is intentional. SKILL.md updated to clarify."
    },
    {
      "area": "Manual rescue trigger schema",
      "issue": "Trigger from relentless_relay.sh omits run_id",
      "patch_status": "ACKNOWLEDGED — manual triggers happen before any run is necessarily active; the trigger consumer (rescue.sh) falls back to most-recently-modified manifest. Documented."
    },
    {
      "area": "Tearsheet scope",
      "issue": "tearsheet.py renders less than SKILL.md describes",
      "patch_status": "ACKNOWLEDGED — tracked as Slice-2 work to expand."
    },
    {
      "area": "Spec compliance",
      "issue": "Live containerized testing + screen recording not implemented",
      "patch_status": "ACKNOWLEDGED — the broader skynet/exaflop loop wraps existing test + Dagger commands rather than implementing a fresh container harness; this matches the realistic scope of a skill (vs a standalone product)."
    }
  ],
  "low_priority_notes": [
    {
      "area": "Description calibration",
      "patch_status": "DEFERRED — description optimization loop is a final-polish step per the skill-creator workflow; will run after Slice-2 patches land."
    },
    {
      "area": "Original spec drift",
      "issue": "Spec says 2 fails before restart; skill defaults to N=3",
      "patch_status": "ACKNOWLEDGED — N is configurable via env. Default of 3 felt right empirically; documented the divergence in SKILL.md."
    }
  ]
}
```

## Things that look right (preserve)

- The 8 original agent prompts are coherent + have concrete output shapes.
- Planner + adversarial-review prompts emphasize testable acceptance criteria.
- Relay rewrite preserves the original archive-before-paste anti-retrigger pattern.
- main/master refusal works at startup.
- Kill switch checked at startup.
- Tearsheet template is self-contained.
- Triple-summarize gate identified as load-bearing AND now correctly requires
  unanimity on `verdict==pass AND recommendation==approve`.

## What's still acknowledged as gap

The skill is currently a **strong design + state-management harness** with
an **LLM-driven runtime**. A standalone Python autonomous loop is not
implemented (and arguably shouldn't be — the LLM is the only thing that can
spawn subagents). Future iterations should focus on:

1. A small daemon (launchd plist or cron) that periodically calls
   `stall_watchdog.sh --sweep` and `rescue.sh` so stall detection + rescue
   handoff happen without the LLM having to remember to do it.
2. Tightening companion-package import contract.
3. Aligning the RunManifest dataclass with the planner's emitted shape.
4. Expanding tearsheet renderer.
5. Description optimization loop via skill-creator.

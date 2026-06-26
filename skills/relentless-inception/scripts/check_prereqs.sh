#!/usr/bin/env bash
# check_prereqs.sh — preflight for /relentless-inception runs.
# Refuses to start (exit nonzero) if anything required is missing.

set -uo pipefail

FAIL=0
WARN=0

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
plain()  { printf '%s\n' "$*"; }

ok()   { green "  OK   $*"; }
miss() { red   "  FAIL $*"; FAIL=$((FAIL+1)); }
warn() { yellow "  WARN $*"; WARN=$((WARN+1)); }

plain "Tools:"
for cli in codex uv dagger docker tmux jq git python3; do
  if command -v "$cli" >/dev/null 2>&1; then
    ok "$cli ($(command -v $cli))"
  else
    miss "$cli not found — install per references/prereqs.md"
  fi
done

plain ""
plain "Credentials:"
if [[ -n "${OPENROUTER_API_KEY:-}" ]] || [[ -f ~/.claude/.env ]] && grep -q '^OPENROUTER_API_KEY=' ~/.claude/.env 2>/dev/null; then
  ok "OPENROUTER_API_KEY present"
else
  miss "OPENROUTER_API_KEY missing — required for gpt-5.5 / gemini / gpt-pro routes"
fi
if [[ -n "${ANTHROPIC_API_KEY:-}" ]] || [[ -f ~/.claude/.env ]] && grep -q '^ANTHROPIC_API_KEY=' ~/.claude/.env 2>/dev/null; then
  ok "ANTHROPIC_API_KEY present"
else
  warn "ANTHROPIC_API_KEY not set in env — fine if you're inside Claude Code (in-process routing), required otherwise"
fi

plain ""
plain "Optional MCPs (skill runs with reduced features if missing):"
for mcp in git-nexus context7 mcp2cli infranodus serena; do
  warn "$mcp — not auto-verifiable; check ~/.claude/settings.json / federate via ContextForge"
done

plain ""
plain "Skill bundle:"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
for f in SKILL.md scripts/relentless_relay.sh scripts/stall_watchdog.sh scripts/status_line.sh scripts/install_hooks.sh agents/planner.md agents/dev-worker.md references/adversarial-gates.md; do
  if [[ -f "$SKILL_DIR/$f" ]]; then
    ok "$f"
  else
    miss "$f missing — re-install the skill bundle"
  fi
done

plain ""
plain "Run state directory:"
if [[ -d ~/.claude/relentless-inception ]]; then
  ok "$HOME/.claude/relentless-inception exists"
else
  warn "$HOME/.claude/relentless-inception does not exist — will be created on first run"
fi
if [[ -f ~/.claude/relentless-inception/KILL ]]; then
  warn "KILL switch is set at $HOME/.claude/relentless-inception/KILL — remove it before running"
fi

plain ""
if [[ "$FAIL" -gt 0 ]]; then
  red "$FAIL fatal issue(s). Fix above before running /relentless-inception."
  exit 1
fi
if [[ "$WARN" -gt 0 ]]; then
  yellow "$WARN warning(s) — skill will run with reduced features."
fi
green "Prereqs OK."
exit 0

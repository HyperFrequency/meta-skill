---
name: cmux-keyboard-shortcuts
version: 0.1.0
description: "Guide and apply cmux keyboard shortcut customization in ~/.config/cmux/cmux.json. Use when the user asks to customize, rebind, unbind, reset, audit, or create shortcut templates for cmux, including tmux-style, Vim-style, terminal-first, browser-heavy, iTerm/Terminal-like, or agent-triage layouts. NOT for non-shortcut cmux settings like theme, fonts, or workspace config (use the cmux-settings skill); NOT for third-party cmux forks or the unrelated tmux 'cmux' clone (targets the cmux app's shortcuts.bindings schema); NOT for terminal-emulator, shell, or macOS-level keybindings outside cmux; NOT for the in-app Settings UI / UserDefaults reset flow that file overrides alone cannot clear."
---

# cmux-keyboard-shortcuts

Use this skill to turn a user's workflow preferences into cmux shortcut bindings in `~/.config/cmux/cmux.json`. It should guide the user, propose compact templates, apply selected changes, and confirm the config parses with recognized keys.

## Prerequisites

- Work from a cmux checkout or worktree root when possible.
- Use `skills/cmux-settings/scripts/cmux-settings` for every read/write. It reads JSONC, writes atomically, and validates JSON plus recognized settings keys.
- For action IDs, read `skills/cmux-settings/references/shortcut-actions.md`.
- For current defaults, read `web/data/cmux-shortcuts.ts` or `Sources/KeyboardShortcutSettings.swift`.

```bash
find_cmux_settings() {
  local root
  root="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || pwd)"
  for candidate in \
    "$root/skills/cmux-settings/scripts/cmux-settings" \
    "${CODEX_HOME:-$HOME/.codex}/skills/cmux-settings/scripts/cmux-settings" \
    "$HOME/.agents/skills/cmux-settings/scripts/cmux-settings"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

if [[ -z "${CMUX_SETTINGS:-}" ]]; then
  CMUX_SETTINGS="$(find_cmux_settings)" || {
    echo "cmux-settings helper not found; run from a cmux checkout or install cmux-settings" >&2
    exit 1
  }
fi
```

## Shortcut Model

- Setting path: `shortcuts.bindings.<actionId>`.
- Single stroke: `"cmd+b"`.
- Chord: `["ctrl+b","c"]`. The first stroke needs a modifier unless the key is Space. The second stroke can be bare.
- Unbind: prefer `null` for explicit unbinds. `""`, `"none"`, `"clear"`, `"unbound"`, and `"disabled"` are accepted aliases, but `null` is the clearest JSON value and matches the templates below.
- `selectSurfaceByNumber` and `selectWorkspaceByNumber` must use a digit from 1 to 9. `cmd+1` means the full `cmd+1` through `cmd+9` family.
- `showHideAllWindows` and `globalSearch` are system-wide shortcuts. They cannot be chords, require modifiers, and may be rejected by macOS if reserved.
- `showHideAllWindows` also requires Settings > Global Hotkey > Enable System-Wide Hotkey. The binding can validate in `cmux.json` while the feature is disabled, so warn the user to enable that setting before reporting the shortcut as usable.
- `unset` deletes a `cmux.json` override. It does not clear shortcut changes saved through the Settings UI/UserDefaults. If the user asks for true built-in defaults, tell them to use Settings > Keyboard Shortcuts > Reset Default Shortcuts after clearing file-managed overrides, then verify in the app. For `showHideAllWindows`, use Settings > Global Hotkey to restore the shortcut to `ctrl+opt+cmd+.` because Keyboard Shortcuts > Reset Default Shortcuts intentionally skips the global hotkey.
- Saving `cmux.json` live reloads. Do not tell the user to restart cmux.

## Workflow

1. Classify the request:
   - One-off rebind or unbind: map the phrase to an action ID, apply it, validate, and report the previous and new binding.
   - Audit-only request: inspect current bindings, validate, and summarize overrides/unbound shortcuts without writing.
   - Reset request: clarify whether the user means file-managed overrides or true built-in defaults. For file-managed resets, use `unset` for named actions. For true built-in defaults, remove file overrides and direct the user to Settings > Keyboard Shortcuts > Reset Default Shortcuts; do not report built-in defaults restored from `cmux-settings` alone. If `showHideAllWindows` is included, also direct them to Settings > Global Hotkey to restore `ctrl+opt+cmd+.` and the enable toggle.
   - Broad customization request: propose 3 to 5 templates from "Preset Templates" and ask the user to choose.
   - Named style such as tmux, Vim, iTerm, browser, or agent triage: select the closest template, show the changed actions and likely collisions, and ask before a bulk apply unless the user explicitly said to apply it.
2. Inspect existing config:

   ```bash
   "$CMUX_SETTINGS" path
   "$CMUX_SETTINGS" get shortcuts.bindings 2>/dev/null || printf '{}\n'
   "$CMUX_SETTINGS" validate
   ```

3. Before applying a template, snapshot prior values for every action you will change. A path that is absent must revert with `unset`; a path with an existing custom value must revert with `set <same-json-value>`.

   ```bash
   "$CMUX_SETTINGS" get shortcuts.bindings.focusLeft 2>/dev/null || printf '<absent>\n'
   ```

4. Apply only the chosen action paths:

   ```bash
   "$CMUX_SETTINGS" set shortcuts.bindings.newSurface '["ctrl+b","c"]'
   "$CMUX_SETTINGS" set shortcuts.bindings.focusLeft cmd+opt+h
   "$CMUX_SETTINGS" set shortcuts.bindings.sendFeedback null
   "$CMUX_SETTINGS" validate
   ```

5. Verify readback for changed actions:

   ```bash
   "$CMUX_SETTINGS" get shortcuts.bindings.newSurface
   ```

6. Finish with the template name, changed actions, and exact revert commands from the snapshot. Use `unset` only for actions that were absent before the template; use `set` to restore previous custom bindings.

## Preset Templates

Propose 3 to 5 of these by name, then apply the chosen one action by action — never overwrite the whole `shortcuts.bindings` object. Full per-action `set`/`unset` command blocks live in `references/preset-templates.md`; read that file before applying.

| Template | Intent |
| --- | --- |
| Tmux Prefix | One `ctrl+b` chord namespace for surfaces, splits, and pane focus. |
| macOS Terminal/iTerm Restore | `unset` surface/split/tab overrides back to built-in defaults. |
| Vim Pane Navigation | Prefix-free `cmd+opt+h/j/k/l` pane focus and splits. |
| Agent Triage | Notification/unread handling on one key family, Vim-compatible. |
| Workspace And Surface Lanes | Workspaces and surfaces on distinct number/bracket lanes. |
| Browser Defaults Restore | `unset` embedded-browser overrides back to macOS browser defaults. |
| Terminal-First Cleanup | Unbind app-level extras (rename, flash, feedback) to `null`. |

## Rules

- Do not edit `~/.config/cmux/settings.json` unless the user explicitly asks. It is legacy fallback config.
- Do not overwrite all of `shortcuts.bindings` unless the user explicitly wants a full replacement.
- Do not invent action IDs. Validate against the schema or `shortcut-actions.md`.
- Do not apply a broad template without showing the changed actions first unless the user explicitly said to apply that named template.
- Do not promise conflict detection from `cmux-settings validate`; it validates JSON and supported keys, not shortcut syntax, macOS reservation, or every focus-context conflict.
- Before assigning `cmd+[` or `cmd+]` to application-scoped actions, warn that they collide with common browser Back/Forward behavior unless the browser actions are also changed or unbound.
- Prefer `unset` to clear file-managed overrides for individual actions. Do not call this a built-in default reset unless Settings UI/UserDefaults values have also been reset:

  ```bash
  "$CMUX_SETTINGS" unset shortcuts.bindings.focusLeft
  "$CMUX_SETTINGS" validate
  ```

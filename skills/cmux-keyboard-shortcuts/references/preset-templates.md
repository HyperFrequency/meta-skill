# Preset Templates

Use these as proposal templates. Apply them action by action, not by overwriting the whole `shortcuts.bindings` object. Always snapshot prior values first (see SKILL.md Workflow step 3) so you can produce exact revert commands.

## Tmux Prefix

For users who want one terminal-style shortcut namespace and accept that `ctrl+b` starts a cmux chord instead of going directly to the shell.

```bash
"$CMUX_SETTINGS" set shortcuts.bindings.newSurface '["ctrl+b","c"]'
"$CMUX_SETTINGS" set shortcuts.bindings.closeTab '["ctrl+b","x"]'
"$CMUX_SETTINGS" set shortcuts.bindings.nextSurface '["ctrl+b","n"]'
"$CMUX_SETTINGS" set shortcuts.bindings.prevSurface '["ctrl+b","p"]'
"$CMUX_SETTINGS" set shortcuts.bindings.selectSurfaceByNumber '["ctrl+b","1"]'
"$CMUX_SETTINGS" set shortcuts.bindings.splitRight '["ctrl+b","v"]'
"$CMUX_SETTINGS" set shortcuts.bindings.splitDown '["ctrl+b","s"]'
"$CMUX_SETTINGS" set shortcuts.bindings.focusLeft '["ctrl+b","h"]'
"$CMUX_SETTINGS" set shortcuts.bindings.focusDown '["ctrl+b","j"]'
"$CMUX_SETTINGS" set shortcuts.bindings.focusUp '["ctrl+b","k"]'
"$CMUX_SETTINGS" set shortcuts.bindings.focusRight '["ctrl+b","l"]'
"$CMUX_SETTINGS" set shortcuts.bindings.toggleSplitZoom '["ctrl+b","z"]'
"$CMUX_SETTINGS" set shortcuts.bindings.toggleTerminalCopyMode '["ctrl+b","["]'
"$CMUX_SETTINGS" set shortcuts.bindings.equalizeSplits '["ctrl+b","="]'
```

## macOS Terminal/iTerm Restore

For users who want surface, split, and tab behavior to feel like common macOS terminals again. These actions already match cmux built-in defaults when no Settings UI override exists, so unset file overrides instead of writing default values.

```bash
"$CMUX_SETTINGS" unset shortcuts.bindings.newSurface
"$CMUX_SETTINGS" unset shortcuts.bindings.closeTab
"$CMUX_SETTINGS" unset shortcuts.bindings.nextSurface
"$CMUX_SETTINGS" unset shortcuts.bindings.prevSurface
"$CMUX_SETTINGS" unset shortcuts.bindings.selectSurfaceByNumber
"$CMUX_SETTINGS" unset shortcuts.bindings.splitRight
"$CMUX_SETTINGS" unset shortcuts.bindings.splitDown
"$CMUX_SETTINGS" unset shortcuts.bindings.toggleSplitZoom
"$CMUX_SETTINGS" unset shortcuts.bindings.toggleTerminalCopyMode
"$CMUX_SETTINGS" unset shortcuts.bindings.renameTab
```

## Vim Pane Navigation

For users who want fast pane movement without a prefix and do not want to depend on arrow keys.

```bash
"$CMUX_SETTINGS" set shortcuts.bindings.focusLeft cmd+opt+h
"$CMUX_SETTINGS" set shortcuts.bindings.focusDown cmd+opt+j
"$CMUX_SETTINGS" set shortcuts.bindings.focusUp cmd+opt+k
"$CMUX_SETTINGS" set shortcuts.bindings.focusRight cmd+opt+l
"$CMUX_SETTINGS" set shortcuts.bindings.splitRight cmd+opt+v
"$CMUX_SETTINGS" set shortcuts.bindings.splitDown cmd+opt+s
"$CMUX_SETTINGS" set shortcuts.bindings.toggleSplitZoom cmd+opt+z
"$CMUX_SETTINGS" set shortcuts.bindings.equalizeSplits cmd+opt+=
```

## Agent Triage

For users who live in notifications and want unread handling on one key family. This keeps toggle unread on `cmd+opt+u` so it can be combined with Vim Pane Navigation without colliding with `cmd+opt+j`.

```bash
"$CMUX_SETTINGS" set shortcuts.bindings.showNotifications cmd+u
"$CMUX_SETTINGS" set shortcuts.bindings.jumpToUnread cmd+j
"$CMUX_SETTINGS" set shortcuts.bindings.markOldestUnreadAndJumpNext cmd+shift+j
"$CMUX_SETTINGS" set shortcuts.bindings.toggleUnread cmd+opt+u
"$CMUX_SETTINGS" set shortcuts.bindings.triggerFlash cmd+shift+h
"$CMUX_SETTINGS" set shortcuts.bindings.focusRightSidebar cmd+shift+e
```

## Workspace And Surface Lanes

For users who want workspaces and surfaces on distinct number and bracket lanes.

```bash
"$CMUX_SETTINGS" set shortcuts.bindings.selectWorkspaceByNumber cmd+1
"$CMUX_SETTINGS" set shortcuts.bindings.selectSurfaceByNumber cmd+opt+1
"$CMUX_SETTINGS" set shortcuts.bindings.nextSidebarTab 'cmd+opt+]'
"$CMUX_SETTINGS" set shortcuts.bindings.prevSidebarTab 'cmd+opt+['
"$CMUX_SETTINGS" set shortcuts.bindings.nextSurface 'cmd+shift+]'
"$CMUX_SETTINGS" set shortcuts.bindings.prevSurface 'cmd+shift+['
```

## Browser Defaults Restore

For users who changed too much and want embedded-browser behavior to match common macOS browser shortcuts again. Use `unset` to clear file overrides so future cmux defaults still apply when no Settings UI override exists.

```bash
"$CMUX_SETTINGS" unset shortcuts.bindings.openBrowser
"$CMUX_SETTINGS" unset shortcuts.bindings.focusBrowserAddressBar
"$CMUX_SETTINGS" unset shortcuts.bindings.browserBack
"$CMUX_SETTINGS" unset shortcuts.bindings.browserForward
"$CMUX_SETTINGS" unset shortcuts.bindings.browserReload
"$CMUX_SETTINGS" unset shortcuts.bindings.browserZoomIn
"$CMUX_SETTINGS" unset shortcuts.bindings.browserZoomOut
"$CMUX_SETTINGS" unset shortcuts.bindings.browserZoomReset
"$CMUX_SETTINGS" unset shortcuts.bindings.toggleBrowserDeveloperTools
"$CMUX_SETTINGS" unset shortcuts.bindings.showBrowserJavaScriptConsole
"$CMUX_SETTINGS" unset shortcuts.bindings.find
"$CMUX_SETTINGS" unset shortcuts.bindings.findNext
"$CMUX_SETTINGS" unset shortcuts.bindings.findPrevious
```

## Terminal-First Cleanup

For users who want fewer app-level shortcuts. Prefer unbinding only the actions they name, but this is a reasonable starting proposal.

```bash
"$CMUX_SETTINGS" set shortcuts.bindings.renameTab null
"$CMUX_SETTINGS" set shortcuts.bindings.renameWorkspace null
"$CMUX_SETTINGS" set shortcuts.bindings.editWorkspaceDescription null
"$CMUX_SETTINGS" set shortcuts.bindings.triggerFlash null
"$CMUX_SETTINGS" set shortcuts.bindings.sendFeedback null
```

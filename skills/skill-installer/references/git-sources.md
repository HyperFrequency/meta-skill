# Git sources, layout, and the install lockfile

How to resolve a source into an immutable, installable set of skills.

## Accepted source forms

| Form | Example | Notes |
| --- | --- | --- |
| Full HTTPS repo | `https://github.com/<owner>/<repo>` | Default branch, every `skills/**/SKILL.md`. |
| HTTPS with ref | `https://github.com/<owner>/<repo>/tree/<ref>` | Pin to a branch, tag, or SHA. |
| Slug shorthand | `<owner>/<repo>` | Assume the default host (e.g. GitHub); resolve to the full URL. |
| Host shorthand + ref + path | `<host>:<owner>/<repo>@<ref>/<path>` | e.g. `gh:anthropics/superpowers@v2/skills/brainstorming` — ref and an optional path scope in one token. |
| Generic git remote | `git+ssh://…`, `https://gitlab.com/…` | Any URL `git clone` accepts. |

Reject anything that is not a git remote (a bare web page, a gist HTML view, a
tarball URL) — tell the user what a valid source looks like instead of guessing.

## Fetch and pin

```bash
tmp=$(mktemp -d)
git clone --depth 1 --branch "<ref-or-default>" "<url>" "$tmp"
sha=$(git -C "$tmp" rev-parse HEAD)   # the immutable unit of trust
```

- Always resolve a moving branch to a concrete `<sha>` at clone time. Every
  downstream artifact — the safety-gate report, the confirm screen, the lockfile —
  references `<sha>`, never the branch name.
- `--depth 1` keeps the clone cheap; deepen only if you must reach a specific
  historical ref.

## Path scoping

If the source token carried a `/<path>` (e.g. `…@<ref>/skills/brainstorming`),
enumerate only under that path. Otherwise enumerate every `skills/<name>/SKILL.md`
in the repo. For each SKILL.md, collect its companion files: anything under a
sibling `scripts/`, any `*.py`/`*.sh` in the skill directory, and any file the
SKILL.md references by relative path. All of these go through the safety gate — a
clean SKILL.md with a malicious helper script is still a malicious skill.

## Namespace derivation

The `<namespace>` is the last URL path segment (the repo name), lowercased and
slugified. A repo with several skills installs them all under one shared namespace:

```
gh:acme/lab-skills            → namespace "lab-skills"
  skills/dock/SKILL.md        → lab-skills/dock
  skills/score/SKILL.md       → lab-skills/score
```

Deriving the namespace deterministically from the source is what lets a later
`remove <namespace>` argument match what was installed. If two different sources
would collide on one namespace, disambiguate with `<owner>-<repo>` and tell the
user.

## On-disk layout

Install into the agent's skills directory — for Claude Code that is
`~/.claude/skills/`; other harnesses use their configured path. One directory per
installed skill, grouped by namespace:

```
~/.claude/skills/
  <namespace>/
    <name>/
      SKILL.md
      references/…        # copied verbatim from the source
      scripts/…
```

Copy the vetted skill directory as-is; do not rewrite the fetched SKILL.md on
install (rewriting would invalidate what the human approved on the confirm screen).

## Install lockfile

Keep a lockfile next to the skills directory (e.g.
`~/.claude/skills/.installed.json`) so every installed skill is reproducible and so
`list`/`remove` have a source of truth beyond the raw directory tree. One entry per
installed skill:

```json
{
  "lab-skills/dock": {
    "source": "gh:acme/lab-skills",
    "sha": "9f1c2ab…",
    "installed_at": "2026-07-10T14:03:00Z",
    "gate": "warn",
    "warnings": ["layer4: network egress in scripts/fetch.sh"]
  }
}
```

- `sha` pins the exact commit so a reinstall is byte-identical.
- `gate` (`allow`/`warn`) and `warnings` carry the review-me signal forward: `list`
  prints a `⚠` for any `warn` entry, and a future re-vet can compare against a fresh
  clone at the same SHA.
- **List** = read this file, print `namespace/name` with the `⚠` marker.
- **Remove `<namespace>`** = delete every matching directory and drop all its
  entries. **Remove `<namespace>/<name>`** = delete one directory and one entry.
  Report the count removed.

The lockfile is local and reproducible; it deliberately depends on no external
sync service.

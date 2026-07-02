# DeepWiki integration (HyperFrequency org forks only)

Step 6 of the main flow. This is what makes a fork's supplementary docs
discoverable across the org rather than living only in this user's vault.

## When it fires

Only when the fork URL is under `HyperFrequency/`. Personal forks (any other
owner) skip this entirely — their docs stay local in
`08-code-docs/forked-up/<repo>/`.

## How

After the supplementary wiki for `08-code-docs/forked-up/<repo>/` is written,
invoke the sibling skill `/doc-sync-embed-verify`. That skill owns the actual
push to the shared Devin DeepWiki repo (`HyperFrequency/deep-tool-wiki`); this
skill does not call Devin directly. It also updates the InfraNodus knowledge
graph + reasoning ontology for the fork.

The push is additionally triggered automatically by the PostToolUse hook on
`git push` to `deep-tool-wiki` and by the GitHub Action on PR merge — so a manual
invocation here is the proactive path, not the only path.

## What gets pushed

The five generated files (`README.md`, `functional-diff.md`, `code-examples.md`,
`upstream-link.md`, `new-files.md`) plus their frontmatter, including
`fork_point`, `last_merge_base`, and `confidence`. DeepWiki keys the entry on the
fork slug; the `upstream-link.md` pointer ties it back to the upstream's
`/deep-tool-wiki` or `/adjacent-tools-code-docs` page.

## On unfork

Do not delete DeepWiki entries when a fork is retired — they remain for
historical reference (see the Unforking section in SKILL.md).

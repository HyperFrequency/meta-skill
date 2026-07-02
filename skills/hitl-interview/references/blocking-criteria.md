# Blocking Criteria — should I actually ask this?

The filter that turns a long candidate list into the 1–4 questions worth interrupting a human for. Apply to **every** candidate question before it reaches `AskUserQuestion`.

## The three-way sort

For each candidate, classify it as exactly one of:

| Class | Meaning | Action |
| --- | --- | --- |
| **Blocking** | The run cannot correctly proceed *right now* without the human's input, and the input exists only in the human's head. | Keep — ask it this round. |
| **Inferable** | A defensible answer can be derived from context, files, conventions, prior answers, or a safe default. | Drop — infer it, record the inferred value as an assumption in the ledger. |
| **Deferrable** | It will block *later*, not now; or it depends on the outcome of work not yet done. | Drop for now — queue it for the gate where it actually blocks. |

Only **Blocking** survives to the ask.

## Test each candidate against these gates (all must be YES to keep)

1. **Only-human?** Is the human the *only* source? If a file, the repo, the web, or a codebase holds the answer, it is not blocking — go get it (`Read`/`Grep`, `deep-research`, `gitnexus`). 
2. **Now?** Does progress stop *this step* without it? If the run can advance and the question resolves itself downstream, defer.
3. **No safe default?** Would picking your best default and noting the assumption be *wrong enough to matter*? If a default is safe and recoverable, don't ask — use it.
4. **Material divergence?** For disambiguation: do the readings actually lead to *different work*? If all interpretations converge on the same action, pick one silently.
5. **Not already answered?** See the no-re-ask check below.

If any gate is NO, the question is inferable or deferrable, not blocking.

## The six categories (what legitimately blocks)

A question only survives if it maps to one of these. If it maps to none, it is almost certainly inferable.

1. **Blocking requirement** — a fact only the human has: target market/user, budget or capital cap, which of two sources is canonical, the deploy target, regulatory constraint.
2. **Preference** — several answers are all correct; taste decides: naming, stack, tone, tunable risk aggressiveness, report format.
3. **Approval / sign-off** — an irreversible or costly action needs an explicit human yes: deploy, spend, delete, send/publish, allocate capital, rotate a credential. *These always block* — never auto-approve an irreversible action.
4. **Disambiguation** — the instruction genuinely supports more than one reading and the readings diverge into different work.
5. **Acceptance criteria** — "done" is undefined and the human owns the definition (the pass bar, the metric, the threshold).
6. **Missing precondition** — the human must provide something before work can continue: a credential *name* (never the value — see below), an access grant, a file, a URL.

## Approvals are special

Category-3 approvals bypass the "safe default" shortcut: even if a default exists, an irreversible/costly action must get an explicit human decision. The default for an approval is always the **safe/no-op** side (do not deploy, do not spend), and the option description must state what is irreversible. You may still *batch* the approval with other questions in the same round.

## The no-re-ask check

Before asking, load the ledger (`state/interview-ledger.md` by default) and drop any candidate that is:
- **Already answered** — same decision, same context.
- **Derivable** — answerable by combining prior answers (e.g. they picked "conservative risk" earlier ⇒ don't ask the per-trade cap; infer the conservative value and note it).
- **Superseded** — a later, broader answer already covers it.

Re-asking a settled question is the single most damaging thing this skill can do — it trains the human to distrust the harness's memory. When in doubt, infer from the prior answer and record the inference rather than re-ask.

## Credential preconditions — never elicit the secret

For a missing credential, ask only for the **name** of the env var / setting the human must populate, and ask them to set it out-of-band (env var, `--settings`, secret manager). Never ask the human to paste a token/key/password into the interview, and never read/echo one back. This mirrors the global credential-safety rule.

## Calibration

A well-run gate is typically **1–4 questions**. Zero is fine and common — if nothing is blocking, do not invoke this skill at all; just proceed with recorded assumptions. If you drafted 10+, you have under-filtered: most are inferable. Push them back through the three-way sort before interrupting the human.

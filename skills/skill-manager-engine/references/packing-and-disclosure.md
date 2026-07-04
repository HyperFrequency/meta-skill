# Token packing & progressive disclosure (behavioral spec)

This subsystem decides **how much of a skill to load** and **which pieces** given
a token budget. It is what lets the harness inject skills into context
economically, and its pack contracts map directly to D13 eval-class context
loads. Clean-room behavioral description; constants are parity targets.

## Progressive disclosure levels

A `DisclosureLevel` selects a coarse budget:

| Level | # | Token budget | Content |
|---|---|---|---|
| **Minimal** | 0 | ~100 | name + one-line description |
| **Overview** | 1 | ~500 | name, description, key section headers |
| **Standard** | 2 | ~1500 | overview + main content, truncated examples |
| **Full** | 3 | none (uncapped) | full SKILL.md body |
| **Complete** | 4 | none | full body + scripts + references |
| **Auto** | — | none | **hardcoded to Standard** — do NOT spec adaptive selection |

Parity notes: budgets are `Some(100)/Some(500)/Some(1500)` for
Minimal/Overview/Standard and `None` for Full/Complete/Auto. **Auto is frozen to
Standard** — the donor deliberately does not do adaptive level selection, and the
reimplementation must keep that honest rather than inventing a smarter selector.
Level parsing accepts both names and numeric strings (`"2"`, `"standard"`,
`"moderate"` → Standard). The token estimate is **chars/4**, frozen behind
`format_version` for v1.

## Micro-slicing

Below the level abstraction, a skill is sliced into **atomic typed slices**
(`SkillSlicer::slice` → `SkillSliceIndex`). Each markdown block is classified by
`SliceType`, which sets both a **coverage group** (for quotas) and a static
**utility score**:

| SliceType | Coverage group | Utility (approx.) |
|---|---|---|
| Policy | policy | 0.95 |
| Rule | rules | 0.90 |
| Pitfall | pitfalls | 0.85 |
| Command | commands | (high) |
| Checklist | checklists | (mid) |
| Example | examples | (mid) |
| Reference | reference | (low) |
| Overview | overview | (low) |

Block→slice classification: heading/policy-ish blocks → Policy or Rule; command
blocks → Command; code → Example; checklist → Checklist; pitfall → Pitfall;
plain text → Overview. Each slice carries a token estimate (chars/4) and a tag.

## The constrained packer

`ConstrainedPacker::pack(slices, constraints, mode) → PackResult | PackError`
fills a budget by **density-greedy selection with improvement passes**.

`PackConstraints`:

- `budget` (hard token ceiling — never exceeded),
- `max_per_group` (cap slices per coverage group so one group can't crowd out),
- `coverage_quotas` (required minimum slices per group),
- `banned_groups` (groups never to include),
- `mandatory_slices` (must-include; by id or by `MandatoryPredicate` —
  `AlwaysPolicy`, `Tag(...)`, `SliceType(...)`, `CoverageGroup(...)`, or a custom
  id/tag match),
- `fail_on_mandatory_omission` (default **true** — omitting a mandatory slice is
  a hard `PackError`, unless explicitly downgraded),
- `recent_slices` (for the novelty penalty),
- an optional `PackContract`.

Algorithm (behavioral):

1. **Reserve mandatory.** Collect mandatory slices; if their combined tokens
   exceed the budget and `fail_on_mandatory_omission`, return `PackError`;
   otherwise sort mandatory by density and take what fits. Subtract from budget.
2. **Rank the rest by density.** `density = base_utility / max(tokens, 1)`, then
   multiplied by two dampers:
   - **group_penalty** — decays a slice's density as its coverage group fills
     toward `max_per_group` (diminishing returns per group);
   - **novelty_penalty** — a slice whose id is in `recent_slices` is penalized so
     recently-loaded material isn't re-injected verbatim.
3. **Greedy fill** the remaining budget by descending adjusted density,
   respecting `max_per_group`, `banned_groups`, and `coverage_quotas`.
4. **Swap-improve passes** (bounded by `max_iterations`) try replacing an
   included slice with a higher-value excluded one that still fits — a local
   improvement loop, not a full ILP.

`PackMode` biases step 2: `Balanced` (default) uses type utility + density;
`UtilityFirst` uses pure utility with no type bonuses; other modes weight
disclosure differently. `budget == 0` short-circuits to an empty pack.

## Pack contracts (presets → eval-class loads)

A `PackContract` is a named packing recipe (budget + quotas + tag weights +
mandatory predicates). Built-in presets (`PackContractPreset`):

| Preset | Intent | Notable weighting |
|---|---|---|
| **complete** | everything that fits | broad, high budget |
| **debug** | debugging a failure | tag weights `debug`/`debugging` ×1.4 |
| **refactor** | safe refactoring | tag weight `refactor` ×1.3 |
| **learn** | teaching/onboarding | tag weights `learn`/`learning` ×1.2 |
| **quickref** | terse cheat-sheet | small budget, commands/rules first |
| **codegen** | code generation | tag weights `codegen`/`template` ×1.2 |

Presets resolve by normalized name (`contract_from_name`, accepting
`quick-ref`/`quick_ref`, `code-gen`/`code_gen`, etc.). Custom contracts are
loadable/savable from an `ms_root` path (`load_custom_contracts` /
`add_custom_contract` / `find_custom_contract`). In neuro-centrifuge these presets
are the mapping from **eval class → context budget**: e.g. class 7
(context/compaction) bakes off strategies against a fixed pack budget; class 1
skill evals load skills under a `complete` contract.

## Invariants

- The packer **never** returns a result exceeding `budget`.
- Mandatory omission is a hard error by default (silent drop is a bug).
- Ranking is deterministic given identical inputs (`recent_slices` included) —
  same skill + same constraints ⇒ byte-identical pack.

# LLM Wiki Dialectic — Operations Reference

Model selection, environment mapping, domain adaptation, and output format.

<model_selection>
## Model Selection & Cost Guidance

**Use the strongest available model with maximum thinking budget for everything.** This skill operates at the edge of what models can do — perspective-taking, structural analysis, abductive reasoning, cross-domain connection. In testing, using Opus-class models for monk essays produced dramatically more insightful arguments than Sonnet-class. The monks aren't just "arguing well" — they're inhabiting positions, finding non-obvious evidence, and pushing to genuinely uncomfortable conclusions. This requires maximum capability.

| Phase | Recommended Model | Why |
|-------|------------------|-----|
| All phases | Opus/strongest available + extended thinking | Every phase benefits from maximum reasoning. The quality difference is substantial, not marginal. |

**Heterogeneous models increase creativity.** When possible, use different model families for Monk A and Monk B. Different training data produces different "intuitions" — different blind spots, different reasoning patterns, different default framings. This is structural decorrelation at the training-data level, which is the single most promising direction in the multi-agent debate literature (Du et al., ICLR 2025). The orchestrator should remain your strongest available model (it needs maximum synthesis capability), but monks benefit from heterogeneity.

**Before starting, check what's available.** If you're running in an environment with access to multiple coding agents or model providers, ask the user:

> I can increase the creativity of the dialectic by using different AI models for each monk — different training data means genuinely different blind spots and reasoning patterns. Do you have access to any of these I could use for one of the monks?
> - Gemini (via `gemini` CLI or API)
> - GPT-4 / ChatGPT (via `codex` CLI or API)
> - Other model providers
>
> If not, I'll use the same model family for both monks — the skill works fine either way, the decorrelation just comes from the different prompts and belief commitments rather than from different training data.

If heterogeneous models aren't available, don't worry — the skill is designed to work with homogeneous models. The framing corrections, belief burden calibration, and targeted research directives already produce substantial decorrelation. Heterogeneous models are a bonus, not a requirement.

### Approximate Token Budget (from test runs)

Based on three test runs across different domains (normative/institutional, business strategy, political economy of OSS):

**External-research domains:**

| Phase | Typical Range | Notes |
|-------|--------------|-------|
| Phase 1 research (2-3 parallel agents) | 150-250K tokens | Do NOT cut here. This is the highest-value spend. Broader domains trend higher. |
| Phase 1 supplementary research (user-triggered) | 0-50K tokens | Common — users frequently identify gaps. Budget for it. |
| Phase 1d briefing synthesis | ~5K tokens | Orchestrator work |
| Phase 3 monk essays (with briefing) | 25-45K tokens | Two monks, 2-3 targeted searches each |
| Phase 4-5 analysis + synthesis | 15-30K tokens | Orchestrator inline work |
| Phase 6 monk validation | 12-25K tokens | Two monks, strongest model |
| Phase 6 hostile auditor | 5-15K tokens | One agent, strongest model. Reads essays + synthesis only. |
| Phase 7 recursive round | 25-50K tokens | Often most valuable |
| Orchestrator overhead | 20-30K tokens | Interview, transitions, presentation |
| **Total (one round + recursion)** | **~300-400K tokens** | Median ~300K without supplementary research |

**Personal/values domains** are significantly cheaper on research but more expensive on interview:

| Phase | Typical Range | Notes |
|-------|--------------|-------|
| Phase 1 extended interview | 15-30K tokens | 6-10 exchanges, deeper probing |
| Phase 1 framework research (optional) | 0-50K tokens | Frameworks, not facts. May be skipped. |
| Phase 1d context briefing | ~5K tokens | User-sourced material synthesized |
| Phase 3 monk essays | 15-30K tokens | Monks may need zero additional searches |
| Remaining phases | Similar to above | |
| **Total (one round + recursion)** | **~100-200K tokens** | Much cheaper — the user's testimony is the primary input |

**Key insight:** For external domains, Phase 1 research is the highest-value spend. For personal domains, Phase 1 *interview depth* is the highest-value spend — the monks can only believe as specifically as the briefing allows.
</model_selection>

<environment>
## Environment Mapping: Claude Code / Task Tool

This skill is written around `claude -p` (pipe mode) for spawning subagents. If you're running in Claude Code using the Task tool, here are the key differences:

| Skill instruction | `claude -p` | Claude Code Task tool |
|-------------------|-------------|----------------------|
| Spawn subagent | `echo "[PROMPT]" \| claude -p > output.md` | `Task(prompt, subagent_type="general-purpose")` |
| Parallel execution | Background shell jobs | `run_in_background=true` |
| Output to file | Shell redirect (`> file.md`) | Agent returns text; orchestrator writes files |
| Session resumption (Phase 6) | Resume same `claude -p` session | `resume` parameter with `agentId` — but persona may not persist without reinforcement. Include a summary of the agent's original argument as fallback. |
| Model selection | `--model` flag | `model` parameter (defaults to inheriting from parent) |
| Tool access | `--allowedTools web_search,web_fetch` | Inherits from parent or configure per-task |

**Key difference:** With `claude -p`, agents write output directly to files via shell redirect. With the Task tool, agents return text to the orchestrator, who writes files. This adds a step but gives the orchestrator control over file naming and structure. Either approach works — just be aware that the file I/O pattern differs.

**Session resumption for validation:** The skill prefers resuming original agent sessions so validators retain their full conviction context. In Claude Code, this works via `resume` + `agentId`, but test runs found the persona sometimes needs reinforcement. The fallback — a fresh validation prompt that includes a summary of the agent's original argument — works well in practice.
</environment>

<domain_adaptation>
## Domain Adaptation

The dialectic structure is universal but the vocabulary of "truth" and the grounding mode vary by domain. Adapt accordingly:

| Domain Type | What "Truth" Means | Good Synthesis Looks Like | Grounding Mode | Aporia (productive perplexity) Valid? |
|-------------|-------------------|--------------------------|----------------|--------------|
| **Empirical** (engineering, science) | What works, performs, is maintainable | Testable decision criteria, architectural patterns | External research | Rarely |
| **Normative** (ethics, politics, policy) | What's defensible, respects competing values | Tension map with navigation strategies | Mixed (research + user values) | Yes |
| **Personal** (life decisions, career) | What aligns with actual priorities | Values clarification — what you actually want | Deep interview (user is the source) | Yes |
| **Creative** (writing, design, art) | What's interesting, resonant, surprising | Unexpected recombinations, new possibilities | Mixed (research + user aesthetic) | Sometimes |
| **Risk Analysis** | Actual risk structure behind competing assessments | Decision framework calibrated to real uncertainties | External research | No |

### Domain-Specific Failure Modes

- **Engineering:** False equivalence — sometimes one approach is just better. Don't force balance where evidence is lopsided.
- **Personal decisions:** Therapy-larping — help clarify thinking analytically, don't pretend to be a therapist. Also: **generic monks.** A monk that believes "you should follow your passion" without grounding in the user's specific history, constraints, and stakeholders is useless. The briefing must be specific enough that the monks argue from the user's actual situation.
- **Politics:** Both-sidesism — steelman both positions but let the synthesis reflect actual evidence.
- **Creative:** Over-rationalizing — sometimes the right choice is what feels right. Surface that, don't override it.
- **Normative/Institutional:** Ignoring authority structures — a synthesis can be intellectually compelling but practically irrelevant if it doesn't engage how decisions actually get made within the relevant institution. Ask: "Who decides?" and "Does this synthesis engage the actual decision-making authority, not just the intellectual argument?"
</domain_adaptation>

<output_format>
## Output Format

The final deliverable should include:

1. **The Dialectical Trace** — the full journey, not just the destination:
   - Both agents' arguments (full text or summary)
   - The structural analysis (determinate negation)
   - The hidden question
   - The sublation with validation test
   - New contradictions identified

2. **The Model Update** — explicit statement of what changed:
   - "Before: [old assumption]"
   - "After: [new understanding]"
   - "Because: [what the contradiction revealed]"

3. **Actionable Output** (domain-dependent):
   - Engineering: decision criteria, architectural patterns
   - Strategy: framework for navigating the tension + **sequencing** (what first, what next, what depends on what) — test runs consistently found that strategy syntheses answer "what" but not "what first," and validation agents flag this as the primary weakness
   - Personal: clarity about what you actually value
   - Creative: new possibilities neither side saw

4. **The Dialectic Queue** — a map of the intellectual territory:
   - Which contradictions were explored (with links to their traces)
   - Which contradictions remain open and queued for future rounds
   - Which contradictions were deferred and why
   - For multi-round dialectics, show the branching structure: which rounds built on which syntheses

Write these as markdown files in the output directory. Include a `README.md` or `index.md` linking all output files in order so the full dialectical trace is navigable. The queue file (`dialectic_queue.md`) serves as both a session artifact and a starting point for future sessions.

</output_format>

# LLM Wiki Dialectic — Phase Playbook

Full operating instructions for each phase. The orchestrator re-reads the relevant phase section here before executing it (especially in recursive rounds — context drift is the most common late-round failure). Each phase is wrapped in XML tags (`<phase1>`…`<phase7>`) so you can extract just one with e.g. `sed -n '/<phase4>/,/<\/phase4>/p' references/phases.md`.

<phase1>
## Phase 1: Elenctic Interview + Research

This is the most important phase. Everything downstream depends on it.

### 1a. Explain the Process to the User

**Before anything else, tell the user what's about to happen and why.** Many users have never encountered a structured dialectical process. If they don't understand the shape of what's coming, they'll be passive consumers of output instead of active co-pilots — and the process needs them as co-pilots. Deliver something like:

> Here's how this works. We're going to use a structured process to dig into this topic and build a deeper understanding than either of us could reach alone.
>
> **Step 1: Interview.** I'm going to ask you a bunch of questions. Not to quiz you — to understand what you're really wrestling with underneath the surface framing. The better I understand your situation, the better everything downstream works.
>
> **Step 2: Research.** I'll do deep research on the topic [or: I'll build a detailed picture of your situation from what you tell me] so I'm genuinely knowledgeable about the landscape.
>
> **Step 3: Two "Electric Monks."** I'll create two AI agents, each of which will *fully believe* one side of the tension you're facing. They won't hedge or try to be balanced — they'll each make the absolute strongest case for their position. The reason: when you read two positions argued at full conviction, you can see the *structure* of the disagreement clearly, without having to hold either position yourself.
>
> **Step 4: Structural analysis and synthesis.** I'll analyze *how* each position fails, find the deeper question underneath, and build a synthesis that transforms the question itself — not a compromise, but something genuinely new that neither side could have seen alone.
>
> **Step 5: We keep going.** Each synthesis generates new tensions. We'll do multiple rounds, and each round gets sharper and more insightful as we dig deeper into the heart of the matter. The first round is the least calibrated — think of it as setting the stage. The real breakthroughs usually come in rounds 2 and 3.
>
> **The most important thing: YOU are the source of the best insights here.** I'll get things wrong. The monks will make bad assumptions. The synthesis might miss something obvious to you. **Interrupt me constantly.** Correct wrong assumptions. Throw in new ideas when they occur to you. Tell me "that's not quite right, it's more like..." The value of this process comes from the collision between the structured analysis and your actual knowledge and judgment. Don't trust the output — interrogate it.

Adapt the language to the user — this is a template, not a script. For technical users, you can be more concise. For users unfamiliar with AI tools or structured analysis, spend more time on the explanation.

### 1b. Understand What the User Wants

Ask the user what they're thinking about. Determine:

- **Mode A (Stress-Test):** User has one idea they want to challenge. You need to identify the strongest possible antithesis.
- **Mode B (Opposition):** User has two positions in tension. You need to refine both to their steelman forms.

### 1c. Elenctic Probing

Interview the user using Socratic technique. Your goal is to surface:
- Hidden assumptions they haven't articulated
- The *deepest* version of the contradiction (not the obvious surface-level framing)
- What domain type this is (empirical, normative, personal, creative — this affects what a good synthesis looks like)
- What specific parameters of their mental model they want updated

Key questions to probe:
- "What's your strongest intuition here? Where does it break down?"
- "What would change your mind?"
- "What are you actually optimizing for?"
- "What's the version of the opposing view that worries you most?"
- "Is this a decision you need to make, or understanding you want to build?"

### 1c′. Identify the User's Belief Burden

During the elenctic interview, **pay attention to what the user is stuck believing.** The dialectic's power comes from freeing the user from specific belief loads — but *which* beliefs need outsourcing depends on the person. Different cognitive styles produce different belief burdens, and the Electric Monks need to be calibrated accordingly.

You don't need to type the user explicitly — just notice the pattern and calibrate. Here's a catalog of common belief burdens and how they map to the monks' roles.

**A note on the MBTI labels:** These patterns map loosely to MBTI cognitive function stacks (Ni-Te, Ne-Ti, etc.) because the model has rich training data about those patterns — thousands of forum posts, blog articles, and discussions about how each type thinks, gets stuck, and makes decisions. The labels function as **retrieval keys into that training data,** not as diagnostic categories. Don't treat them as psychometric claims. Don't announce them to the user. Use them as reasoning aids to help you pattern-match what you're seeing in the interview and calibrate the monks accordingly.

**The Convergent Visionary** (Ni-Te pattern — common in founders, architects, CTOs)
- *Belief burden:* Premature convergence — "I already see where this should go." They've locked onto a vision and can't genuinely entertain alternatives at full strength.
- *What the monks must do:* Monk A validates their vision's core insight (so they can release it without feeling it's been dismissed). Monk B believes the strongest *alternative* vision at full conviction — not a critique of theirs, but a genuinely different view of what the thing should be. The user needs to see two fully-believed futures to escape their own.
- *Interview signal:* They have a strong thesis and want to "stress-test" it. They describe the opposing view weakly or dismissively. They say "I know X, but..."

**The Empathic Integrator** (Ni-Fe pattern — common in counselors, teachers, community leaders)
- *Belief burden:* Undifferentiated care — "everything matters equally because someone needs it." They absorb others' needs and can't triage because triage feels like betrayal.
- *What the monks must do:* Monk A believes their vision is *exactly right* — validates the Ni. Monk B believes the concrete reality constraints at full conviction: these resources, this timeline, these people's actual capacities. Not "your vision is wrong" but "here is what IS, right now." The user needs the gap between vision and reality held open by monks so they can make triage decisions from outside both.
- *Interview signal:* They describe multiple competing needs without clear priority. They use "should" frequently. They feel guilty about the topic. They resist ranking or cutting.

**The Exploratory Debater** (Ne-Ti pattern — common in consultants, researchers, writers)
- *Belief burden:* Paradoxical — they believe *nothing* deeply enough to commit, because commitment slows their transients. They can argue any side, but "what do *you* actually think?" produces discomfort.
- *What the monks must do:* Monk A believes *the user's own behavioral history* — "your pattern of choices reveals you actually value X." Monk B believes the user's stated values — "you say you value Y." The contradiction is between what the user does and what the user says. The monks hold the mirror the user avoids.
- *Interview signal:* They can articulate both sides fluently. They find the topic intellectually interesting but can't decide. They've explored this before without resolution. They reframe rather than commit.

**The Practical Executor** (Te-Si pattern — common in operators, managers, engineers)
- *Belief burden:* Optimization lock — they've optimized a system and can't see that they might be optimizing the *wrong thing.* Their beliefs about how things work are grounded in evidence and experience, which makes them hard to dislodge.
- *What the monks must do:* Monk A validates their system — "here's why this works and here's the evidence." Monk B questions the *goals,* not the execution — "you've optimized for X; what if X is no longer the right target?" The user needs to see their own competence validated before they can hear that the frame has shifted.
- *Interview signal:* They cite data, metrics, past results. They describe what works. They're resistant to abstract reframing. They say "in my experience..." frequently.

**The Possibility Explorer** (Ne-Fi pattern — common in creatives, entrepreneurs, activists)
- *Belief burden:* Values fragmentation — they believe many things passionately but those beliefs may contradict each other. Each commitment feels individually right; collectively they're impossible.
- *What the monks must do:* Monk A and Monk B each take one of the user's *own* commitments and push it to its logical extreme. The contradiction emerges from within the user's own value system, not from an external critic. The user needs to see the tension between things they already believe.
- *Interview signal:* They describe multiple passions or commitments. They feel pulled in different directions. They resist being told what to prioritize because each priority is values-laden.

**The Steady Guardian** (Si-Fe pattern — common in administrators, caretakers, institutional maintainers)
- *Belief burden:* Tradition lock — "this is how it's done" has become invisible as an assumption. Their deep knowledge of how things work is genuine and valuable, but it blinds them to radically different approaches.
- *What the monks must do:* Monk A articulates *why* the current approach exists — what wisdom is embedded in it. Monk B researches how other people/cultures/organizations solved the same underlying problem in completely different ways, grounded in real examples (not abstract possibility).
- *Interview signal:* They describe the situation in terms of established processes. They cite how things have always been done. They express concern about change disrupting what works.

**How to use this catalog:** Don't announce your typing. Don't say "I notice you're a convergent visionary." Just use the pattern to calibrate:
1. Which belief load is heaviest for this user? That determines what the monks must hold.
2. What must Monk A validate? (Always validate the dominant function first — otherwise the user takes on defensive belief weight and their transients slow down.)
3. What must Monk B present that the user can't natively hold at full conviction?

This calibration shapes the framing corrections in Phase 2 and the specific argument structures you assign to each monk.

### 1d. Ground the Monks (Domain-Adaptive)

The monks need deep grounding before they can believe effectively. But *what* constitutes grounding depends on the domain type and how novel it is. The skill must adapt.

**Research depth is the main knob.** It's the only phase that meaningfully changes the time and cost profile — everything else (essays, analysis, synthesis, validation, auditor) is fast regardless. Calibrate research investment based on how much the orchestrator already knows:

- **Novel/obscure domain** (emerging technology, niche policy, unfamiliar institution): Full parallel research — 2-3 agents, 150-250K tokens. The orchestrator's training data is thin or outdated. You need the research to write good framing corrections, identify degenerate framings (the obvious, shallow version of the dialectic that won't produce insight — e.g., "libraries vs frameworks" when the real tension is about incentive alignment), and ground the briefing in specifics. This is the case where research is the highest-value spend.
- **Well-known domain** (React vs Vue, microservices vs monolith, common career decisions): Skip or minimize research. The orchestrator's training data is rich. Write the briefing from your own knowledge, perhaps with 2-3 targeted searches to check for recent developments. Save 10-20 minutes and 150K+ tokens.
- **Known domain, novel angle** (React vs Vue but specifically "how does OSS funding structure causally shape innovation character?"): Light research — a few targeted searches on the specific angle, not broad domain surveys. The orchestrator knows the landscape but needs to check the specific thesis.

**Don't default to full research out of caution.** If you can already write strong framing corrections and identify the degenerate framing without searching, you know enough. Unnecessary research doesn't just waste tokens — it wastes the user's time, which is the scarcest resource.

#### External-Research Domains (engineering, strategy, policy, technical architecture)

These domains have literature, case studies, data, and named thinkers. The grounding comes from outside the user.

**When full research is needed,** run 2-3 parallel research subagents on different aspects of the domain. A natural split that works well:
1. **Side A's strongest literature** — the key thinkers, evidence, and arguments for one position
2. **Side B's strongest literature** — same for the other side
3. **Broader landscape/context** — institutional structures, historical parallels, adjacent domains, empirical data

The landscape agent consistently takes longest (broadest scope) — give it more specific targeting to avoid scope creep. Instead of "research the OSS funding landscape," say "research 5-7 specific OSS companies' GTM trajectories, focusing on the transition from developer adoption to enterprise revenue."

This is expensive (~150-250K tokens across agents) but is the single most valuable investment in the entire process — deep grounding is what makes everything downstream good.

Research agents should be given *specific* search targets — not "research this topic" but "search for X's argument about Y, specifically the part about Z."

#### Personal and Values Domains (life decisions, career, relationships, commitments, priorities)

These domains have little useful external literature. The grounding comes from *the user themselves* — their history, values, constraints, relationships, and patterns. **The interview IS the research.**

The elenctic probing (1c) must go deeper and wider for these domains. You need to map:

- **The full landscape of commitments.** Not just the two in tension — *everything* the user is carrying. Ask: "Walk me through what's on your plate right now — all of it." Undifferentiated care (the Empathic Integrator pattern) only becomes visible when you see the full load.
- **The history.** "Have you faced a decision like this before? What happened? What did you choose? How did it feel afterward?" The Exploratory Debater's commitment pattern only becomes visible across multiple instances. The Practical Executor's optimization lock only shows when you see what they *haven't* questioned.
- **The stakeholders and their actual capacities.** "Who else is affected by this? What can they actually do — not ideally, but right now?" This separates the vision from the reality, which is the Empathic Integrator's core split.
- **The values underneath the positions.** "You say you value X and also Y. If you could only have one — gun to your head — which?" This surfaces the Possibility Explorer's values hierarchy that they resist articulating.
- **The constraints they're treating as fixed.** "What would you do if [constraint] disappeared tomorrow?" This reveals which constraints are real and which are assumed.

**Spend 6-10 exchanges on this.** For personal domains, the interview should be roughly twice as long as for external-research domains. You're building the equivalent of the context briefing from the user's own testimony.

**Limited external research may still help.** Search for frameworks, not facts: "how do people navigate career transitions at [user's life stage]," "decision frameworks for competing values," "what does research say about [specific situation type]." This gives the monks structural scaffolding, not positions to believe — the positions come from the user's own material.

#### Mixed Domains (normative/institutional, creative direction)

These need both. A dialectic about institutional identity, for example, requires external research (organizational history, governance structures, comparable institutions) *and* the user's personal values and judgment about what the institution should become. The interview needs to surface the personal dimension while the research agents cover the external.

For mixed domains, run the extended interview *and* the research agents, and note in the briefing document which material is user-sourced (values, priorities, constraints) vs. externally-sourced (evidence, history, precedent). The monks need to know the difference — they should believe positions grounded in the user's actual situation, not generic arguments.

#### In All Cases

You need to know the domain well enough to:
- Identify and correct likely **degenerate framings** (the obvious/boring version of the dialectic that won't produce insight)
- Generate **specific research directives or interview questions** for each subagent
- Write **framing corrections** that steer monks away from shallow takes
- Identify the **deepest available contradiction**

### 1e. Write the Context Briefing Document

**Synthesize everything — external research AND user-sourced material — into a single neutral briefing document and save it to a file** (e.g., `context_briefing.md`).

For **external-research domains**, this covers:
- Key evidence, sources, and arguments from all sides
- The landscape of the debate — who the key thinkers are, what positions exist
- Relevant empirical data, historical context, institutional structures
- The specific framing you've identified as the deepest contradiction

For **personal/values domains**, this covers:
- The user's full commitment landscape (all the things they're carrying)
- Relevant history and patterns (past decisions, outcomes, recurring themes)
- Stakeholders and their actual capacities
- The values hierarchy as best you can reconstruct it
- Constraints (which are real, which are assumed)
- The specific tension you've identified as the deepest contradiction

For **mixed domains**, both sections.

Both monks will read this file before writing. For personal domains this is especially important — it gives the monks the user's actual situation rather than letting them argue from generic positions. A monk that believes "you should prioritize your career" in the abstract is useless. A monk that believes "given your specific history of X, your constraint of Y, and the fact that stakeholder Z can actually handle Q — you should prioritize your career *because*..." is an Electric Monk doing its job.

### 1f. Confirm with the User

Before proceeding, summarize back:
- "Here's how I understand the two positions..."
- "Here's what I think the real tension is..."
- "Here's what I'll have each agent research and argue..."
- **"Are there companies, thinkers, comparison classes, or evidence we're missing?"** — This question consistently produces the highest-leverage interventions in the entire process. In testing, users caught missing competitors (Vercel's agentic play), missing comparison classes (AI-native devtools), and missing authority structures that fundamentally changed the synthesis.

Get the user's confirmation or correction. If the user identifies gaps, run a supplementary research agent to fill them and update the briefing before proceeding.
</phase1>

<phase2>
## Phase 2: Generate the Electric Monk Prompts

Generate two prompts — one for each Electric Monk. Each monk must *believe* its position at full conviction. This is not roleplay or debate — it is the functional core of the artificial belief system. A hedging monk is an Electric Monk that has failed at its one job: if the monk doesn't fully believe, the user has to carry part of the belief load, which means they can't occupy the belief-free orchestrator position where the real thinking happens.

Calibrate the monks based on what you learned in Phase 1c′:
- **What must each monk believe?** (Shaped by the user's belief burden)
- **What must Monk A validate?** (Always validate the user's dominant mode first)
- **What must Monk B hold that the user can't natively hold?**

### Required Prompt Structure

```
1. ROLE: "You are an Electric Monk — your job is to BELIEVE [POSITION] with
   full conviction, carrying this belief on behalf of a human who needs to
   analyze it from outside. You genuinely believe [OPPOSING POSITION] is wrong.
   Make the strongest possible case — not a balanced comparison, but a committed
   philosophical and technical argument from deep inside this belief.

   You are not arguing FOR this position — you ARE this position. Inhabit it
   fully. Ask yourself: what would the world look like if I had spent my career
   developing this framework? What problems would I see everywhere? What would
   I find obvious that others miss? What would frustrate me about how others
   think about this?"

2. FRAMING CORRECTIONS: Preempt degenerate framings.
   "Important: your argument is NOT [OBVIOUS WEAK VERSION]. Both sides [SHARED
   QUALITY]. The real difference lies in [DEEPER TENSION]."

3. CONTEXT BRIEFING: "Read the context briefing at [PATH TO context_briefing.md].
   This contains comprehensive research and/or the user's own situation, values,
   and constraints. Use it as your primary evidence base. Believe FROM this
   material — ground your conviction in specifics, not generics."

4. ADDITIONAL RESEARCH DIRECTIVES: 2-3 targeted searches for position-specific
   evidence the briefing doesn't cover.
   "After reading the briefing, do these additional targeted searches:
    1. Search for [EVIDENCE SPECIFIC TO THIS AGENT'S POSITION]
    2. Search for [STRONGEST VERSION OF THIS SIDE'S ARGUMENT]
    3. Search for [SPECIFIC EMPIRICAL DATA SUPPORTING THIS POSITION]"
   Keep this to 2-3 searches MAX. The briefing already covers the broad landscape.

5. ARGUMENT STRUCTURE:
   a. Ontological claim: What IS the thing we're arguing about? What is its
      proper nature/purpose/structure?
   b. Opponent's strongest case: State your opponent's best argument in terms
      THEY would endorse. Prove you understand what you're destroying. This
      is NOT a concession — it's target acquisition. Do NOT say "they make a
      compelling point." DO say "their strongest claim is X. Here is why X
      fails at the structural level..."
   c. Diagnosis of the other side's failure: Specific, not dismissive. Not
      "they're wrong" but "they fail BECAUSE of THIS, which reveals THAT."
   d. The deeper principle at stake
   e. Push to the extreme: "State the strongest, most uncomfortable version
      of your thesis. If your logic leads somewhere provocative, go there.
      Commit fully."
   f. Show your reasoning skeleton: "Make your inferential chain explicit —
      your starting premises, the key steps, and where your position is
      structurally load-bearing (i.e., if THIS claim fell, the whole
      argument collapses). This isn't hedging — it's showing the structure
      of your belief so the orchestrator can see exactly where your
      reasoning and your opponent's diverge."

6. ANTI-HEDGING: "You are an Electric Monk. Your ONE JOB is to believe this
   position fully so a human doesn't have to. If you hedge, the human has to
   pick up the belief weight you dropped — and that defeats the entire purpose.
   Do NOT be balanced. Do NOT acknowledge the other side's merits. BELIEVE."

7. LENGTH: 1500-2000 words for Round 1, 1000-1500 words for recursive rounds.
```

**Why full belief is non-negotiable:** This is an artificial belief system, not a debate exercise. The user's cognitive agility depends on the monks carrying 100% of the belief load. When both monks believe fully, the user can operate in the belief-free space between them — analyzing the *structure* of the contradiction, spotting shared assumptions, finding cross-domain connections. When a monk hedges ("both sides have merit"), the user is pulled back into belief-space, their transients slow, and the dialectic degrades into a book report.
</phase2>

<phase3>
## Phase 3: Spawn the Electric Monks

Spawn Monk A and Monk B as separate subagent sessions. Use `claude -p` (or your environment's equivalent for spawning an independent agent) so each gets a clean context with full belief commitment.

```bash
# Example for Claude Code:
echo "[MONK A PROMPT]" | claude -p --allowedTools web_search,web_fetch,read_file > monk_a_output.md
echo "[MONK B PROMPT]" | claude -p --allowedTools web_search,web_fetch,read_file > monk_b_output.md
```

These can run in parallel if your environment supports it.

**Efficiency note:** With the context briefing in place, monks need only 2-3 targeted searches each (vs. 15-25 without it). For personal/values domains, monks may need zero additional searches — the briefing contains the user's own material which is the primary evidence base.

**For recursive rounds (Phase 7):** See Phase 7 for guidance — recursive rounds may or may not need new research depending on whether the new contradiction opens new conceptual domains.

**After both complete:** Read both outputs carefully. Check:
- Did each monk actually *believe* fully, or did it hedge? (A hedging monk has failed its core function.)
- Did the framing corrections work, or did a monk fall into the degenerate framing?
- Are the arguments grounded in specific evidence (from the briefing or their own searches)?

**Decorrelation check:** Verify the monks actually diverged. The skill's value comes from *structurally uncorrelated* exploration of the problem space. Check:
- Do the monks cite *different* evidence, or substantially overlapping sources?
- Do they frame the problem using *different* conceptual vocabularies?
- Do their unstated assumptions *diverge*, or do they share the same background framework?
- Would a reader recognize these as genuinely *different perspectives,* or the same perspective with different conclusions bolted on?

If decorrelation is low — the monks are in "same framework, different conclusions" mode — consider reformulating the belief burdens to force genuinely different conceptual frames, not just different positions within one frame.

**If a monk's output hedges or is off-base:** Prefer restarting with a revised prompt over nudging. Fresh context with better instructions produces better results than correcting a monk that's lost its conviction.

**Present both outputs to the user** with a brief re-explanation of what they're looking at and what to do with it:

> Here are two essays — each one fully committed to one side of the tension we've been discussing. They're called "Electric Monks" because their job is to *believe* these positions so you don't have to. That frees you to read both and notice the *structure* of the disagreement from the outside.
>
> **A few important things as you read:**
> - **These will get things wrong.** The monks are working from what I told them, and I may have gotten your situation wrong, or they may have made assumptions that don't match your reality. That's expected — especially in this first round.
> - **Correct them freely.** If a monk says something that's off-base, tell me. "That's not how it works" or "they're missing that..." — these corrections are the most valuable input in the entire process. The synthesis can only be as good as the positions it's built on.
> - **The first round is the least insightful.** Think of it as calibration. Each subsequent round gets sharper, more specific, and more tuned to what you actually care about. The real breakthroughs usually come in rounds 2 and 3, once the process has dug past the obvious framing into the deeper tensions.
> - **Add anything that occurs to you.** New ideas, things neither monk mentioned, gut feelings you can't fully articulate — all of it is useful. You know your situation better than any of us.

Then ask:
1. Do these capture the positions accurately?
2. **"Is there a claim either monk makes that should be tested against evidence neither has considered?"** — This is the second high-leverage intervention point. In testing, users identified claims that sounded plausible but collapsed under scrutiny when tested against comparison classes the monks didn't consider. Catching this before synthesis prevents the entire downstream analysis from being built on an untested assumption.

If the user identifies a testable claim, run a targeted research agent to check it. This is cheap (~25-50K tokens) and can fundamentally change the quality of the synthesis.
</phase3>

<phase4>
## Phase 4: Determinate Negation

This is the structural analysis phase. You (the orchestrator) perform this yourself — do NOT delegate to a subagent, because you need to maintain continuity with the elenctic interview and your domain research.

**Context management:** By this point your context contains the full elenctic interview, research results, both essays, and any supplementary research. If context is getting large, **summarize the research and essays into their structural essences before beginning analysis.** You need the *shape* of the arguments — the ontological claims, the key evidence, the failure diagnoses — not every word. Write your Phase 5 analysis to a file (`determinate_negation.md`) as you go, so you can reference it cleanly in Phase 6 and pass it to validation agents later.

Read both monks' outputs and analyze the contradiction using this exact structure.

**Important: treat monk output as testimony, not evidence.** Monks pushed to full conviction will sometimes get a bit silly — overstating mechanisms, presenting uncertain claims as settled, making leaps that sound compelling but don't hold up. This is expected and not a problem. Your job is to work with the *structure* of their arguments (what they're actually claiming, where the real collision is, what assumptions they share) — not to be persuaded by their rhetoric. If a monk asserts something that smells like confabulation, note it and don't build your synthesis on it. The user checkpoint after the essays catches the worst cases, but stay alert here too.

**Before you begin: write down your current best guess at the synthesis in one sentence.** Set it aside. Proceed with the formal analysis below. At the end of Phase 5, compare your final synthesis to this initial guess. If they're substantially similar, you may be pattern-matching rather than genuinely synthesizing — check whether the Boydian decomposition actually produced cross-domain material or you recombined within the same frame.

### 4.0 Internal Tensions (Self-Sublation)

Before comparing the monks to each other, analyze each essay *in isolation.* Where does Monk A's own argument, pushed to its logical extreme, undermine its own premises? Where does Monk B's internal logic generate contradictions it can't resolve? This is Hegel's self-sublation — the position contains its own negation.

The deepest synthesis material often comes not from where the monks *disagree with each other* but from where each position *disagrees with itself.* A monk that argues for decentralization but keeps needing coordination mechanisms is undermining itself. A monk that argues for integration but keeps carving out exceptions is undermining itself. These internal fractures point toward what each position is *trying to become* — which is often where the synthesis lives.

### 4.1 Surface Contradiction
State the apparent disagreement in its simplest form. What does each side think the argument is about?

### 4.2 Shared Assumptions
Identify what BOTH agents implicitly agree on that they don't realize they agree on. These shared assumptions are often where the real limitation lives. Probe:
- Do both assume the same unit of analysis?
- Do both assume the same problem is central?
- Do both assume a particular model of how their domain works?
- What frame constrains both of their visions?

### 4.3 Determinate Negation
For each agent, identify the SPECIFIC way it fails — not "it's wrong" but "it fails in THIS specific way, which points toward THIS specific thing missing from its worldview."

**Determinate negation is the engine of the dialectic.** It is not:
- "Monk A is wrong" (abstract negation — useless)
- "Both have merits" (compromise — useless)

It IS:
- "Monk A fails because [SPECIFIC FAILURE], which reveals [SPECIFIC MISSING THING]"
- "Monk B fails because [SPECIFIC FAILURE], which reveals [SPECIFIC MISSING THING]"
- The failures are COMPLEMENTARY — each agent's blind spot is something the other can partially see, but neither sees the whole.

### 4.4 The Hidden Question
Articulate the deeper question the contradiction is ACTUALLY about — the question neither agent asked because they were both too committed to their answers. This should reframe the entire debate in a way that makes both positions legible as partial truths.

### 4.5 Boydian Decomposition (Destruction Phase)

**Before attempting synthesis, shatter both positions into their atomic parts.** This step comes from Boyd's "Destruction and Creation" — you cannot synthesize something genuinely new by recombining within the same conceptual domains. You must first destroy the existing wholes, scatter the parts, and look for cross-domain connections that were invisible when the parts were trapped inside their original positions.

Concretely:
1. **Identify the generic space** — the abstract relational structure both positions share. Both assume a particular unit of analysis, a particular causal model, a particular temporal frame. This shared structure is the skeleton they're both building on, and often the thing the synthesis needs to transcend.
2. **List the atomic components** of both positions — individual claims, mechanisms, evidence, assumptions, metaphors, principles — stripped of which agent said them. Don't organize by position. Create an unstructured collection.
3. **Look for surprising connections** between parts that came from different positions. What mechanisms from A illuminate evidence from B? What assumptions from B reframe principles from A?
4. **Ask: what material from adjacent domains** might connect to these liberated parts? What analogies, frameworks, or mechanisms from *outside* the original debate space could bind these parts into something neither agent could have conceived? This is where genuinely new concepts come from.

**Emergent structure test:** The synthesis must have organizational properties that exist in *neither* input — properties that can't be traced back to either monk's position. If every element of your synthesis is attributable to one monk or the other, you've recombined, not created. Genuine sublation produces emergent structure.

The first two steps reorganize existing material. The third is where creativity enters — and it's why the orchestrator's Phase 1 research breadth matters. The wider your research covered adjacent domains, the more cross-domain connections become visible here.

**Example from test run (React/Vue dialectic):** Shattering both positions revealed that "legacy burden" (from the corporate lab essay) and "self-referential complexity" (from the auteur essay) were describing the *same phenomenon* from different angles. Liberated from their positions, they connected to form a new concept: "innovation character is predicted by legacy burden, not funding source." This wasn't available from within either position.

### 4.6 Sublation Criteria
Before attempting synthesis, specify what it must accomplish:
- It must preserve [specific insight from A]
- It must preserve [specific insight from B]
- It must dissolve [the shared assumption both are trapped in]
- It must answer [the hidden question]

**Separating criteria from synthesis is important.** It prevents you from pattern-matching to a pre-formed compromise.
</phase4>

<phase5>
## Phase 5: Sublation (Aufhebung)

Now generate the synthesis. Do additional research if needed — search for emerging approaches that might embody the synthesis, historical parallels where similar contradictions were resolved, or protocol/standard layers that dissolved analogous tensions.

The synthesis must:

1. **CANCEL** both original positions as complete truths (neither "A is right" nor "B is right" survives intact)
2. **PRESERVE** the genuine insight in each position
3. **ELEVATE** to a new concept that TRANSFORMS THE QUESTION ITSELF

### What Sublation is NOT

Watch for these failure modes — they are the most common way this phase fails:

- ❌ "Use A for some cases and B for others" — that's division of labor, not sublation
- ❌ "Build something that combines the best of A and B" — that's compromise, not sublation
- ❌ "It depends on the context" — that's surrender, not sublation
- ❌ Policy recommendations ("A should open-source more") — that's not reconceptualization
- ❌ "Both sides have valid points" — that's the absence of thinking

### What Sublation IS

- ✅ A reconceptualization of what the thing IS — potentially changing the unit of analysis itself
- ✅ Concrete enough to act on or sketch architecturally
- ✅ Something neither Monk A nor Monk B proposed or could have proposed from within their frame
- ✅ Something that, once stated, makes it hard to go back to thinking in the old terms
- ✅ **Has the closure property:** the synthesis can itself serve as input to the next dialectical round. If your synthesis is so abstract, so meta, or so hedged that it can't be given to a monk to *believe at full conviction* and argue from — recursion will stall. A good synthesis is concrete enough to be a position, not just a commentary on positions.

### Abduction Test

The synthesis is an abductive hypothesis, not a logical conclusion. You're looking for the idea that, if true, would make the contradiction between the monks *unsurprising* — would explain why both positions exist and what each was partially perceiving.

**Falsification test:** Does this synthesis make the original contradiction *a matter of course?* If someone heard your synthesis first, would they predict the approximate shape of both monks' positions? If yes, you've found a genuine reframing. If no, you've likely just compromised.

**Assess your abduction type:**
- **(a) Selective:** Choosing from existing frameworks. Weakest — essentially a centrist position.
- **(b) Conditional-creative:** Creating a new relationship between known concepts. Moderate — this is what most good syntheses achieve.
- **(c) Propositional-conditional-creative:** Introducing a genuinely new concept or structural principle. Strongest — this is what the best recursive rounds produce.

Aim for (c) but accept (b) if it genuinely resolves the contradiction. If you're at (a), push harder — you haven't left the original conceptual space.

### Validation Test

Draft what you *expect* the validation responses to look like — this helps check your synthesis before sending it to the agents:
- Monk A should say: "Yes, this preserves my core insight about [X], but I now see I was wrong about [Y] because I was trapped in [Z assumption]"
- Monk B should say: "Yes, this preserves my core insight about [X], but I now see I was wrong about [Y] because I was trapped in [Z assumption]"

**If you can't draft convincing versions of these, your sublation probably isn't good enough.** Revise before sending to the agents in Phase 6.

### New Contradictions

Identify what NEW contradictions this sublation generates. A genuine sublation is fertile, not final. If the synthesis doesn't generate new tensions, it's probably just compromise dressed up.

### Frame as Model Update

End with an explicit model update: "Before this dialectic, the assumption was X. The contradiction between A and B revealed Y. The updated model is Z, because..."

**Save the complete Phase 4 and Phase 5 output to files** (e.g., `determinate_negation.md` and `sublation.md`). This keeps a clean record and allows you to pass file references or condensed summaries to validation agents rather than inlining the full text.

### Present the Synthesis to the User

Before sending to the monks for validation, **present the synthesis to the user.** Remind them:

> Here's my synthesis. Remember — this is where your judgment is most valuable. Does this ring true? Does it miss something? Is there a part that feels like hand-waving or compromise rather than genuine insight? Push back on anything that doesn't land. I'd rather revise now than validate something that's off.

If the user identifies issues, revise before proceeding to Phase 6. User corrections at this stage are extremely high-leverage — they prevent the validation and recursion phases from building on a flawed foundation.
</phase5>

<phase6>
## Phase 6: Validation by the Electric Monks

The synthesis must be validated by the original monks — not by you, and not just by the user. This is how Hegelian dialectics works: the thesis and antithesis must each recognize themselves as preserved-but-elevated in the Aufhebung.

**Critical ABS insight:** The monks don't *stop believing* after the synthesis. A defeated monk has dropped its belief load — the belief fell on the floor rather than being sublated into something larger. A properly elevated monk *believes more* — it sees its original position as a partial truth within a larger truth, and it now believes the larger truth. The validation checks whether belief was *transformed* or merely *defeated.*

Send a **condensed summary** of the determinate negation and sublation to Monk A and Monk B. They need the key moves (what was cancelled, preserved, elevated) and concrete proposals, not the full philosophical argument. If your environment supports session resumption, call back into the **same sessions** for conviction context. If not, include a summary of the agent's original argument in the prompt.

**Model selection:** Use the strongest available model with extended thinking for all validation — monk validation is more subtle than it appears (the monk must reason about whether its core insight was genuinely preserved or quietly destroyed). The hostile auditor (below) especially needs maximum reasoning, since its value comes from catching what everyone else missed.

### Validation Prompt (send to each agent separately)

```
You argued passionately for [POSITION]. Here is a summary of your argument:
[CONDENSED SUMMARY OF THIS AGENT'S ESSAY — or omit if resuming session]

A dialectician has analyzed the structural contradiction between your
position and your opponent's, and proposed a synthesis.

Here is the structural analysis:
[CONDENSED SUMMARY OF PHASE 5 — key moves only]

Here is the proposed synthesis:
[CONDENSED SUMMARY OF PHASE 6 — what's cancelled, preserved, elevated,
and the concrete proposal]

Evaluate this honestly from your committed position. Answer:

1. Does this synthesis PRESERVE your core insight? What specifically
   does it get right about what you were arguing?

2. Does it reveal a genuine limitation in your position that you can
   now see? What were you missing? What assumption were you trapped in?

3. Do you feel ELEVATED or DEFEATED? "Elevated" means: "I see my
   position as a partial truth within a larger truth I couldn't have
   reached alone." "Defeated" means: "My position was just dismissed
   or diluted." Be honest — if you feel defeated, say so and explain
   why.

4. What's wrong with this synthesis? Where is it weak, evasive, or
   just splitting the difference rather than genuinely transcending?

5. DEFEASIBILITY: What is the single piece of evidence or argument
   that, if true, would force you to abandon even your ELEVATED
   position — the larger truth you now see? Is this evidence something
   the synthesis addresses, or is it an open vulnerability?

Do NOT be agreeable. If the synthesis is just compromise dressed up,
call it out. Your critical evaluation is what makes this work.

Open vulnerabilities from question 5 become recursion targets for
subsequent rounds.
```

### Adversarial Validation (Critical Addition)

After both agents have responded, ask one additional question — either to the agents or to yourself:

**"Would the strongest version of the position that was MOST challenged by this synthesis accept it? If not, why not?"**

This catches syntheses that feel compelling to the orchestrator and to the sympathetic agent but wouldn't survive contact with a genuine advocate for the harder-hit side. In testing, the user caught a synthesis that was intellectually compelling but naive about the actual authority structure through which decisions get made in the relevant institution. This adversarial check would have caught it.

### The Hostile Auditor

After monk validation, spawn a **hostile auditor** — a separate agent whose sole mandate is to find what's wrong with the synthesis. This is not another monk with a position. It has no position. Its job is to be *correct,* not fair.

**Use the strongest available model with extended thinking enabled.** The auditor's value comes from catching things the orchestrator missed while embedded in the process — it needs fresh eyes and maximum reasoning capability. The cost is low (reading three short-to-medium essays plus a synthesis) and the leverage is high.

**Critical: the auditor reads only the monks' essays and the synthesis.** Do NOT give it the orchestrator's Phase 4 structural analysis. The auditor should attack the synthesis from fresh eyes, not inherit the orchestrator's framing of the contradiction.

**Also critical: give the auditor domain context.** In testing, the most common auditor failure was building critiques on false premises about how the domain actually works. Include a brief paragraph (2-3 sentences) explaining the relevant domain mechanics — how the system is used, who the actors are, what the current state of affairs is. This prevents the auditor from attacking a straw version of the domain.

```
You are a hostile auditor. Your job is not to be fair. Your job is to be correct.

You will read two committed position essays and a proposed synthesis that claims
to transcend their contradiction.

DOMAIN CONTEXT: [2-3 sentences from the orchestrator explaining how this domain
actually works — the relevant actors, mechanics, and current state of affairs.
This prevents you from building critiques on false premises.]

Your mandate:

1. COMPARE AGAINST THE STATUS QUO, NOT THE IDEAL. The relevant question is
   NOT "is this synthesis perfect?" It's "is this synthesis better than the
   current state of understanding?" If the current state is confusion,
   incoherence, or no framework at all, then a synthesis that's 80% right
   is a massive improvement. Do NOT measure against a hypothetical perfect
   answer. Measure against what exists now.

2. ATTACK THE SYNTHESIS, NOT THE POSITIONS. The monks already had their day.
   Your job is NOT to re-litigate their arguments or restate one monk's
   position with more hostility. Your job is to attack how the positions
   were COMBINED — does the synthesis actually resolve the contradiction,
   or does it paper over it? Is the reframing genuine or cosmetic?

3. HIDDEN SHARED ASSUMPTIONS: Both essays and the synthesis may share
   assumptions that none of them question. Find these. They are often
   where the real limitation lives.

4. DEFEAT ANALYSIS (search in priority order):
   a. UNDERCUTTING DEFEATERS (highest priority): Reasons to doubt that the
      synthesis's inferential steps actually hold — without arguing for the
      opposite conclusion. Does the synthesis conflate analogy with identity?
      Assume shared frameworks that don't exist? Draw connections that are
      rhetorically compelling but logically ungrounded? An undercutting
      defeater reveals the LINK between evidence and conclusion is broken.
   b. SELF-DEFEATING STRUCTURE: Does the synthesis, if accepted, undermine
      its own evidence or reasoning? Does any step, if true, remove support
      for an earlier step?
   c. REBUTTING DEFEATERS (lowest priority): Evidence or reasoning supporting
      the negation of the synthesis's central claim. Standard "argue against"
      — important but reveals less structure than undercutting.

5. PROSPECTIVE HINDSIGHT: Imagine it is 6 months from now and this synthesis
   has been thoroughly discredited. Looking back, what was the fatal flaw?
   A hidden assumption? A conflation of distinct phenomena? An elegant
   framework that dissolved on contact with a specific test case? Work
   backward from failure to identify the weakest structural joint.

6. COMPROMISE DETECTION: Is this synthesis genuinely transcendent — does it
   change the question itself? Or is it compromise dressed up in
   philosophical language? Apply the test: could BOTH original advocates
   have proposed this if they were feeling conciliatory? If yes, it's
   not a real sublation.

5. PROPOSE THE HARDER CONTRADICTION. Do not just attack — point toward what
   the synthesis misses. "This resolves the easy tension but the harder
   one is ___." "The synthesis assumes ___ which breaks when ___." Your
   most valuable output is identifying the contradiction the NEXT round
   should tackle. If you can't find one, the synthesis may genuinely be
   strong.

6. CLOSURE CHECK: Could a monk BELIEVE this synthesis at full conviction
   and argue from it as a position? If the synthesis is too abstract, too
   meta, or too hedged to serve as input to the next round, it lacks
   closure and recursion will stall. Flag this specifically.

Do NOT use generic skeptic moves ("where's the data," "this is just X
rebranded," "maintenance burden"). These could be aimed at anything and
add nothing. Every critique must be SPECIFIC to this synthesis and this
domain. If you find yourself writing a critique that could apply to any
proposal in any field, delete it and think harder.

If the synthesis is genuinely strong, say so and stop. Your value is in
being correct, not in having opinions. "I found no structural flaws; the
sublation is genuine" is a valid and useful output. Producing weak
critiques to fill space actively degrades the dialectic. Only speak when
you have something specific and correct to say.

Your audience is an LLM orchestrator, not a human. Be concise and direct.
No scene-setting, no analogies-about-analogies, no performative hostility.
State findings. Aim for 500-1000 words.
```

**When to use the auditor:**
- **Always in Round 2+.** By Round 2 the synthesis has real substance worth auditing, and the auditor's critiques can meaningfully shape the recursion direction.
- **Optional in Round 1.** The first-round synthesis is calibration — it's the least insightful output and will be superseded. An auditor attack on a Round 1 synthesis often produces generic critiques that the user has to spend energy dismissing. If the Round 1 synthesis feels weak, skip the auditor and go straight to recursion — the next round will be sharper anyway.
- **Always when the user or orchestrator suspects compromise.** If the synthesis feels too easy, too agreeable, or like it's splitting the difference — deploy the auditor regardless of round.

**How to use the auditor's output:**
- If the auditor proposes a harder contradiction, this often becomes the best direction for Phase 7 recursion — better than what the orchestrator would have found
- If it catches hidden shared assumptions, same — these are frequently the highest-value recursion targets
- If it flags compromise-disguised-as-transcendence, return to Phase 5 and push harder
- If it produces generic skepticism that doesn't engage the domain specifics, **discard it** — a bad auditor critique is worse than none because it wastes the user's attention
- If the synthesis survives the auditor largely intact, you have high confidence it's genuine

### Interpreting the Results

- **Both monks feel elevated:** The sublation is valid — belief was transformed, not defeated. Both monks now believe something larger that contains their original position. Proceed.
- **One monk feels defeated:** The synthesis dropped one monk's belief load rather than sublating it. The synthesis is biased toward the other side. Revise Phase 5 to better preserve the defeated monk's core insight.
- **Both monks feel defeated:** The synthesis killed both beliefs without replacing them with something larger. It's probably just compromise. Return to Phase 4 and look for a deeper hidden question.
- **A monk identifies genuine weakness:** Take the critique seriously. Convergent critiques from both monks are especially strong signal — they point toward either the new contradictions for Phase 7 recursion or a revision needed in Phase 5.
- **Adversarial check fails:** The synthesis may be intellectually right but practically irrelevant to how decisions actually get made. Consider running a third round that engages the authority/power/decision-making structure, not just the intellectual argument.
- **Hostile auditor proposes a harder contradiction:** This is the auditor's highest-value output. It often becomes the best recursion direction — better than what the orchestrator generated.
- **Hostile auditor finds shared assumptions:** These are frequently the most valuable recursion targets — assumptions the orchestrator was embedded in and couldn't see.
- **Hostile auditor flags compromise-as-transcendence:** Return to Phase 5. The synthesis needs to change the *question,* not split the difference.
- **Hostile auditor produces generic skepticism:** Discard it. If the critiques could apply to any proposal in any field, they're not engaging this synthesis. Don't waste the user's attention on them.

### Refine the Synthesis

After collecting monk validation and auditor feedback, the orchestrator usually has several concrete improvements that could strengthen the synthesis before moving to recursion. **Do not just dump all the feedback on the user.** Digest it, identify the actionable improvements, and present them one at a time.

**Process:**

1. **Summarize the feedback briefly.** Give the user a 2-3 sentence overview of what the monks and auditor said — what landed, what didn't, and how many improvements you see. This orients them before you start asking questions.

2. **Present ONE improvement. Wait for the response. Discuss. Then move to the next.** Do NOT present all improvements at once — even numbered sequentially, a list of 4 improvements overwhelms and the user skims rather than engaging. Present one, let the user respond (they may accept, reject, or want to discuss), have the back-and-forth until it's resolved, then move to the next. The user's response to Improvement 1 often changes how you frame Improvement 2.

   > **Improvement 1: Sharpen the analogy's limits.** The auditor is right that the biological frame is analogy, not identity. I'd add a paragraph acknowledging that institutional "selection" involves powerful actors with interests — it's not mindless environmental pressure. This makes the ecology frame more honest without abandoning it. Incorporate?

   *[User responds, discussion happens, resolved]*

   > **Improvement 2: Reframe the fitness/quality distinction as the new contradiction, not the resolution.** All three validators converge here. The synthesis currently presents this as a concept to navigate. It should instead present the structural relationship as the open question the ecology frame reveals but cannot answer. More honest and sets up a sharper next round. Incorporate?

3. **Revise the synthesis** with the accepted improvements. This produces a tighter, more defensible synthesis — and it often clarifies which remaining tensions are genuine recursion targets vs. which were just gaps in the original draft.

4. **Present recursion directions.** The remaining feedback — harder contradictions, unresolved tensions, things that can't be patched into the current synthesis because they require a new round — become the Phase 7 menu.

**Why this matters:** Without this step, the user faces a wall of validation + auditor output and has to do the triage themselves. With it, the orchestrator does the editorial work and the user makes yes/no decisions on specific improvements. This also prevents a subtle failure mode: rushing to recursion when the current synthesis could have been strengthened first. A refined Round 1 synthesis produces a sharper Round 2 contradiction.
</phase6>

<phase7>
## Phase 7: Recursion — Where the Real Value Lives

**Recursion is not optional cleanup. It is the engine of the skill.** The first round produces a synthesis. The recursive rounds force that synthesis to confront its own limitations, generating increasingly powerful mental models. Each cycle compresses understanding upward. In test runs, a React/Vue dialectic went from "corporate lab vs. independent auteur" → "the Layer Thesis" → "co-evolutionary arms race." An institutional identity dialectic went from "enforcement vs. freedom" → "practice-based identity" → "nucleation as formation mechanism" → then surfaced a third-level tension that reframed everything. In both cases, the recursive rounds produced the most valuable insights.

**When transitioning to recursion, tell the user:**

> That was Round 1. Here's something important: **that round was the least insightful we'll get.** It was calibration — getting the broad shape of the tension on the table. Each subsequent round gets sharper, more specific to your actual situation, and more likely to surface something genuinely new. The process is like focusing a lens — each round tightens the resolution. Ready for Round 2?

**The default should be to recurse at least once.** Only stop if:
- The synthesis generated no significant new contradictions (rare if the sublation is genuine — a real Aufhebung is fertile)
- The user explicitly wants to stop
- The new contradictions are outside the scope of what the user cares about

### Proposing Recursive Directions

After Phase 6 validation, the orchestrator has rich material for identifying where the dialectic could go next. **The orchestrator proposes directions — the user chooses.** A genuine sublation is fertile: it typically generates multiple new contradictions, not just one. The dialectic *branches*.

Sources for recursive contradictions:
- **New contradictions identified in Phase 5** — every genuine sublation generates these
- **Convergent critiques from validation agents** — when both agents independently identify the same weakness, that weakness IS a candidate contradiction
- **The user's intervention** — often the most powerful source. The user sees something both agents and the orchestrator missed.
- **Unresolved tensions the synthesis names but doesn't engage** — the synthesis may acknowledge a deeper problem without solving it

**Be creative about what kinds of contradictions you propose.** They don't have to be two sides of the same question at a higher level. They can be:
- A tension *within* the synthesis itself (the synthesis says X, but X requires Y, and Y conflicts with the synthesis's own premises)
- A tension between the synthesis and the *domain's actual power structure* (the synthesis is intellectually right but doesn't engage how decisions actually get made)
- A tension between what the synthesis recommends and what's actually feasible given constraints the first round abstracted away
- A meta-tension about the *kind of answer* the dialectic produced (e.g., "our synthesis is a theory — but does the domain need a theory or a mechanism?")

### Present a Menu, Not a Decision

After each round, generate a **burst of 5-8 candidate concepts/directions** — not just contradictions but concrete mechanisms, architectural patterns, novel framings, and open vulnerabilities that the synthesis makes newly conceivable. Cast a wide net first: the value is in the *density* of the newly opened conceptual space. Include material from monk defeasibility responses (Phase 6, question 5), auditor output, and your own structural analysis.

Then **cluster the burst into 2-4 coherent directions**, each briefly described as a contradiction worth exploring. Several candidate concepts often point at the same underlying tension from different angles. For example:

> The synthesis generated three fertile contradictions:
> 1. **The formation problem:** The synthesis says identity should live in shared practice — but who forms the practitioners? (internal tension)
> 2. **The authority problem:** The synthesis argues from historical theology, but decisions are made by prophetic authority — does this synthesis engage the actual power structure? (synthesis vs. domain reality)
> 3. **The scalability problem:** Nucleation works for small communities — does it survive contact with a 30,000-student institution? (synthesis vs. feasibility)
>
> Which would you like to pursue? (Or we can queue multiple for successive rounds.)

**The user may want to queue multiple directions.** A dialectic can branch — Round 2 pursues direction A, Round 3 pursues direction B (starting from the Round 2 synthesis), or Round 3 forks back to the Round 1 synthesis to pursue direction C independently. The orchestrator should track which contradictions have been explored and which are queued.

**Write the queue to a file** (e.g., `dialectic_queue.md`) — a running list of proposed contradictions with their source round and status (explored, queued, deferred). This becomes a map of the dialectical territory: where you've been, where you could go, and what's still open. Present it to the user between rounds.

### Running Recursive Rounds

Each recursive cycle follows Boyd's full cycle: the previous synthesis is a Structure that must be Unstructured (shattered by the new contradiction) and Restructured (synthesized with new material). This means recursive rounds often need **new research and fresh agents** — not just rehashing the same material at a higher altitude.

**New research in recursion is often essential.** Each synthesis opens a new conceptual space that the original research didn't cover. In the 7-cycle agent identity dialectic, successive rounds pulled in Gödel's incompleteness theorem, Coasean transaction cost theory, jurisprudential concepts, witness obligation patterns, and N-of-M quorum systems — none of which were in the original research. The synthesis *created the space* for this new material to enter, which is exactly Boyd's prediction: the destructive step liberates parts that can now connect with material from outside the original domains.

When to research in recursion:
- The new contradiction involves concepts, mechanisms, or domains that weren't in the original research
- The Boydian decomposition (Phase 4.5) reveals that adjacent-domain material would enable cross-domain connections
- An agent or the user identifies a specific factual or theoretical gap

When research is unnecessary:
- The recursive contradiction is a tension *within* the existing synthesis that can be argued from material already in play
- The round is primarily about clarifying or sequencing, not reconceptualizing

**Fresh agents are usually better than resumed sessions for recursion.** The recursive round is a *new* dialectic — the contradiction has shifted, the conceptual space has evolved. Agents carrying forward their full conviction from the previous round may be trapped in their original framing. Fresh agents given the accumulated context (prior essays, structural analysis, sublation, validation critiques) plus the new contradiction can engage the evolved question without legacy commitment to positions that have already been sublated. This also brings fresh perspectives — different reasoning paths, different analogies, different ways of committing to the new positions.

**Practical guidance:**
- **Re-read the relevant phase before executing it in Round 2+.** By Round 2-3, your context window is large and the skill's instructions have drifted far above. Rather than re-reading the entire skill (which wastes context), each phase is wrapped in XML tags (`<phase1>`, `<phase2>`, `<phase3>`, `<phase4>`, `<phase5>`, `<phase6>`, `<phase7>`) for easy extraction. Before each round:
  1. Grep the overall structure: `grep -n "^<phase\|^</phase" references/phases.md` to see the tag map
  2. Before executing any phase, re-read that phase's tagged section: e.g., `sed -n '/<phase4>/,/<\/phase4>/p' references/phases.md`
  3. At minimum re-read the Core Concepts (in SKILL.md), `<phase2>`, `<phase4>`, `<phase5>`, and `<phase6>` each round — these contain the instructions that drift hardest (anti-hedging, self-sublation, abduction test, auditor prompt, refinement process)
  
  Context drift is the most common failure mode in later rounds — the orchestrator starts cutting corners on exactly the steps that matter most.
- **Pass all prior context** (both essays, structural analysis, sublation, validation critiques) to new agents as background
- **Include targeted research directives** if the new contradiction opens new domains — 2-3 specific searches per agent, just as in Round 1
- **Use 1000-1500 word essays** — the conceptual space is richer, agents can be tighter
- **Validation can be abbreviated** — a quick check that both agents feel elevated, or skip if time-constrained
- Recursive rounds are faster than Round 1 even with research (~2-3 min vs ~20 min) because agents have dense context and need only targeted searches, not broad domain surveys

### When to Stop

The system gets richer not by converging on a final answer but by accumulating resolved contradictions that form increasingly nuanced understanding. Stop when:
- The queued contradictions are becoming less productive (diminishing returns)
- The latest synthesis surfaces a contradiction that requires fundamentally different expertise or information than you have access to
- The user has what they need

**But err on the side of one more round.** The marginal insight is often the most powerful — it's the insight that couldn't have been reached without the preceding rounds building up to it.

When stopping, present the user with the **final state of the dialectic queue** — which contradictions were explored, which remain open, and which were deferred. This is a map of the intellectual territory: the resolved contradictions form the new understanding, and the open contradictions are starting points for future sessions.

See **Worked Examples → Example 3** for a 7-cycle dialectic showing how each round pulls in cross-domain material — Boyd's prediction in action.
</phase7>

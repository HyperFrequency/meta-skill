# InfraNodus tools — when and how to use them

Steps 1–3 of the Workflow (in SKILL.md) are mandatory tool calls when InfraNodus is available. This file provides full guidance on what each tool does, how to use it, and what to look for in the output. Read this before executing the workflow steps.

> Note: the skill runs against the LOCAL InfraNodus engine (`http://infranodus-mcp:9005/sse`) — no calls to infranodus.com, no per-request fees. AI-dependent tools degrade gracefully because the OSS engine is older than the SaaS.

## `generate_topical_clusters` — map the rhetorical terrain (Workflow Step 1)

**When to use:** At the start of any analysis of a substantial argument, article, speech, or debate thread. Before identifying moves, run the text through topical cluster analysis to see which concepts are dominant, which are peripheral, and how they group.

**What it adds:** The workflow's move-mapping is linear and sequential. Topical clustering reveals the structural weight distribution across the whole argument: which ideas are central (high connectivity), which are isolated, and which are being connected in ways not visible in linear reading. A dominant cluster that appears early and then disappears is a different rhetorical choice than one that recurs throughout.

**Key diagnostic:** Run the text → identify the 3–5 main clusters → check whether the stated topic actually corresponds to the structurally dominant cluster. When they diverge — when the argument claims to be about X but the network shows it's structurally organized around Y — that divergence reveals the hidden operative premise.

## `generate_content_gaps` — identify the inferential gaps structurally (Workflow Step 2)

**When to use:** After topical clustering, when looking for the hidden assumptions and missing inferential steps the skill targets in Step 6.

**What it adds:** Content gaps in the network sense are concepts that would connect existing clusters but are absent. In rhetorical terms, these map directly onto the "missing inferential step" — the premise that connects stated claim to conclusion but isn't present. The gap analysis makes this structural rather than intuitive: instead of guessing what's missing, you see which conceptual bridge the argument requires but doesn't build.

**Key diagnostic:** The gaps identified are candidates for the co-authorship mechanism. A gap the audience is likely to fill with their own prior is a designed participation space. A gap the audience is unlikely to fill independently is either a flaw or a concealment. The distinction determines the correct analytical response.

## `optimize_text_structure` — diagnose bias and coherence (Workflow Step 3)

**When to use:** When analyzing an argument suspected of being tribally organized rather than principally structured, or assessing whether it's over-concentrated (biased) or too dispersed to make a coherent point.

**What it adds:** The bias/coherence analysis maps directly onto the skill's distinction between arguing from principles and arguing from conclusions. A highly biased text — network dominated by a single cluster — structurally confirms the tribal signaling failure mode: the argument keeps returning to its home base rather than building outward.

**Key modes:** Use `responseType: "question"` to generate the questions the argument's own structure implies it should be answering but isn't — these are the missing inferential steps as explicit demands. Use `responseType: "transcend"` when the argument appears to operate within a framework that forecloses certain conclusions.

## `generate_research_questions` — surface hidden premises as questions (supplements Workflow Step 6)

**When to use:** After gap analysis, when making hidden assumptions explicit in a form deployable in the debate itself.

**What it adds:** Research questions generated from gap analysis are structurally derived rather than intuited — they emerge from what the network shows is missing. This makes them harder to dismiss as the analyst's imposition and easier to present as demands following from the argument's own logic.

**Practical deployment:** Use the generated questions directly as the consistency challenge: "your argument requires an answer to X — what is it?" If the opponent hasn't provided one, the question exposes the gap. If their answer contradicts their position elsewhere, the consistency challenge follows.

## `develop_latent_topics` — find the underdeveloped operative premises (supplements Workflow Step 6)

**When to use:** When an argument has concepts that appear briefly but carry significant structural weight — ideas connecting multiple clusters without being elaborated. These are often where the actual operative premises live.

**What it adds:** Latent topic analysis identifies nodes with high betweenness centrality (connecting many other concepts) but low local density (not themselves elaborated). In rhetorical terms, these are load-bearing premises the arguer hasn't noticed they're relying on — the mechanism behind the hidden prior problem.

**Key mode:** Use `requestMode: "transcend"` to see how latent concepts connect the argument to broader discourse frameworks the arguer may be importing unconsciously. This surfaces the trained-milieu priors the skill warns against.

## `memory_add_relations` — build a persistent graph of a debate (for extended exchanges)

**When to use:** When analyzing an extended debate across multiple exchanges, or tracking how arguments evolve across a long thread.

**What it adds:** The concession audit technique — tracking what has been conceded across a long exchange — is difficult to do reliably from memory. Saving each exchange to a named graph and building it incrementally creates a persistent structural record. The evolving graph shows which concepts gain centrality over time (terms that come to organize the debate), which drop out (abandoned positions), and where new clusters form (genuine conceptual movement versus recycling).

**Practical application:** Save opening positions, add each response as new text to the same graph. Structural changes between iterations reveal the actual movement of the argument — often different from what either participant claims happened.

## `generate_research_ideas` with `shouldTranscend: true` — offer a competing participation space (for co-authorship gaps)

**When to use:** When facing an argument organized around a co-authorship gap — a productive inferential space the audience is filling with their own premises — and direct logical refutation has been identified as the wrong tool.

**What it adds:** The skill's most advanced principle states that against co-authorship mechanisms, the correct move is to offer a competing participation space rather than fill the existing gap with your own premise. Transcendent research ideas generate conceptual bridges that go beyond the current argument's frame — potential alternative inferences the audience could make instead.

**Practical application:** Run the original argument text → generate transcendent ideas → identify which represent genuine alternative completions of the inferential gap → offer the most compelling one as a competing frame rather than a refutation. You're not correcting their reasoning — you're offering them a different inference to inhabit.

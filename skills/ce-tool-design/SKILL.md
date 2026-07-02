---
name: ce-tool-design
version: 0.1.0
description: "This skill should be used for the tool-interface layer of an agent system specifically: writing tool descriptions agents can route on, designing tool schemas and response formats, naming conventions, actionable error recovery messages, MCP server design, tool-set consolidation, and deciding when to add or remove an individual tool. Use this when the unit of work is a single tool or a set of tools. Route project-shape, pipeline architecture, and task-model-fit decisions to project-development; route deciding whether to introduce sub-agents to multi-agent-patterns. Do not use for project pipeline architecture, multi-agent design decisions, or trajectory-level token optimization."
---

# Tool Design for Agents

Design every tool as a contract between a deterministic system and a non-deterministic agent. Unlike human-facing APIs, agent-facing tools must make the contract unambiguous through the description alone: agents infer intent from descriptions and generate calls that must match expected formats. Every ambiguity becomes a potential failure mode that no amount of prompt engineering can fix.

The unit of work for this skill is a single tool or a tool catalog. Project-shape, pipeline architecture, task-model-fit, and cost-at-the-project-level decisions belong to `project-development`. Deciding whether to introduce sub-agents belongs to `multi-agent-patterns`. This skill owns the interface layer that connects deterministic code to the agent.

## When to Activate

Activate this skill when the unit of work is a tool:

- Writing a new tool description, schema, or response format.
- Debugging cases where the agent picked the wrong tool or generated malformed calls.
- Consolidating an overlapping tool catalog (the classic "we have 17 tools, the agent picks wrong half the time" case).
- Designing actionable error messages so the agent can self-correct.
- Naming tools and parameters consistently across a catalog (MCP namespacing, verb-noun naming).
- Evaluating a third-party tool against the consolidation principle before adding it.

Do not activate this skill for adjacent work owned by other skills:

- Deciding whether the project should use LLMs at all, or what the pipeline stages should be: `project-development`.
- Deciding whether to split work across sub-agents or run a single agent with more tools: `multi-agent-patterns`.
- Reducing the token weight of tool outputs at the trajectory level (observation masking, format-option choice at scale): `context-optimization`.

## Core Concepts

Design tools around the consolidation principle: if a human engineer cannot definitively say which tool should be used in a given situation, an agent cannot be expected to do better. Reduce the tool set until each tool has one unambiguous purpose, because agents select tools by comparing descriptions and any overlap introduces selection errors.

Treat every tool description as prompt engineering that shapes agent behavior. The description is not documentation for humans -- it is injected into the agent's context and directly steers reasoning. Write descriptions that answer what the tool does, when to use it, and what it returns, because these three questions are exactly what agents evaluate during tool selection.

## Detailed Topics

Full reasoning, patterns, and code for each topic live in [Detailed Topics](./references/detailed_topics.md). Read the relevant section there when you need depth; the router below is the index:

- **The Tool-Agent Interface** — tools as self-contained contracts, descriptions-as-prompt, namespacing as the catalog grows.
- **The Consolidation Principle** — single comprehensive tools over overlapping narrow ones, why it works, and when not to consolidate.
- **Architectural Reduction** — primitives over specialized tools, the file-system agent pattern, when reduction beats complexity, building for future models. Production evidence in [Architectural Reduction Case Study](./references/architectural_reduction.md).
- **Tool Description Engineering** — the four-question description structure (what / when / inputs / returns) and default-parameter selection.
- **Response Format Optimization** — offering concise vs. detailed response modes to control context usage.
- **Error Message Design** — actionable errors that tell the agent what went wrong and how to recover.
- **Tool Definition Schema** — verb-noun names, consistent parameter and return field names across the catalog.
- **Tool Collection Design** — smallest non-overlapping set, namespacing, and selection mechanisms (grouping, hints, umbrella tools).
- **MCP Tool Naming Requirements** — always use fully qualified `ServerName:tool_name` to avoid "tool not found" with multiple servers.
- **Using Agents to Optimize Tools** — the tool-testing feedback loop (`optimize_tool_description` pattern).
- **Testing Tool Design** — evaluate against unambiguity, completeness, recoverability, efficiency, consistency.
- **Worked Examples** — a well-designed `get_customer` tool vs. a poor `search(query)` anti-pattern.

## Practical Guidance

### Tool Selection Framework

When designing tool collections:
1. Identify distinct workflows agents must accomplish
2. Group related actions into comprehensive tools
3. Ensure each tool has a clear, unambiguous purpose
4. Document error cases and recovery paths
5. Test with actual agent interactions

### Tool Audit Checklist

Use this checklist for every tool before adding it to an agent:

1. **Name**: verb-noun, namespaced if the catalog has multiple domains.
2. **Description**: states what the tool does, when to use it, and what it returns.
3. **Schema**: every parameter has type, constraints, defaults, and example values.
4. **Return shape**: success and error payloads are documented and machine-readable.
5. **Recovery**: each error tells the agent what to change before retrying.
6. **Overlap**: no other tool has the same activation scenario.
7. **Consolidation decision**: adjacent narrow tools are merged unless independent calls are required.
8. **Token impact**: large responses support concise mode or file-reference mode.

## Examples

Two worked examples — a well-designed `get_customer` tool and a poor `search(query)` anti-pattern with its failure modes — are in [Detailed Topics → Worked Examples](./references/detailed_topics.md#worked-examples).

## Guidelines

1. Write descriptions that answer what, when, and what returns
2. Use consolidation to reduce ambiguity
3. Implement response format options for token efficiency
4. Design error messages for agent recovery
5. Establish and follow consistent naming conventions
6. Limit tool count and use namespacing for organization
7. Test tool designs with actual agent interactions
8. Iterate based on observed failure modes
9. Question whether each tool enables or constrains the model
10. Prefer primitive, general-purpose tools over specialized wrappers
11. Invest in documentation quality over tooling sophistication
12. Build minimal architectures that benefit from model improvements

## Gotchas

1. **Vague descriptions**: Descriptions like "Search the database for customer information" leave too many questions unanswered. State the exact database, query format, and return shape.
2. **Cryptic parameter names**: Parameters named `x`, `val`, or `param1` force agents to guess meaning. Use descriptive names that convey purpose without reading further documentation.
3. **Missing error recovery guidance**: Tools that fail with generic messages like "Error occurred" provide no recovery signal. Every error response must tell the agent what went wrong and what to try next.
4. **Inconsistent naming across tools**: Using `id` in one tool, `identifier` in another, and `customer_id` in a third creates confusion. Standardize parameter names across the entire tool collection.
5. **MCP namespace collisions**: When multiple MCP tool providers register tools with similar names (e.g., two servers both exposing `search`), agents cannot disambiguate. Always use fully qualified `ServerName:tool_name` format and audit for collisions when adding new providers.
6. **Tool description rot**: Descriptions become inaccurate as underlying APIs evolve -- parameters get added, return formats change, error codes shift. Treat descriptions as code: version them, review them during API changes, and test them against current behavior.
7. **Over-consolidation**: Making a single tool handle too many workflows produces parameter lists so large that agents struggle to select the right combination. If a tool requires more than 8-10 parameters or serves fundamentally different use cases, split it.
8. **Parameter explosion**: Too many optional parameters overwhelm agent decision-making. Each parameter the agent must evaluate adds cognitive load. Provide sensible defaults, group related options into format presets, and move rarely-used parameters into an `options` object.
9. **Missing error context**: Error messages that say only "failed" or "invalid input" without specifying which input, why it failed, or what a valid input looks like leave agents unable to self-correct. Include the invalid value, the expected format, and a concrete example in every error response.

## Integration

This skill owns the tool-interface layer. Adjacent decisions are owned elsewhere:

- `project-development`: shape of the project, choice of pipeline stages, task-model-fit, cost estimation at the project level. If the question is "what is the right pipeline architecture" rather than "what is the right tool API," route there.
- `multi-agent-patterns`: deciding whether one agent with more tools is better than two agents with smaller tool catalogs. If the question is "should this split into sub-agents," route there.
- `context-optimization`: trajectory-level token efficiency, observation masking, choosing response-format options across many tool calls. If the question is "how do we reduce token weight of accumulated tool outputs," route there.
- `context-fundamentals`: the conceptual question of how tool definitions consume the attention budget. If the question is "why does adding tools degrade routing accuracy," start there.
- `evaluation`: judging whether the tool set improved agent outcomes overall.

## References

Internal references:
- [Best Practices Reference](./references/best_practices.md) - Read when: designing a new tool from scratch or auditing an existing tool collection for quality gaps
- [Architectural Reduction Case Study](./references/architectural_reduction.md) - Read when: considering removing specialized tools in favor of primitives, or evaluating whether a complex tool architecture is justified

Related skills in this collection:
- context-fundamentals - Tool context interactions
- evaluation - Tool testing patterns

External resources:
- MCP (Model Context Protocol) documentation - Read when: implementing tools for multi-server agent environments or debugging tool routing failures
- Framework tool conventions - Read when: adopting a new agent framework and need to map tool design principles to framework-specific APIs
- API design best practices for agents - Read when: translating existing human-facing APIs into agent-facing tool interfaces
- Vercel d0 agent architecture case study - Read when: evaluating whether to consolidate tools or seeking production evidence for architectural reduction

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2026-05-15
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 2.2.0

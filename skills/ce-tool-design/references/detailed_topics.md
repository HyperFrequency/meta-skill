# Tool Design: Detailed Topics

Deep treatment of each tool-design topic. The SKILL.md router summarizes these; read the relevant section here when you need the full reasoning, patterns, and code.

## The Tool-Agent Interface

**Tools as Contracts**
Design each tool as a self-contained contract. When humans call APIs, they read docs, understand conventions, and make appropriate requests. Agents must infer the entire contract from a single description block. Make the contract unambiguous by including format examples, expected patterns, and explicit constraints. Omit nothing that a caller needs to know, because agents cannot ask clarifying questions before making a call.

**Tool Description as Prompt**
Write tool descriptions knowing they load directly into agent context and collectively steer behavior. A vague description like "Search the database" with cryptic parameter names forces the agent to guess -- and guessing produces incorrect calls. Instead, include usage context, parameter format examples, and sensible defaults. Every word in the description either helps or hurts tool selection accuracy.

**Namespacing and Organization**
Namespace tools under common prefixes as the collection grows, because agents benefit from hierarchical grouping. When an agent needs database operations, it routes to the `db_*` namespace; when it needs web interactions, it routes to `web_*`. Without namespacing, agents must evaluate every tool in a flat list, which degrades selection accuracy as the count grows.

## The Consolidation Principle

**Single Comprehensive Tools**
Build single comprehensive tools instead of multiple narrow tools that overlap. Rather than implementing `list_users`, `list_events`, and `create_event` separately, implement `schedule_event` that finds availability and schedules in one call. The comprehensive tool handles the full workflow internally, removing the agent's burden of chaining calls in the correct order.

**Why Consolidation Works**
Apply consolidation because agents have limited context and attention. Each tool in the collection competes for attention during tool selection, each description consumes context budget tokens, and overlapping functionality creates ambiguity. Consolidation eliminates redundant descriptions, removes selection ambiguity, and shrinks the effective tool set. Vercel's d0 case study is a concrete example of reducing specialized tools into a smaller primitive tool set with better measured outcomes (claim-tool-design-vercel-d0-reduction).

**When Not to Consolidate**
Keep tools separate when they have fundamentally different behaviors, serve different contexts, or must be callable independently. Over-consolidation creates a different problem: a single tool with too many parameters and modes becomes hard for agents to parameterize correctly.

## Architectural Reduction

Push the consolidation principle to its logical extreme by removing most specialized tools in favor of primitive, general-purpose capabilities. Production evidence shows this approach can outperform sophisticated multi-tool architectures.

**The File System Agent Pattern**
Provide direct file system access through a single command execution tool instead of building custom tools for data exploration, schema lookup, and query validation. The agent uses standard Unix utilities (grep, cat, find, ls) to explore and operate on the system. This works because file systems are a proven abstraction that models understand deeply, standard tools have predictable behavior, agents can chain primitives flexibly rather than being constrained to predefined workflows, and good documentation in files replaces summarization tools.

**When Reduction Outperforms Complexity**
Choose reduction when the data layer is well-documented and consistently structured, the model has sufficient reasoning capability, specialized tools were constraining rather than enabling the model, or more time is spent maintaining scaffolding than improving outcomes. Avoid reduction when underlying data is messy or poorly documented, the domain requires specialized knowledge the model lacks, safety constraints must limit agent actions, or operations genuinely benefit from structured workflows.

**Build for Future Models**
Design minimal architectures that benefit from model improvements rather than sophisticated architectures that lock in current limitations. Ask whether each tool enables new capabilities or constrains reasoning the model could handle on its own -- tools built as "guardrails" often become liabilities as models improve.

See [Architectural Reduction Case Study](./architectural_reduction.md) for production evidence.

## Tool Description Engineering

**Description Structure**
Structure every tool description to answer four questions:

1. What does the tool do? State exactly what the tool accomplishes -- avoid vague language like "helps with" or "can be used for."
2. When should it be used? Specify direct triggers ("User asks about pricing") and indirect signals ("Need current market rates").
3. What inputs does it accept? Describe each parameter with types, constraints, defaults, and format examples.
4. What does it return? Document the output format, structure, successful response examples, and error conditions.

**Default Parameter Selection**
Set defaults to reflect common use cases. Defaults reduce agent burden by eliminating unnecessary parameter specification and prevent errors from omitted parameters. Choose defaults that produce useful results without requiring the agent to understand every option.

## Response Format Optimization

Offer response format options (concise vs. detailed) because tool response size significantly impacts context usage. Concise format returns essential fields only, suitable for confirmations. Detailed format returns complete objects, suitable when full context drives decisions. Document when to use each format in the tool description so agents learn to select appropriately.

## Error Message Design

Design error messages for two audiences: developers debugging issues and agents recovering from failures. For agents, every error message must be actionable -- it must state what went wrong and how to correct it. Include retry guidance for retryable errors, corrected format examples for input errors, and specific missing fields for incomplete requests. An error that says only "failed" provides zero recovery signal.

## Tool Definition Schema

Establish a consistent schema across all tools. Use verb-noun pattern for tool names (`get_customer`, `create_order`), consistent parameter names across tools (always `customer_id`, never sometimes `id` and sometimes `identifier`), and consistent return field names. Consistency reduces the cognitive load on agents and improves cross-tool generalization.

## Tool Collection Design

Limit tool collections to the smallest set with non-overlapping purposes, because description overlap causes model confusion and more tools do not always lead to better outcomes. When more tools are genuinely needed, use namespacing to create logical groupings. Implement selection mechanisms: tool grouping by domain, example-based selection hints, and umbrella tools that route to specialized sub-tools.

## MCP Tool Naming Requirements

Always use fully qualified tool names with MCP (Model Context Protocol) to avoid "tool not found" errors.

Format: `ServerName:tool_name`

```python
# Correct: Fully qualified names
"Use the BigQuery:bigquery_schema tool to retrieve table schemas."
"Use the GitHub:create_issue tool to create issues."

# Incorrect: Unqualified names
"Use the bigquery_schema tool..."  # May fail with multiple servers
```

Without the server prefix, agents may fail to locate tools when multiple MCP servers are available. Establish naming conventions that include server context in all tool references.

## Using Agents to Optimize Tools

Feed observed tool failures back to an agent to diagnose issues and improve descriptions. Treat reported efficiency gains as workload-specific until reproduced on the target tool catalog.

**The Tool-Testing Agent Pattern**:

```python
def optimize_tool_description(tool_spec, failure_examples):
    """
    Use an agent to analyze tool failures and improve descriptions.

    Process:
    1. Agent attempts to use tool across diverse tasks
    2. Collect failure modes and friction points
    3. Agent analyzes failures and proposes improvements
    4. Test improved descriptions against same tasks
    """
    prompt = f"""
    Analyze this tool specification and the observed failures.

    Tool: {tool_spec}

    Failures observed:
    {failure_examples}

    Identify:
    1. Why agents are failing with this tool
    2. What information is missing from the description
    3. What ambiguities cause incorrect usage

    Propose an improved tool description that addresses these issues.
    """

    return get_agent_response(prompt)
```

This creates a feedback loop: agents using tools generate failure data, which agents then use to improve tool descriptions, which reduces future failures.

## Testing Tool Design

Evaluate tool designs against five criteria: unambiguity, completeness, recoverability, efficiency, and consistency. Test by presenting representative agent requests and evaluating the resulting tool calls against expected behavior.

## Worked Examples

**Example 1: Well-Designed Tool**
```python
def get_customer(customer_id: str, format: str = "concise"):
    """
    Retrieve customer information by ID.

    Use when:
    - User asks about specific customer details
    - Need customer context for decision-making
    - Verifying customer identity

    Args:
        customer_id: Format "CUST-######" (e.g., "CUST-000001")
        format: "concise" for key fields, "detailed" for complete record

    Returns:
        Customer object with requested fields

    Errors:
        NOT_FOUND: Customer ID not found
        INVALID_FORMAT: ID must match CUST-###### pattern
    """
```

**Example 2: Poor Tool Design**

This example demonstrates several tool design anti-patterns:

```python
def search(query):
    """Search the database."""
    pass
```

**Problems with this design:**

1. **Vague name**: "search" is ambiguous - search what, for what purpose?
2. **Missing parameters**: What database? What format should query take?
3. **No return description**: What does this function return? A list? A string? Error handling?
4. **No usage context**: When should an agent use this versus other tools?
5. **No error handling**: What happens if the database is unavailable?

**Failure modes:**
- Agents may call this tool when they should use a more specific tool
- Agents cannot determine correct query format
- Agents cannot interpret results
- Agents cannot recover from failures

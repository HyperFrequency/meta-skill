# Compression Gotchas

Failure modes to guard against. Read this before shipping a compression pipeline.

1. **Never compress tool definitions or schemas**: Compressing function call schemas, API specs, or tool definitions destroys agent functionality entirely. The agent cannot invoke tools whose parameter names or types have been summarized away. Treat tool definitions as immutable anchors that bypass compression.

2. **Compressed summaries hallucinate facts**: When an LLM summarizes conversation history, it may introduce plausible-sounding details that never appeared in the original. Always validate compressed output against source material before discarding originals — especially for file paths, error codes, and numeric values that the summarizer may "round" or fabricate.

3. **Compression breaks artifact references**: File paths, commit SHAs, variable names, and code snippets get paraphrased or dropped during compression. A summary saying "updated the config file" when the agent needs `config/redis.ts` causes re-exploration. Preserve identifiers verbatim in dedicated sections rather than embedding them in prose.

4. **Early turns contain irreplaceable constraints**: The first few turns of a session often contain task setup, user constraints, and architectural decisions that cannot be re-derived. Protect early turns from compression or extract their constraints into a persistent preamble that survives all compression cycles.

5. **Aggressive ratios compound across cycles**: A 95% compression ratio seems safe once, but applying it repeatedly compounds losses. After three cycles at 95%, only 0.0125% of original tokens remain. Calibrate ratios assuming multiple compression cycles, not a single pass.

6. **Code and prose need different compression**: Prose compresses well because natural language is redundant. Code does not — removing a single token from a function signature or import path can make it useless. Apply domain-specific compression strategies: summarize prose sections aggressively while preserving code blocks and structured data verbatim.

7. **Probe-based evaluation gives false confidence**: Probes can pass despite critical information being lost, because the probes test only what they ask about. A probe set that checks file names but not function signatures will miss signature loss. Design probes to cover all six evaluation dimensions, and rotate probe sets across evaluation runs to avoid blind spots.

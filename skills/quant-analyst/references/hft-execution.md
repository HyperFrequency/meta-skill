# HFT, Microstructure & Execution

Coverage checklists for the latency-sensitive end of the stack. Microstructure
research has dedicated siblings (`microstructure-analysis`, `microstructure-analyst`,
`microstructure-feature-engineering`).

## High-frequency trading
- Microstructure analysis
- Order book dynamics
- Latency optimization
- Co-location strategies
- Market impact models
- Execution algorithms
- Tick data analysis
- Hardware optimization

Latency caveat: do NOT promise a specific number (e.g. "< 1ms") as if achieved.
Achievable latency depends on language, venue, co-location, NIC/kernel bypass, and
the rest of the path. State measured latency from a profiler, with the conditions
it was measured under. Python-level loops will not hit microsecond budgets; the
hot path typically lives in Rust (`nautilus-trader` Rust core) or C++.

## Execution optimization
- Order routing
- Smart execution
- Impact minimization
- Timing optimization
- Venue selection
- Cost analysis
- Slippage reduction
- Fill improvement

# Market Research Runtime Verification Checklist

Use the lightest check that can prove the claim. Record commands and artifacts when the answer depends on runtime behavior.

## Always Check

- Current branch and dirty files before editing.
- Whether the target path is inside the parent repo or a nested repo/submodule.
- Whether the relevant deep-tool-wiki or KB page exists before citing it as complete.
- Whether current docs are needed for third-party API/version claims.

## Market Runtime Checks

- For vectorized research, require data path, timeframe, fees/slippage assumptions, and returns artifact.
- For Nautilus, identify backtest versus sandbox/live execution before changing code.
- For HFT backtests, require tick/order-book schema and latency model assumptions.
- For tear sheets, require raw returns, config, data path, and generated report path.

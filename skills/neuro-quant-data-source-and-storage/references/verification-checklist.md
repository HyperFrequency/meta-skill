# Data Source And Storage Verification Checklist

Use the lightest check that can prove the claim. Record commands and artifacts when the answer depends on runtime behavior.

## Always Check

- Current branch and dirty files before editing.
- Whether the target path is inside the parent repo or a nested repo/submodule.
- Whether the relevant deep-tool-wiki or KB page exists before citing it as complete.
- Whether current docs are needed for third-party API/version claims.

## Data Checks

- Preserve source-first partitioning by data source, market, exchange, symbol, and data type.
- Separate raw archives, working slices, and derived feature panels.
- Estimate size before sync or ingestion.

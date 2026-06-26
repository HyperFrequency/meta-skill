# Execution UI Ops Verification Checklist

Use the lightest check that can prove the claim. Record commands and artifacts when the answer depends on runtime behavior.

## Always Check

- Current branch and dirty files before editing.
- Whether the target path is inside the parent repo or a nested repo/submodule.
- Whether the relevant deep-tool-wiki or KB page exists before citing it as complete.
- Whether current docs are needed for third-party API/version claims.

## Execution UI Checks

- Verify service health endpoints before making UI state claims.
- Keep admin, prediction, and execution surfaces separate in handoffs.
- Do not infer live trading state from UI screenshots alone.

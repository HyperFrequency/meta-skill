# Forecasting Oracle ML Verification Checklist

Use the lightest check that can prove the claim. Record commands and artifacts when the answer depends on runtime behavior.

## Always Check

- Current branch and dirty files before editing.
- Whether the target path is inside the parent repo or a nested repo/submodule.
- Whether the relevant deep-tool-wiki or KB page exists before citing it as complete.
- Whether current docs are needed for third-party API/version claims.

## Forecasting Checks

- Require train/validation/test split definitions and leakage checks.
- Record model version, checkpoint source, seed, and feature transforms.
- Compare against a simple baseline before claiming model lift.

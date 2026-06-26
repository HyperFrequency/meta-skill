# Knowledge RAG Control Plane Verification Checklist

Use the lightest check that can prove the claim. Record commands and artifacts when the answer depends on runtime behavior.

## Always Check

- Current branch and dirty files before editing.
- Whether the target path is inside the parent repo or a nested repo/submodule.
- Whether the relevant deep-tool-wiki or KB page exists before citing it as complete.
- Whether current docs are needed for third-party API/version claims.

## RAG Control Checks

- Validate compose config before service startup.
- Confirm model manifests and secrets exist before full RAG runs.
- Keep generated docs, KB leaves, and canonical deep-tool-wiki pages distinct.

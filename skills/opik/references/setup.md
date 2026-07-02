# Setup — config decision tree, formats, deployments, interactive config

SKILL.md → "Setup" routes here. This file holds the full decision tree (which
mechanism to use, never duplicating an existing one) plus the concrete formats.

## Environment Config Decision Tree

**Before adding Opik config, inspect the project's existing config approach.** Follow this decision tree exactly:

1. **Check for existing `.env` / `.env.local` files and `dotenv` usage in code.**
   - If the project loads a `.env` file (via `python-dotenv`, `dotenv`, or framework auto-loading): **append** `OPIK_API_KEY` and `OPIK_WORKSPACE` to that same file. Do NOT create a separate config file.
   - If there is a `.env.example` or `.env.sample`: **also update it** with the new Opik vars (using placeholder values) so future developers know which vars are needed.

2. **If no `.env` file exists:**
   - Python: create or update `~/.opik.config` (INI format). This is the SDK's native config file.
   - TypeScript/JavaScript: create `.env` (or `.env.local` if the project uses Next.js or similar).

3. **Never introduce a second config mechanism.** If the project already uses `.env` for API keys, do NOT also create `~/.opik.config`. If it uses `~/.opik.config`, do NOT add Opik vars to `.env`.

4. **Never overwrite existing values.** If `OPIK_API_KEY` is already set in `.env`, leave it. Only add vars that are missing.

5. **Prefer setting `project_name` in code**, not in env files — one machine may log to many projects.

6. **If the user provides an API key and workspace in the prompt**, use those values directly. If they provide only an API key, ask for the workspace or default to `"default"` for local OSS.

## Config formats

Python `~/.opik.config` (INI) — the SDK's native config file:

```ini
[opik]
api_key=your-api-key
url_override=https://www.comet.com/opik/api
workspace=your-workspace
```

Environment variables (append to an existing `.env`):

```bash
# Opik
OPIK_API_KEY=your-api-key
OPIK_URL_OVERRIDE=https://www.comet.com/opik/api
OPIK_WORKSPACE=your-workspace
```

TypeScript uses `OPIK_WORKSPACE` as the env var and `workspaceName` in `new Opik({...})`.

## Standard deployments

- Cloud: `https://www.comet.com/opik/api` — requires `api_key` + `workspace`
- Local OSS: `http://localhost:5173/api` — usually workspace `default`
- Self-hosted: use the deployment's custom URL, following the project's existing config style

## Interactive config (optional)

```bash
opik configure
opik configure --use_local
npx opik-ts configure
npx opik-ts configure --use-local
```

Set the project name in code (preferred over machine-wide config):

```python
@opik.track(project_name="my-project")
def run():
    ...
```

```typescript
const client = new Opik({ projectName: "my-project" });
```

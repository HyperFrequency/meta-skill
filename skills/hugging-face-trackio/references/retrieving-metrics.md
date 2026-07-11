# Retrieving Metrics from Trackio (Dashboard HTTP API + MCP Server)

Trackio has **no** `trackio list`/`trackio get` query subcommands. To read logged
data programmatically you launch the dashboard and hit the HTTP JSON API it
serves, or connect an MCP client to the dashboard's MCP endpoint. Both read from
the same local SQLite store (or a Space, if that is where the dashboard is
running).

- GitHub: [gradio-app/trackio](https://github.com/gradio-app/trackio)
- Docs: [huggingface.co/docs/trackio](https://huggingface.co/docs/trackio/index)
- API + MCP: [huggingface.co/docs/trackio/api_mcp_server](https://huggingface.co/docs/trackio/api_mcp_server)

## The `trackio` CLI (what actually exists)

| Command | Purpose |
|---------|---------|
| `trackio show` | Launch the local dashboard (also serves the `/api/*` HTTP endpoints) |
| `trackio show --project <name>` | Open the dashboard on a specific project |
| `trackio show --mcp-server` | Also mount the MCP server at `/mcp/` (needs `trackio[mcp]`) |
| `trackio show --host 0.0.0.0` | Bind to all interfaces for remote access (default `127.0.0.1`) |
| `trackio show --color-palette "#FF0000,#00FF00"` | Custom plot colors |
| `trackio show --frontend ./dir` | Serve a custom static frontend that calls `/api/*` |
| `trackio sync` | Push a local project's database to a Hugging Face Space |
| `trackio config set/unset frontend <dir>` | Persist a default custom frontend |

There is no CLI flag that prints run/metric values as JSON to stdout; use the
HTTP API below for that.

## Launch the API, then query it

`trackio show` runs a Gradio app on `http://127.0.0.1:7860` by default and
exposes each read tool as a plain HTTP endpoint at `POST /api/{tool_name}`. The
body is JSON — pass arguments flat (`{"project": "..."}`), or as
`{"kwargs": {...}}` / `{"args": [...]}`. Every response is wrapped as
`{"data": ...}`.

```bash
trackio show            # leave this running (or run on a remote host / Space)
```

### Read endpoints

| Endpoint (`POST /api/…`) | Returns |
|--------------------------|---------|
| `get_all_projects` | List of project names |
| `get_runs_for_project` | List of run names for a `project` |
| `get_metrics_for_run` | Metric names recorded for a `project`/`run` |
| `get_metric_values` | Values (`step`, `timestamp`, `value`) for a `project`/`run`/`metric_name` |
| `get_project_summary` | Project metadata (run count, recent activity) |
| `get_run_summary` | Run metadata (metrics, config) |
| `get_system_metrics_for_run` | System-metric names (GPU/CPU/RAM) for a run |
| `get_system_logs` | System-metric values for a run |
| `get_logs` / `get_snapshot` | Metric logs / a single snapshot around a step or timestamp |
| `get_alerts` | Alerts for a project, optionally filtered by run/level |
| `get_settings` | Dashboard settings and asset configuration |

### curl

```bash
BASE=http://127.0.0.1:7860

# all projects
curl -s -X POST $BASE/api/get_all_projects \
  -H "Content-Type: application/json" -d '{}'

# runs in a project
curl -s -X POST $BASE/api/get_runs_for_project \
  -H "Content-Type: application/json" \
  -d '{"project": "my-project"}'

# values for one metric
curl -s -X POST $BASE/api/get_metric_values \
  -H "Content-Type: application/json" \
  -d '{"project": "my-project", "run": "run-1", "metric_name": "loss"}'
```

### Python (httpx)

```python
import httpx

base = "http://127.0.0.1:7860"

projects = httpx.post(f"{base}/api/get_all_projects").json()["data"]
runs = httpx.post(f"{base}/api/get_runs_for_project",
                  json={"project": "my-project"}).json()["data"]
values = httpx.post(f"{base}/api/get_metric_values",
                    json={"project": "my-project", "run": "run-1",
                          "metric_name": "loss"}).json()["data"]
```

Note the argument names: run identifiers use `run`, and `get_metric_values`
takes `metric_name` (not `metric`).

## MCP server mode (for LLM agents / MCP clients)

The `/api/*` endpoints above are always served by `trackio show`. To expose the
same tools over the Model Context Protocol — so Claude Code, Claude Desktop, or
another agent can "chat with" the experiment data — install the extra and enable
the MCP server:

```bash
pip install "trackio[mcp]"
trackio show --mcp-server        # or: GRADIO_MCP_SERVER=True trackio show
```

The streamable-HTTP MCP endpoint is then at `http://127.0.0.1:7860/mcp/`
(`https://<your-space>.hf.space/mcp/` when deployed to a Space). Client config:

```json
{
  "mcpServers": {
    "trackio": { "url": "http://127.0.0.1:7860/mcp/" }
  }
}
```

The read tools (`get_all_projects`, `get_runs_for_project`, `get_metric_values`,
`get_run_summary`, `get_system_metrics_for_run`, `get_system_logs`, `get_snapshot`,
`get_alerts`, `get_settings`, …) mirror the HTTP endpoints and never require a
token.

## Mutation tools (write-gated)

`delete_run`, `rename_run`, and `trigger_sync` (HTTP: `force_sync`) change state
and require a write credential:

- **Local dashboard** — pass `write_token`. It is printed to the terminal at
  `trackio show` startup and embedded as `?write_token=…` in the dashboard URL.
- **On a Space** — pass `hf_token` with write access to the Space repo instead.

```bash
curl -s -X POST http://127.0.0.1:7860/api/rename_run \
  -H "Content-Type: application/json" \
  -d '{"project": "my-project", "run": "run-1", "new_name": "baseline",
       "write_token": "<token from startup output>"}'
```

## Automation with jq

```bash
BASE=http://127.0.0.1:7860

# latest value of a metric
curl -s -X POST $BASE/api/get_metric_values \
  -H "Content-Type: application/json" \
  -d '{"project":"my-project","run":"run-1","metric_name":"loss"}' \
  | jq -r '.data[-1].value'

# export a run summary
curl -s -X POST $BASE/api/get_run_summary \
  -H "Content-Type: application/json" \
  -d '{"project":"my-project","run":"run-1"}' > run_summary.json

# runs whose name starts with "train"
curl -s -X POST $BASE/api/get_runs_for_project \
  -H "Content-Type: application/json" -d '{"project":"my-project"}' \
  | jq '.data[] | select(startswith("train"))'
```

Agent read loop: `get_all_projects` → `get_project_summary` →
`get_runs_for_project` → `get_run_summary` → `get_metric_values`.

## Boundaries

- The API reads the store the **running dashboard** points at. `trackio show`
  reads the local SQLite database; a run that lives only on a Space is not
  visible from a local dashboard — query the Space's own URL (`.hf.space/api/…`)
  or sync it down first. Project/run names are case-sensitive.
- Reading requires a running server (`trackio show`); there is no offline
  `--json` dump subcommand. In a headless job, launch with
  `--host 0.0.0.0` (and/or `share=True` via `trackio.show`) to reach it.
- `pip install "trackio[mcp]"` is only needed for the `/mcp/` endpoint; the plain
  `/api/*` HTTP endpoints work with the base `trackio` install.

## Further reading

- Trackio API + MCP-server docs: [huggingface.co/docs/trackio/api_mcp_server](https://huggingface.co/docs/trackio/api_mcp_server)
- Launching / hosting the dashboard: [huggingface.co/docs/trackio/launch](https://huggingface.co/docs/trackio/launch)

# Code Recipes

Client-side patterns for driving the API. These are ordinary HTTP/`requests` idioms and hold
regardless of exact endpoint drift — but confirm the base URL and payload fields against the
live API (see `api.md`).

## Setup

```python
import os, json, requests
from dotenv import load_dotenv

load_dotenv()
API_KEY  = os.getenv("ADAPTYV_API_KEY")
BASE_URL = os.getenv("ADAPTYV_BASE_URL")   # keep in config — the alpha endpoint moves
HEADERS  = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def check_connection() -> bool:
    r = requests.get(f"{BASE_URL}/organization/credits", headers=HEADERS)
    r.raise_for_status()
    print(f"OK — credits: {r.json().get('balance')}")
    return True
```

## FASTA helpers (validate before you spend)

```python
VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")

def validate_fasta(fasta: str):
    lines = fasta.strip().split("\n")
    if not lines or not lines[0].startswith(">"):
        return False, "FASTA must start with a '>' header"
    header = None
    for i, line in enumerate(lines, 1):
        if line.startswith(">"):
            if not line[1:].strip():
                return False, f"Line {i}: empty header"
            header = line[1:].strip()
        else:
            if header is None:
                return False, f"Line {i}: sequence before any header"
            bad = set(line.strip().upper()) - VALID_AA
            if bad:
                return False, f"Line {i}: invalid residues {bad}"
    return True, None

def sequences_to_fasta(seqs: dict[str, str]) -> str:
    out = ""
    for name, seq in seqs.items():
        clean = "".join(seq.split()).upper()
        ok, err = validate_fasta(f">{name}\n{clean}")
        if not ok:
            raise ValueError(f"Invalid sequence '{name}': {err}")
        out += f">{name}\n{clean}\n"
    return out
```

## Submit — single and batch

```python
def submit(seqs: dict[str, str], experiment_type="binding", target_id=None,
           webhook_url=None, metadata=None) -> dict:
    payload = {"sequences": sequences_to_fasta(seqs), "experiment_type": experiment_type}
    if target_id:   payload["target_id"]   = target_id
    if webhook_url: payload["webhook_url"]  = webhook_url    # prefer this over polling
    if metadata:    payload["metadata"]     = metadata
    r = requests.post(f"{BASE_URL}/experiments", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()

exp = submit(
    {"variant_1": "MKVLW...", "variant_2": "MKVLS...", "wildtype": "MKVLW..."},  # always ship a control
    experiment_type="expression",
    webhook_url="https://your-server.example/adaptyv-webhook",
    metadata={"project": "ab_opt", "round": 3, "optimization_method": "SolubleMPNN+ESM"},
)
print(exp["experiment_id"], exp["status"])
```

## Track — webhook preferred, polling as fallback

Register a `webhook_url` at submission (above) and handle `experiment.completed` server-side.
Only poll if you must; experiments run for weeks, so poll on the scale of hours, not seconds.

```python
def status(experiment_id: str) -> dict:
    r = requests.get(f"{BASE_URL}/experiments/{experiment_id}", headers=HEADERS)
    r.raise_for_status()
    return r.json()

def list_experiments(status_filter=None, limit=50):
    params = {"limit": limit}
    if status_filter:
        params["status"] = status_filter
    r = requests.get(f"{BASE_URL}/experiments", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()["experiments"]
```

## Retrieve + parse

```python
import pandas as pd

def download_results(experiment_id: str, out_dir="results") -> dict:
    r = requests.get(f"{BASE_URL}/experiments/{experiment_id}/results", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    os.makedirs(out_dir, exist_ok=True)
    with open(f"{out_dir}/{experiment_id}.json", "w") as f:
        json.dump(data, f, indent=2)
    return data

def binding_table(results: dict) -> pd.DataFrame:
    rows = [{
        "sequence_id": x["sequence_id"],
        "kd": x["measurements"]["kd"],
        "kon": x["measurements"]["kon"],
        "koff": x["measurements"]["koff"],
        "confidence": x["quality_metrics"]["confidence"],
        "r_squared": x["quality_metrics"]["r_squared"],
    } for x in results["results"]]
    return pd.DataFrame(rows).sort_values("kd")   # lower KD = stronger binder

def expression_table(results: dict) -> pd.DataFrame:
    rows = [{
        "sequence_id": x["sequence_id"],
        "yield_mg_per_l": x["measurements"]["total_yield_mg_per_l"],
        "soluble_fraction": x["measurements"]["soluble_fraction_percent"],
        "purity": x["measurements"]["purity_percent"],
    } for x in results["results"]]
    return pd.DataFrame(rows).sort_values("yield_mg_per_l", ascending=False)
```

## Retry with backoff (429 / 5xx only)

```python
import time
from requests.exceptions import HTTPError, RequestException

def request_with_retry(method, url, max_retries=3, backoff=2, **kwargs):
    for attempt in range(max_retries):
        try:
            r = requests.request(method, url, **kwargs)
            r.raise_for_status()
            return r
        except HTTPError as e:
            code = e.response.status_code
            if code == 429 or code >= 500:          # transient — honor Retry-After / back off
                wait = int(e.response.headers.get("Retry-After", backoff ** attempt))
                time.sleep(wait)
                continue
            raise                                   # 4xx client error — do not retry
        except RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff ** attempt)
    raise RequestException(f"failed after {max_retries} attempts")
```

## End-to-end shape

```python
# 1. pre-screen candidates in silico (see sequence-optimization.md), then:
exp = submit(top_candidates, experiment_type="binding",
             target_id="tgt_pdl1_human",
             webhook_url="https://your-server.example/hook",
             metadata={"project": "affinity_maturation"})
# 2. on the webhook's experiment.completed event:
results = download_results(exp["experiment_id"])
df = binding_table(results)
df.to_csv(f"{exp['experiment_id']}_binding.csv", index=False)
# 3. feed the measured KD/yield back into the next design round.
```

Do **not** busy-poll a weeks-long job in a tight loop — it burns rate limit for no benefit.
Register a webhook and react to it.

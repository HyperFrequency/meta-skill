# BRENDA Query Recipes

Parsing helpers and worked recipes built on top of the raw SOAP client described
in [soap-api.md](soap-api.md). These are self-contained patterns you implement —
no pre-built vendor module is assumed. Adapt field names to the operation you
call.

Assume the setup from the skill body: a `client`, your `email`, and the
SHA-256 `password_hash`.

```python
import os, time, hashlib, re
from zeep import Client
from zeep.helpers import serialize_object

WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
client = Client(WSDL)
email = os.environ["BRENDA_EMAIL"]
password_hash = hashlib.sha256(os.environ["BRENDA_PASSWORD"].encode()).hexdigest()

def km_query(ec, organism="", substrate=""):
    params = (email, password_hash,
              f"ecNumber*{ec}", f"organism*{organism}",
              "kmValue*", "kmValueMaximum*",
              f"substrate*{substrate}", "commentary*",
              "ligandStructureId*", "literature*")
    return [serialize_object(r) for r in client.service.getKmValue(*params)]
```

## Robust response parsing

Handle both the modern list-of-dicts and the legacy delimited string:

```python
def to_records(response):
    """Normalize a BRENDA response to list[dict]."""
    if isinstance(response, str):                      # legacy delimited form
        records = []
        for chunk in response.split("|") if "|" in response else [response]:
            row = {}
            for token in chunk.split("#"):
                if "*" in token:
                    key, _, val = token.partition("*")
                    row[key.strip()] = val.strip()
            if row:
                records.append(row)
        return records
    return [serialize_object(r) for r in response]     # modern object list
```

## Extracting numeric values and conditions

Kinetic values arrive as strings and may carry ranges or notes; `commentary`
often encodes pH and temperature.

```python
def parse_float(text):
    if not text:
        return None
    m = re.search(r"[-+]?\d*\.?\d+", text)
    return float(m.group()) if m else None

def conditions_from_commentary(commentary):
    commentary = commentary or ""
    ph   = re.search(r"pH\s*([0-9.]+)", commentary)
    temp = re.search(r"(\d+(?:\.\d+)?)\s*°?\s*C", commentary)
    return {
        "ph":   float(ph.group(1))   if ph   else None,
        "temp": float(temp.group(1)) if temp else None,
    }
```

## Recipe: compare an enzyme across organisms

```python
def compare_km_across_organisms(ec, organisms):
    summary = []
    for org in organisms:
        rows = km_query(ec, organism=org)
        time.sleep(0.5)                       # rate limit
        values = [parse_float(r.get("kmValue")) for r in rows]
        values = [v for v in values if v is not None]
        if values:
            summary.append({
                "organism": org,
                "n": len(values),
                "km_mean": sum(values) / len(values),
                "km_min": min(values),
                "km_max": max(values),
            })
    return summary
```

## Recipe: rank substrate specificity (lower Km = tighter binding)

```python
def substrate_specificity(ec):
    rows = km_query(ec)                       # all substrates, all organisms
    by_substrate = {}
    for r in rows:
        sub = r.get("substrate")
        km  = parse_float(r.get("kmValue"))
        if sub and km is not None:
            by_substrate.setdefault(sub, []).append(km)
    ranked = [
        {"substrate": s, "km_mean": sum(v) / len(v), "n": len(v)}
        for s, v in by_substrate.items()
    ]
    return sorted(ranked, key=lambda x: x["km_mean"])
```

For catalytic efficiency, pair this with a `getTurnoverNumber` query on the same
EC/substrate to compute `kcat / Km` — the correct specificity constant. Do not
approximate kcat from Km data alone.

## Recipe: hunt thermophilic / pH-stable variants

Use the dedicated condition operations rather than scraping commentary. The
call convention is identical; only the operation and its value field change
(confirm exact field order from the WSDL — see [soap-api.md](soap-api.md)).

```python
def temperature_optima(ec):
    params = (email, password_hash,
              f"ecNumber*{ec}", "organism*",
              "temperatureOptimum*", "temperatureOptimumMaximum*",
              "commentary*", "literature*")
    rows = [serialize_object(r) for r in client.service.getTemperatureOptimum(*params)]
    out = []
    for r in rows:
        t = parse_float(r.get("temperatureOptimum"))
        if t is not None:
            out.append({"organism": r.get("organism"), "temp_opt": t})
    return sorted(out, key=lambda x: x["temp_opt"], reverse=True)

# Filter to thermostable candidates:
# hot = [x for x in temperature_optima("1.1.1.1") if x["temp_opt"] >= 50]
```

Apply the same shape to `getPhOptimum` / `getPhStability` for acid- or
alkaline-stable variants.

## Recipe: assemble kinetic-model parameters

To parameterize a Michaelis-Menten term (`v = Vmax * [S] / (Km + [S])`), pull
Km and kcat for a specific enzyme/substrate/organism and read conditions from
commentary:

```python
def model_parameters(ec, substrate, organism=""):
    km_rows = km_query(ec, organism=organism, substrate=substrate)
    time.sleep(0.5)
    kcat_params = (email, password_hash,
                   f"ecNumber*{ec}", f"organism*{organism}",
                   "turnoverNumber*", "turnoverNumberMaximum*",
                   f"substrate*{substrate}", "commentary*", "literature*")
    kcat_rows = [serialize_object(r) for r in client.service.getTurnoverNumber(*kcat_params)]

    km  = next((parse_float(r.get("kmValue")) for r in km_rows if r.get("kmValue")), None)
    kcat = next((parse_float(r.get("turnoverNumber")) for r in kcat_rows if r.get("turnoverNumber")), None)
    cond = conditions_from_commentary(km_rows[0].get("commentary")) if km_rows else {}
    return {
        "ec": ec, "substrate": substrate, "organism": organism,
        "km_mM": km, "kcat_per_s": kcat,
        "kcat_over_km": (kcat / km) if (km and kcat) else None,
        **cond,
    }
```

Once you have parameters, hand off downstream flux/steady-state modeling to
`cobrapy`; BRENDA's job ends at supplying measured constants.

## Reactions, cofactors, inhibitors — use native operations

- **Reactions / stoichiometry**: `getReaction` returns the balanced equation in
  the `reaction` field (`<=>` reversible, `->` directional). Split on `<=>` /
  `->` then on `+` to list reactants and products.
- **Cofactors**: `getCofactor` (field `cofactor`). This is the curated answer —
  more reliable than inferring cofactors by matching NAD+/ATP/FAD substrings in
  reaction reactants.
- **Inhibitors / activators**: `getInhibitors` (`inhibitor`) and
  `getActivatingCompound` (`activatingCompound`). Prefer these over keyword
  matching the `commentary` of Km records against a hardcoded inhibitor list,
  which misses most entries and invents false positives.

## Pathway / retrosynthesis (out of scope, do it deliberately)

BRENDA has no pathway-planning endpoint. Chaining EC numbers into a synthesis
route means: query enzymes by product/substrate, stitch matching reactions, and
score feasibility yourself — a heuristic search, not a database lookup. Treat
any such routine as your own approximation, validate each step's reaction and
kinetics against BRENDA, and do not present the assembled route as authoritative
BRENDA data. For serious metabolic-network work, model the network in `cobrapy`
with BRENDA-sourced constants rather than ad hoc chaining.

## Exporting

For tabular export, flatten records to a list of dicts (via `to_records`) and
write with the standard library `csv` module or `pandas.DataFrame(rows)`. Keep
the raw `literature` field so results stay traceable to primary sources — feed
those references to `citation-management` to produce formatted citations.

## Troubleshooting checklist

- **No results**: EC has four levels? Organism/substrate spelled as BRENDA
  expects? Try `ecNumber*A.B.C.*` then narrow. Some enzymes simply lack a given
  measurement.
- **Auth failure**: password SHA-256 hex, not plaintext; account active with API
  access; using `BRENDA_EMAIL` (not the legacy misspelling).
- **Rate limiting / slowness**: `time.sleep(0.5)` between calls; cache; prefer
  specific queries over broad wildcards.
- **Inconsistent parsing**: use `parse_float` and `.get()` with defaults; never
  assume a field is present; convert zeep objects with `serialize_object`
  before treating them as dicts.
- **Wrong values for kcat/Ki/cofactors**: you are probably scraping `commentary`
  — switch to the dedicated operation for that datum.

---
name: brenda-database
version: 0.1.0
description: >-
  Query the BRENDA enzyme database (BRaunschweig ENzyme DAtabase) over its
  authenticated SOAP API to pull curated, literature-sourced enzyme data keyed
  by EC number: Michaelis constants (Km), turnover numbers (kcat), Ki/IC50
  inhibition constants, pH and temperature optima, cofactors, activators,
  specific activity, reaction equations, and per-organism values. Use when you
  need experimental kinetic parameters for a named enzyme or EC class, want to
  compare an enzyme across organisms, hunt thermostable or substrate-selective
  variants, or gather constants to parameterize a Michaelis-Menten or
  metabolic model. NOT for enzyme 3D structure (use `alphafold-database` /
  `esm`), small-molecule property prediction (`admet-prediction`, `datamol`),
  genome-scale flux modeling once parameters are in hand (`cobrapy`), or turning
  BRENDA's literature refs into formatted citations (`citation-management`).
  Requires a free BRENDA account.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "BRENDA data: CC BY 4.0 (free registration required); zeep SOAP client: MIT"
---

# BRENDA Database

## Overview

BRENDA is the reference collection of functional enzyme data, manually curated
from primary literature and organized by Enzyme Commission (EC) number. Each EC
entry aggregates experimentally measured values — kinetics, inhibition, optimal
conditions, cofactors, reactions — annotated by organism and literature source.

Programmatic access is a **SOAP web service**. Every call is authenticated with
your registered email plus the SHA-256 hex digest of your password, and returns
records that are either a list of field objects (modern `brenda_zeep.wsdl`) or a
`field*value#field*value` delimited string (legacy endpoint). Getting the call
convention exactly right is the main hurdle; the queries themselves are simple.

BRENDA data is licensed **CC BY 4.0** and requires a **free account** for API
access. Register at https://www.brenda-enzymes.org/ and cite BRENDA when you
publish derived results.

## When to Use This Skill

- You have an enzyme name or EC number and need measured **Km, kcat, Vmax,
  Ki, or IC50** values from the literature.
- You want **optimal pH / temperature**, cofactor requirements, activators, or
  inhibitors for an enzyme.
- You need **reaction equations and stoichiometry** for an EC number.
- You are comparing an enzyme's kinetics **across organisms**, or hunting
  thermophilic / pH-stable / high-affinity variants for engineering.
- You are assembling constants to **parameterize a kinetic or metabolic model**.

## When NOT to Use This Skill

- You need a **predicted 3D structure or fold** for an enzyme — use
  `alphafold-database` or `esm`.
- You are predicting **small-molecule properties** (solubility, toxicity,
  descriptors) for substrates/inhibitors — use `admet-prediction` or `datamol`.
- You already have kinetic parameters and want **genome-scale flux / FBA**
  modeling — use `cobrapy`.
- You want a **general federated bio-database client** (UniProt, KEGG, ChEBI,
  and BRENDA behind one Python API) — use `bioservices`, which ships a BRENDA
  module and can be simpler than raw SOAP.
- You need to turn BRENDA's returned literature references into **formatted
  citations / BibTeX** — use `citation-management`.
- The value you want is a raw **protein sequence or PDB id** — those live in
  UniProt / PDB; BRENDA only mirrors identifiers.

## Access and Authentication

Install the SOAP client:

```bash
uv pip install zeep
```

Provide credentials via environment variables (never hard-code them):

```bash
export BRENDA_EMAIL="you@example.org"
export BRENDA_PASSWORD="your_password"
```

The **one thing to get right**: hash the password with SHA-256, then pass
`email`, `passwordHash`, and each query field as a separate positional
`"field*value"` string, in the operation's documented field order. An empty
value (`"kmValue*"`) matches anything.

```python
import os, hashlib
from zeep import Client
from zeep.helpers import serialize_object

WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"

email = os.environ["BRENDA_EMAIL"]
password = hashlib.sha256(os.environ["BRENDA_PASSWORD"].encode("utf-8")).hexdigest()
client = Client(WSDL)

# getKmValue field order: ecNumber, organism, kmValue, kmValueMaximum,
# substrate, commentary, ligandStructureId, literature
params = (
    email, password,
    "ecNumber*1.1.1.1",           # alcohol dehydrogenase
    "organism*Homo sapiens",
    "kmValue*", "kmValueMaximum*",
    "substrate*ethanol",
    "commentary*", "ligandStructureId*", "literature*",
)
records = client.service.getKmValue(*params)

for rec in records:                       # each rec is a dict-like object
    r = serialize_object(rec)             # -> plain dict
    print(r["organism"], r["substrate"], r["kmValue"], r.get("commentary"))
```

Full auth details, response shapes, and the operation catalog are in
[references/soap-api.md](references/soap-api.md).

## What You Can Query

BRENDA exposes roughly one `getX` operation per data field shown on an enzyme
page. Each takes the same `email, passwordHash, <field*value>...` convention but
its **own** field set. The commonly used operations:

| You want | Operation | Key data fields |
| --- | --- | --- |
| Michaelis constant | `getKmValue` | kmValue, substrate, organism, commentary |
| Turnover number (kcat) | `getTurnoverNumber` | turnoverNumber, substrate, organism |
| Inhibition constant | `getKiValue` / `getIc50Value` | kiValue / ic50Value, inhibitor, organism |
| Reaction equation | `getReaction` | reaction, organism, commentary |
| pH optimum / range | `getPhOptimum` / `getPhRange` | phOptimum, organism |
| Temperature optimum / range | `getTemperatureOptimum` / `getTemperatureRange` | temperatureOptimum, organism |
| Cofactor | `getCofactor` | cofactor, organism |
| Activator | `getActivatingCompound` | activatingCompound, organism |
| Inhibitor | `getInhibitors` | inhibitor, organism, commentary |
| Specific activity | `getSpecificActivity` | specificActivity, organism |

> Operation names and their exact field lists occasionally change. Before
> relying on one you have not used, **enumerate the live WSDL** to confirm it
> exists and check its parameters — see
> [references/soap-api.md](references/soap-api.md) for the introspection snippet
> and the fuller catalog.

**Use native operations, not commentary scraping:** dedicated operations like
`getInhibitors`, `getCofactor`, and `getTurnoverNumber` return *curated* values.
Do not substitute keyword-scraping the free-text `commentary` field of Km
records for these — that yields noisy, incomplete results. Query the native
operation for the datum you actually want.

## Parsing Responses

- **Modern `brenda_zeep.wsdl`** returns a list of records; each record is a
  zeep object. Convert with `zeep.helpers.serialize_object(rec)` to get a plain
  `dict` keyed by field name (`organism`, `substrate`, `kmValue`, ...).
- **Legacy endpoints** return one delimited string:
  `organism*Escherichia coli#substrate*ethanol#kmValue*1.2#commentary*pH 7.4, 25C`.
  Split on `#`, then split each token on the first `*` into key/value.
- Numeric parameters arrive as **strings** and may carry ranges or notes; parse
  a leading float, and mine `commentary` for pH / temperature when needed.

Parser helpers, numeric extraction, and higher-level recipes (cross-organism
comparison, substrate-specificity ranking, thermophile hunting, kinetic-model
parameter assembly) are in [references/recipes.md](references/recipes.md).

## Rate Limits and Failure Modes

- **Throttle**: keep to ~1 request/second (burst ceiling ~5/second). Add a
  `time.sleep(0.5)` between calls and **cache** results locally.
- **Empty results** usually mean an over-specific query, a misspelled organism
  or substrate, or a wrong EC format — use `1.1.1.1` (four levels), widen with
  wildcards (`ecNumber*1.1.1.*`), then narrow.
- **Auth failures**: confirm the password is SHA-256 hex (not plaintext) and the
  account is active. A historical BRENDA quirk used the misspelled env var
  `BRENDA_EMIAL`; standardize on `BRENDA_EMAIL`.
- **Missing fields**: coverage is uneven across enzymes and organisms — never
  assume every EC number has kcat, pH, or inhibitor data. Handle absent keys
  gracefully.

See [references/recipes.md](references/recipes.md) for a troubleshooting
checklist and defensive-parsing patterns.

## References

- [references/soap-api.md](references/soap-api.md) — WSDL, authentication,
  exact call convention, live-WSDL introspection, operation catalog, EC-number
  structure, wildcards, response formats, and error handling.
- [references/recipes.md](references/recipes.md) — response parsers,
  numeric/condition extraction, and worked recipes for organism comparison,
  substrate specificity, variant hunting, and kinetic modeling, plus a
  troubleshooting checklist.

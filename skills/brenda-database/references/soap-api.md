# BRENDA SOAP API Reference

Depth reference for the `brenda-database` skill. Covers the WSDL, the exact
authenticated call convention, how to enumerate operations from the live
service, the common operation catalog, EC-number structure, wildcard rules,
response formats, and error handling.

## WSDL and transport

- **WSDL**: `https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl`
- **Protocol**: SOAP over HTTPS, consumed here with the `zeep` Python client.
- **License**: BRENDA data is CC BY 4.0; API access requires a free account
  (register at https://www.brenda-enzymes.org/).

## Authentication

Every operation's first two positional arguments are:

1. `email` — your registered BRENDA account email.
2. `passwordHash` — the **SHA-256 hex digest** of your password (not the
   plaintext).

```python
import hashlib
password_hash = hashlib.sha256("your_password".encode("utf-8")).hexdigest()
```

Historical note: some older BRENDA client code read the misspelled environment
variable `BRENDA_EMIAL`. Standardize on `BRENDA_EMAIL` and only add the
misspelled alias if you must interoperate with legacy scripts.

## Call convention

After `email` and `passwordHash`, pass **one positional string per query field**
in the operation's documented order, formatted `"fieldName*value"`. An empty
value matches anything (acts as a wildcard for that field).

```python
from zeep import Client
client = Client("https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl")

params = (email, password_hash,
          "ecNumber*1.1.1.1",
          "organism*",            # empty -> all organisms
          "kmValue*",
          "kmValueMaximum*",
          "substrate*ethanol",
          "commentary*",
          "ligandStructureId*",
          "literature*")
records = client.service.getKmValue(*params)
```

Passing the wrong number of fields, or fields out of order, is the most common
cause of empty or malformed results. When unsure, introspect the live service
(below) rather than guessing.

## Enumerate operations from the live service

Operation names and their parameter lists are authoritative in the WSDL, not in
any static list. Confirm before relying on an operation you have not used:

```python
from zeep import Client
client = Client("https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl")

# List all operations exposed by the service
for service in client.wsdl.services.values():
    for port in service.ports.values():
        for op_name in port.binding._operations:
            print(op_name)
```

You can also consult the official method list at
https://www.brenda-enzymes.org/soap.php.

## Common operation catalog

Each operation follows the same auth-then-`field*value` convention but has its
own field set. The two verified in this skill's source are `getKmValue` and
`getReaction` (exact field orders below). The rest are standard BRENDA fields;
confirm their exact parameters via WSDL introspection before first use.

| Operation | Returns | Notable value field(s) |
| --- | --- | --- |
| `getKmValue` | Michaelis constants | `kmValue` (mM) |
| `getTurnoverNumber` | kcat | `turnoverNumber` (1/s) |
| `getKcatKmValue` | catalytic efficiency | `kcatKmValue` |
| `getKiValue` | inhibition constant | `kiValue` |
| `getIc50Value` | half-max inhibitory conc. | `ic50Value` |
| `getReaction` | reaction equations | `reaction` |
| `getSubstrate` / `getNaturalSubstrate` | substrates | `substrate` |
| `getProduct` / `getNaturalProduct` | products | `product` |
| `getPhOptimum` / `getPhRange` | pH optima / ranges | `phOptimum` / `phRange` |
| `getTemperatureOptimum` / `getTemperatureRange` | temperature optima / ranges | `temperatureOptimum` |
| `getCofactor` | cofactors | `cofactor` |
| `getActivatingCompound` | activators | `activatingCompound` |
| `getInhibitors` | inhibitors | `inhibitor` |
| `getSpecificActivity` | specific activity | `specificActivity` |
| `getMetalsIons` | metal / ion requirements | `metalsIons` |
| `getMolecularWeight` | molecular weight | `molecularWeight` |
| `getPhStability` / `getTemperatureStability` | stability windows | `phStability` |
| `getOrganism` | organisms with this EC | `organism` |

There are also reverse-lookup operations (e.g. finding EC numbers from a value
or ligand); enumerate the WSDL for their exact names.

### Verified field orders

**`getKmValue`** — `ecNumber`, `organism`, `kmValue`, `kmValueMaximum`,
`substrate`, `commentary`, `ligandStructureId`, `literature`.

**`getReaction`** — `ecNumber`, `organism`, `reaction`, `commentary`,
`literature`.

Other operations substitute their primary value field (e.g. `getTurnoverNumber`
uses `turnoverNumber` / `turnoverNumberMaximum` in place of `kmValue` /
`kmValueMaximum`) but otherwise mirror this pattern. Confirm from the WSDL.

## EC number structure

EC numbers are hierarchical: `A.B.C.D`.

| Level | Meaning |
| --- | --- |
| `A` | Main class: 1 Oxidoreductases, 2 Transferases, 3 Hydrolases, 4 Lyases, 5 Isomerases, 6 Ligases, 7 Translocases |
| `B` | Subclass (bond type / group acted on) |
| `C` | Sub-subclass (acceptor / cofactor detail) |
| `D` | Serial number |

Examples: `1.1.1.1` alcohol dehydrogenase, `2.7.1.1` hexokinase, `3.2.1.23`
beta-galactosidase, `6.3.5.5` glutamine synthetase. Always supply all four
levels for exact matches; use a trailing wildcard (`1.1.1.*`) to span a
sub-subclass.

## Wildcards

- `*` alone (empty field value) matches everything for that field.
- Partial EC numbers with `*` match families: `ecNumber*1.1.1.*`.
- Organism/substrate wildcards: `organism*Bacillus*`, `substrate*glucose*`.
- Broad wildcard queries return large result sets — narrow by organism or
  substrate to stay within rate limits and keep parsing tractable.

## Response formats

**Modern (`brenda_zeep.wsdl`)** — a list of record objects. Convert each to a
plain dict:

```python
from zeep.helpers import serialize_object
rows = [serialize_object(r) for r in records]   # list[dict]
```

Keys are the field names for that operation (`organism`, `substrate`,
`kmValue`, `commentary`, `literature`, ...).

**Legacy** — a single delimited string, records joined and fields inline:

```
organism*Escherichia coli#substrate*ethanol#kmValue*1.2#kmValueMaximum*#commentary*pH 7.4, 25C#ligandStructureId*#literature*
```

Split on `#`, then split each token once on `*` into `(key, value)`. A robust
parser that handles both shapes lives in [recipes.md](recipes.md).

## Rate limits

- Sustained: ~1 request/second recommended.
- Burst ceiling: ~5 requests/second.
- Insert `time.sleep(0.5)` between calls; cache results locally to avoid
  re-querying identical parameters.

## Error handling

```python
from zeep.exceptions import Fault, TransportError

try:
    records = client.service.getKmValue(*params)
except Fault as e:          # SOAP-level error: bad auth, bad params
    ...
except TransportError as e: # HTTP/network error, service unavailable
    ...
```

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| SOAP `Fault`, auth failed | plaintext (unhashed) password, inactive account | SHA-256 the password; verify account |
| Empty list | over-specific query, misspelled name, wrong EC format | widen with wildcards; check spelling; use four EC levels |
| `Fault` on parameters | wrong field count/order | introspect WSDL, match the operation's field list |
| `TransportError` | network / service down | retry with backoff; check https://www.brenda-enzymes.org/ status |
| Inconsistent field text | free-text `commentary` variation | defensive parsing (see recipes.md) |

## Related resources

- BRENDA home: https://www.brenda-enzymes.org/
- SOAP method list: https://www.brenda-enzymes.org/soap.php
- Enzyme nomenclature (IUBMB): https://www.qmul.ac.uk/sbcs/iubmb/enzyme/
- zeep docs: https://docs.python-zeep.org/

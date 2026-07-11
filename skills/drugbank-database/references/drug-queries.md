# Drug Information Queries

Navigating the DrugBank XML, looking up drugs, extracting fields, and building
datasets. All snippets assume `ns = {"db": "http://www.drugbank.ca"}` and a
`root` from `get_drugbank_root()`.

## Database contents

Each `<drug>` entry carries 200+ fields. Categories and exact counts are
**version-dependent** — download a version and count rather than quoting fixed
figures. Drug `type` attribute is typically `small molecule` or `biotech`;
approval/experimental status lives in `<groups>`.

Field families: identifiers (DrugBank ID, CAS, UNII, PubChem CID), names
(generic/brand/synonym/IUPAC), chemical (SMILES/InChI/formula/MW), pharmacology
(indication, mechanism of action, pharmacodynamics), pharmacokinetics (ADME),
toxicity (LD50, adverse effects), clinical (dosage forms, routes, half-life),
proteins (targets/enzymes/transporters/carriers), interactions (drug-drug,
drug-food), and references.

## XML structure

```xml
<drugbank>
  <drug type="small molecule" created="..." updated="...">
    <drugbank-id primary="true">DB00001</drugbank-id>
    <name>Lepirudin</name>
    <description>...</description>
    <cas-number>...</cas-number>
    <groups><group>approved</group></groups>
    <indication>...</indication>
    <pharmacodynamics>...</pharmacodynamics>
    <mechanism-of-action>...</mechanism-of-action>
    <toxicity>...</toxicity>
    <metabolism>...</metabolism>
    <absorption>...</absorption>
    <half-life>...</half-life>
    <protein-binding>...</protein-binding>
    <calculated-properties>...</calculated-properties>
    <experimental-properties>...</experimental-properties>
    <external-identifiers>...</external-identifiers>
    <targets>...</targets>
    <enzymes>...</enzymes>
    <transporters>...</transporters>
    <carriers>...</carriers>
    <drug-interactions>...</drug-interactions>
    <pathways>...</pathways>
  </drug>
</drugbank>
```

A `get_text_safe` helper avoids `AttributeError` on missing elements:

```python
def get_text_safe(element):
    return element.text if element is not None else None
```

## Lookups

### By DrugBank ID

```python
def get_drug_by_id(root, ns, drugbank_id):
    for drug in root.findall("db:drug", ns):
        primary = drug.find('db:drugbank-id[@primary="true"]', ns)
        if primary is not None and primary.text == drugbank_id:
            return drug
    return None
```

### By name (including synonyms)

```python
def get_drug_by_name(root, ns, name):
    target = name.lower()
    for drug in root.findall("db:drug", ns):
        n = drug.find("db:name", ns)
        if n is not None and n.text and n.text.lower() == target:
            return drug
        for syn in drug.findall(".//db:synonym", ns):
            if syn.text and syn.text.lower() == target:
                return drug
    return None
```

### By CAS number

```python
def get_drug_by_cas(root, ns, cas_number):
    for drug in root.findall("db:drug", ns):
        cas = drug.find("db:cas-number", ns)
        if cas is not None and cas.text == cas_number:
            return drug
    return None
```

## Field extractors

### Basic info

```python
def extract_basic_info(drug, ns):
    return {
        "drugbank_id": drug.find('db:drugbank-id[@primary="true"]', ns).text,
        "name": get_text_safe(drug.find("db:name", ns)),
        "type": drug.get("type"),
        "cas_number": get_text_safe(drug.find("db:cas-number", ns)),
        "description": get_text_safe(drug.find("db:description", ns)),
        "indication": get_text_safe(drug.find("db:indication", ns)),
    }
```

### Pharmacology

```python
def extract_pharmacology(drug, ns):
    tags = [
        "indication", "pharmacodynamics", "mechanism-of-action", "toxicity",
        "metabolism", "absorption", "half-life", "protein-binding",
        "route-of-elimination", "volume-of-distribution", "clearance",
    ]
    return {t.replace("-", "_"): get_text_safe(drug.find(f"db:{t}", ns)) for t in tags}
```

### Chemical properties

Calculated and experimental properties are stored as `<property><kind>/<value>`
lists under `<calculated-properties>` / `<experimental-properties>`:

```python
def extract_properties(drug, ns):
    props = {}
    for block, suffix in [("calculated-properties", ""),
                          ("experimental-properties", "_experimental")]:
        parent = drug.find(f"db:{block}", ns)
        if parent is not None:
            for prop in parent.findall("db:property", ns):
                kind = get_text_safe(prop.find("db:kind", ns))
                value = get_text_safe(prop.find("db:value", ns))
                if kind:
                    props[f"{kind}{suffix}"] = value
    return props
# Common kinds: SMILES, InChI, InChIKey, Molecular Formula, Molecular Weight,
# logP, Water Solubility, Polar Surface Area (PSA), pKa, Melting Point
```

### External identifiers

```python
def extract_external_identifiers(drug, ns):
    ids = {}
    parent = drug.find("db:external-identifiers", ns)
    if parent is not None:
        for ext in parent.findall("db:external-identifier", ns):
            resource = get_text_safe(ext.find("db:resource", ns))
            identifier = get_text_safe(ext.find("db:identifier", ns))
            if resource:
                ids[resource] = identifier
    return ids
# Common resources: PubChem Compound/Substance, ChEMBL, ChEBI, UniProtKB,
# KEGG Drug, PharmGKB, RxCUI (RxNorm), ZINC
```

## Building datasets

### DataFrame of all drugs

```python
import pandas as pd

def create_drug_dataframe(root, ns):
    rows = []
    for drug in root.findall("db:drug", ns):
        rows.append({
            "drugbank_id": drug.find('db:drugbank-id[@primary="true"]', ns).text,
            "name": get_text_safe(drug.find("db:name", ns)),
            "type": drug.get("type"),
            "cas_number": get_text_safe(drug.find("db:cas-number", ns)),
            "indication": get_text_safe(drug.find("db:indication", ns)),
        })
    return pd.DataFrame(rows)

df = create_drug_dataframe(root, ns)
df.to_csv("drugbank_drugs.csv", index=False)
```

### Filter by type

```python
def filter_by_type(root, ns, drug_type="small molecule"):
    return [
        {"id": d.find('db:drugbank-id[@primary="true"]', ns).text,
         "name": get_text_safe(d.find("db:name", ns))}
        for d in root.findall("db:drug", ns) if d.get("type") == drug_type
    ]
```

### Keyword search over a field

```python
def search_drugs_by_keyword(root, ns, keyword, field="indication"):
    kw, results = keyword.lower(), []
    for drug in root.findall("db:drug", ns):
        elem = drug.find(f"db:{field}", ns)
        if elem is not None and elem.text and kw in elem.text.lower():
            results.append({
                "id": drug.find('db:drugbank-id[@primary="true"]', ns).text,
                "name": get_text_safe(drug.find("db:name", ns)),
                field: elem.text[:200],
            })
    return results
```

## Indexing (do this for repeated queries)

Every lookup above scans all drugs (O(n)). Build indexes **once** and reuse:

```python
def build_indexes(root, ns={"db": "http://www.drugbank.ca"}):
    by_id, by_name, by_cas = {}, {}, {}
    for drug in root.findall("db:drug", ns):
        db_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        by_id[db_id] = drug
        name = get_text_safe(drug.find("db:name", ns))
        if name:
            by_name[name.lower()] = drug
        cas = get_text_safe(drug.find("db:cas-number", ns))
        if cas:
            by_cas[cas] = drug
    return {"id": by_id, "name": by_name, "cas": by_cas}

idx = build_indexes(root)
aspirin = idx["name"].get("aspirin")   # O(1)
```

Cache the index to disk keyed by version (see `references/data-access.md`).

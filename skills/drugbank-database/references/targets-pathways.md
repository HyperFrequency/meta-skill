# Targets, Enzymes, Transporters, and Pathways

Extracting drug-protein relationships and SMPDB pathways for mechanism-of-action
studies, repurposing, and ADME reasoning. Assumes `ns = {"db":
"http://www.drugbank.ca"}`, a `root`, and `get_text_safe` from `drug-queries.md`.

## Protein categories

DrugBank splits drug-protein relationships into four sibling blocks that share
an identical element schema:

- **`<targets>`** — proteins the drug acts on therapeutically (receptors,
  enzymes, ion channels, nucleic acids). Each has `<actions>` (inhibitor,
  agonist, antagonist, ...) and `known-action` (yes/no/unknown).
- **`<enzymes>`** — metabolizing enzymes: CYP450 (CYP3A4, CYP2D6, CYP2C9, ...)
  and Phase II (UGTs, SULTs, GSTs).
- **`<transporters>`** — membrane transport: efflux (P-gp/ABCB1, BCRP, MRPs),
  uptake (OATPs, OCTs), and other SLC/ABC families.
- **`<carriers>`** — plasma carriers (albumin, alpha-1-acid glycoprotein, ...).

## XML structure

```xml
<targets>
  <target>
    <id>BE0000048</id>
    <name>Prothrombin</name>
    <organism>Humans</organism>
    <actions><action>inhibitor</action></actions>
    <known-action>yes</known-action>
    <polypeptide id="P00734" source="Swiss-Prot">
      <gene-name>F2</gene-name>
      <general-function>Serine-type endopeptidase activity</general-function>
      <specific-function>...</specific-function>
      <organism>Homo sapiens</organism>
      <go-classifiers>...</go-classifiers>
    </polypeptide>
  </target>
</targets>
```

## Extraction

### One protein element

```python
def extract_protein(elem, ns):
    data = {
        "id": get_text_safe(elem.find("db:id", ns)),
        "name": get_text_safe(elem.find("db:name", ns)),
        "organism": get_text_safe(elem.find("db:organism", ns)),
        "known_action": get_text_safe(elem.find("db:known-action", ns)),
    }
    actions = elem.find("db:actions", ns)
    if actions is not None:
        data["actions"] = [a.text for a in actions.findall("db:action", ns)]
    poly = elem.find("db:polypeptide", ns)
    if poly is not None:
        data["uniprot_id"] = poly.get("id")   # UniProt accession
        data["gene_name"] = get_text_safe(poly.find("db:gene-name", ns))
        data["general_function"] = get_text_safe(poly.find("db:general-function", ns))
    return data
```

### All four blocks for a drug

```python
def get_all_proteins(root, ns, drugbank_id):
    for drug in root.findall("db:drug", ns):
        primary = drug.find('db:drugbank-id[@primary="true"]', ns)
        if primary is not None and primary.text == drugbank_id:
            out = {}
            for block in ("targets", "enzymes", "transporters", "carriers"):
                parent = drug.find(f"db:{block}", ns)
                out[block] = ([extract_protein(c, ns) for c in list(parent)]
                              if parent is not None else [])
            return out
    return None

def get_drug_targets(root, ns, drugbank_id):
    proteins = get_all_proteins(root, ns, drugbank_id)
    return proteins["targets"] if proteins else []
```

## Drug-target networks

### Edge list

```python
import pandas as pd

def drug_target_edges(root, ns):
    rows = []
    for drug in root.findall("db:drug", ns):
        drug_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        drug_name = get_text_safe(drug.find("db:name", ns))
        block = drug.find("db:targets", ns)
        if block is None:
            continue
        for t in block.findall("db:target", ns):
            poly = t.find("db:polypeptide", ns)
            rows.append({
                "drug_id": drug_id, "drug_name": drug_name,
                "target_id": get_text_safe(t.find("db:id", ns)),
                "target_name": get_text_safe(t.find("db:name", ns)),
                "uniprot_id": poly.get("id") if poly is not None else None,
            })
    return pd.DataFrame(rows)
```

### Drugs hitting a protein

```python
def find_drugs_for_target(root, ns, target_query):
    q, hits = target_query.lower(), []
    for drug in root.findall("db:drug", ns):
        block = drug.find("db:targets", ns)
        if block is None:
            continue
        for t in block.findall("db:target", ns):
            name = get_text_safe(t.find("db:name", ns)) or ""
            if q in name.lower():
                hits.append({
                    "drug_id": drug.find('db:drugbank-id[@primary="true"]', ns).text,
                    "drug_name": get_text_safe(drug.find("db:name", ns)),
                    "target_name": name,
                })
                break
    return hits
```

## Target-based repurposing

Match on UniProt accession where present (cross-database-safe), falling back to
name. Drugs sharing targets with a reference drug are repurposing candidates.

```python
def _target_ids(targets):
    return {t.get("uniprot_id") or t["name"] for t in targets}

def find_shared_targets(root, ns, drug1_id, drug2_id):
    return list(_target_ids(get_drug_targets(root, ns, drug1_id))
                & _target_ids(get_drug_targets(root, ns, drug2_id)))

def find_similar_target_profiles(root, ns, drugbank_id, min_shared=2):
    ref = _target_ids(get_drug_targets(root, ns, drugbank_id))
    out = []
    for drug in root.findall("db:drug", ns):
        drug_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        if drug_id == drugbank_id:
            continue
        ids = _target_ids(get_drug_targets(root, ns, drug_id))
        shared = ref & ids
        if len(shared) >= min_shared:
            out.append({
                "drug_id": drug_id,
                "drug_name": get_text_safe(drug.find("db:name", ns)),
                "shared_targets": len(shared),
                "overlap_ratio": len(shared) / len(ids) if ids else 0,
                "indication": get_text_safe(drug.find("db:indication", ns)),
                "shared_target_names": list(shared),
            })
    return sorted(out, key=lambda x: x["overlap_ratio"], reverse=True)
```

Note the nested loop calls `get_drug_targets` per drug (each an O(n) scan) —
build target sets from a single pass, or index drugs first (`drug-queries.md`),
for whole-database runs.

## Enzyme and transporter profiling

CYP450 involvement drives many metabolic drug-drug interactions:

```python
def cyp450_profile(root, ns, drugbank_id):
    enzymes = get_all_proteins(root, ns, drugbank_id)["enzymes"]
    return [
        {"gene": e["gene_name"], "name": e["name"], "actions": e.get("actions", [])}
        for e in enzymes if (e.get("gene_name") or "").startswith("CYP")
    ]

def transporter_profile(root, ns, drugbank_id):
    out = {"efflux": [], "uptake": [], "other": []}
    for t in get_all_proteins(root, ns, drugbank_id)["transporters"]:
        name, gene = t["name"].lower(), (t.get("gene_name") or "").upper()
        if "p-glycoprotein" in name or gene == "ABCB1":
            out["efflux"].append(t)
        elif "oatp" in name or gene.startswith("SLCO"):
            out["uptake"].append(t)
        else:
            out["other"].append(t)
    return out
```

## Pathways (SMPDB)

```python
def get_drug_pathways(root, ns, drugbank_id):
    for drug in root.findall("db:drug", ns):
        primary = drug.find('db:drugbank-id[@primary="true"]', ns)
        if primary is not None and primary.text == drugbank_id:
            block = drug.find("db:pathways", ns)
            if block is None:
                return []
            pathways = []
            for p in block.findall("db:pathway", ns):
                entry = {
                    "smpdb_id": get_text_safe(p.find("db:smpdb-id", ns)),
                    "name": get_text_safe(p.find("db:name", ns)),
                    "category": get_text_safe(p.find("db:category", ns)),
                }
                enz = p.find("db:enzymes", ns)
                if enz is not None:
                    entry["enzymes"] = [u.text for u in enz.findall("db:uniprot-id", ns)]
                pathways.append(entry)
            return pathways
    return []
```

## GO terms

```python
def get_target_go_terms(root, ns, drugbank_id):
    terms = []
    for t in get_drug_targets(root, ns, drugbank_id):
        pass  # get_drug_targets drops go-classifiers; re-walk the element if needed
    # Walk polypeptide/go-classifiers directly:
    for drug in root.findall("db:drug", ns):
        primary = drug.find('db:drugbank-id[@primary="true"]', ns)
        if primary is None or primary.text != drugbank_id:
            continue
        for target in drug.findall("db:targets/db:target", ns):
            gc = target.find("db:polypeptide/db:go-classifiers", ns)
            if gc is None:
                continue
            for go in gc.findall("db:go-classifier", ns):
                terms.append({
                    "category": get_text_safe(go.find("db:category", ns)),
                    "description": get_text_safe(go.find("db:description", ns)),
                })
    return terms
```

## Best practices

1. Match proteins on **UniProt accession** across databases, not names.
2. Respect `<actions>` — inhibitor vs agonist vs antagonist changes the biology.
3. Separate `known-action == "yes"` targets from predicted/unknown ones.
4. Filter by organism; DrugBank includes non-human targets.
5. CYP450 and transporter profiles are the backbone of DDI prediction — pair
   with `references/interactions.md`.
6. For protein annotation beyond DrugBank, cross-reference via `bioservices` or
   `database-lookup` (UniProt) using the accession.

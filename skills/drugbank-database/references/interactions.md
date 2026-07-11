# Drug-Drug Interactions

Extracting, classifying, and analyzing DrugBank drug-drug interactions (DDIs)
for pharmacovigilance, clinical decision support, and network studies. Assumes
`ns = {"db": "http://www.drugbank.ca"}` and a `root`, plus `get_text_safe` from
`drug-queries.md`.

## Data structure

Each drug lists its partners under `<drug-interactions>`:

```xml
<drug-interactions>
  <drug-interaction>
    <drugbank-id>DB00002</drugbank-id>
    <name>Aspirin</name>
    <description>The risk or severity of bleeding can be increased ...</description>
  </drug-interaction>
</drug-interactions>
```

Only three fields per interaction: partner `drugbank-id`, partner `name`, and a
free-text `description` that encodes mechanism and severity. **Interactions are
stored directionally** — an A→B entry may not have a matching B→A entry, so
always check both directions.

## Extraction

### All interactions for a drug

```python
def get_drug_interactions(root, ns, drugbank_id):
    for drug in root.findall("db:drug", ns):
        primary = drug.find('db:drugbank-id[@primary="true"]', ns)
        if primary is not None and primary.text == drugbank_id:
            block = drug.find("db:drug-interactions", ns)
            if block is None:
                return []
            return [{
                "partner_id": get_text_safe(i.find("db:drugbank-id", ns)),
                "partner_name": get_text_safe(i.find("db:name", ns)),
                "description": get_text_safe(i.find("db:description", ns)),
            } for i in block.findall("db:drug-interaction", ns)]
    return []
```

### Whole-database adjacency

```python
def build_interaction_network(root, ns):
    network = {}
    for drug in root.findall("db:drug", ns):
        drug_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        block = drug.find("db:drug-interactions", ns)
        network[drug_id] = [
            get_text_safe(i.find("db:drugbank-id", ns))
            for i in block.findall("db:drug-interaction", ns)
        ] if block is not None else []
    return network
```

### Check a specific pair (bidirectional)

```python
def check_interaction(root, ns, drug1_id, drug2_id):
    for a, b in [(drug1_id, drug2_id), (drug2_id, drug1_id)]:
        for i in get_drug_interactions(root, ns, a):
            if i["partner_id"] == b:
                return i
    return None
```

## Classification

Severity and mechanism are not structured fields — infer them from the
description text. These keyword heuristics are a **starting point, not a
validated clinical grading**; tune them and cross-check against clinical
guidelines.

```python
def classify_severity(description):
    d = description.lower()
    if any(w in d for w in ["contraindicated", "avoid", "should not"]):
        return "major"
    if any(w in d for w in ["may increase", "can increase", "risk"]):
        return "moderate"
    if any(w in d for w in ["may decrease", "minor", "monitor"]):
        return "minor"
    return "unknown"

def classify_mechanism(description):
    d, mechs = description.lower(), []
    if "metabolism" in d or "cyp" in d:            mechs.append("metabolic")
    if "absorption" in d:                          mechs.append("absorption")
    if "excretion" in d or "renal" in d:           mechs.append("excretion")
    if "synergistic" in d or "additive" in d:      mechs.append("pharmacodynamic")
    if "protein binding" in d:                     mechs.append("protein_binding")
    return mechs or ["unspecified"]

def categorize_interactions(root, ns, drugbank_id):
    buckets = {"major": [], "moderate": [], "minor": [], "unknown": []}
    for i in get_drug_interactions(root, ns, drugbank_id):
        sev = classify_severity(i["description"])
        i["severity"], i["mechanisms"] = sev, classify_mechanism(i["description"])
        buckets[sev].append(i)
    return buckets
```

## Ranking and export

```python
def rank_by_interaction_count(root, ns):
    counts = []
    for drug in root.findall("db:drug", ns):
        block = drug.find("db:drug-interactions", ns)
        counts.append({
            "id": drug.find('db:drugbank-id[@primary="true"]', ns).text,
            "name": get_text_safe(drug.find("db:name", ns)),
            "interaction_count": len(block.findall("db:drug-interaction", ns)) if block is not None else 0,
        })
    return sorted(counts, key=lambda x: x["interaction_count"], reverse=True)
```

```python
import pandas as pd

def export_interactions_csv(root, ns, output="drugbank_interactions.csv"):
    edges = []
    for drug in root.findall("db:drug", ns):
        drug_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        drug_name = get_text_safe(drug.find("db:name", ns))
        block = drug.find("db:drug-interactions", ns)
        if block is None:
            continue
        for i in block.findall("db:drug-interaction", ns):
            edges.append({
                "drug1_id": drug_id, "drug1_name": drug_name,
                "drug2_id": get_text_safe(i.find("db:drugbank-id", ns)),
                "drug2_name": get_text_safe(i.find("db:name", ns)),
                "description": get_text_safe(i.find("db:description", ns)),
            })
    pd.DataFrame(edges).to_csv(output, index=False)
    return len(edges)
```

## Matrix over a drug set

```python
import numpy as np, pandas as pd

def interaction_matrix(root, ns, drug_ids):
    idx = {d: i for i, d in enumerate(drug_ids)}
    m = np.zeros((len(drug_ids), len(drug_ids)), dtype=int)
    for i, drug_id in enumerate(drug_ids):
        for inter in get_drug_interactions(root, ns, drug_id):
            j = idx.get(inter["partner_id"])
            if j is not None:
                m[i, j] = m[j, i] = 1   # force symmetric
    return pd.DataFrame(m, index=drug_ids, columns=drug_ids)
```

## Network analysis (networkx)

```python
import networkx as nx

def build_graph(root, ns):
    G = nx.Graph()
    for drug_id, partners in build_interaction_network(root, ns).items():
        G.add_node(drug_id)
        for p in partners:
            if p:
                G.add_edge(drug_id, p)
    return G

G = build_graph(root, ns)
print(G.number_of_nodes(), G.number_of_edges(), f"density={nx.density(G):.4f}")

# Hubs: drugs with the most interaction partners
hubs = sorted(dict(G.degree()).items(), key=lambda x: x[1], reverse=True)[:10]

# Communities (Louvain)
from networkx.algorithms import community
communities = community.louvain_communities(G)
```

Hub drugs are worth flagging in polypharmacy review — highly connected drugs
raise the chance of an interaction anywhere in a regimen. For deeper graph work
(centrality, clustering, community metrics) see the `networkx` skill.

## Polypharmacy screening

```python
def check_polypharmacy(root, ns, drug_list):
    found = []
    for i, d1 in enumerate(drug_list):
        for d2 in drug_list[i + 1:]:
            inter = check_interaction(root, ns, d1, d2)
            if inter:
                inter.update({"drug1": d1, "drug2": d2})
                found.append(inter)
    return found

def risk_score(root, ns, drug_list):
    weights = {"major": 3, "moderate": 2, "minor": 1, "unknown": 1}
    inters = check_polypharmacy(root, ns, drug_list)
    total = sum(weights[classify_severity(i["description"])] for i in inters)
    return {
        "total_interactions": len(inters),
        "risk_score": total,
        "average_severity": total / len(inters) if inters else 0,
    }
```

The risk score is a coarse relative signal for triage, not a clinical
determination — a single major contraindication can matter more than many minor
interactions.

## Best practices

1. Check both directions for every pair.
2. Treat keyword severity/mechanism as heuristic; validate against guidelines.
3. Use the latest DrugBank version for current interaction data.
4. Interpret in clinical context — dose, timing, and patient factors are not in
   the file.
5. Record the DrugBank version and your classification rules for reproducibility.

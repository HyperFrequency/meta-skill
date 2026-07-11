# Paper Workflows: Index, Claim, Curate, Cite

End-to-end sequences plus the details for the non-programmatic parts of Paper Pages (authorship, visibility) and the read-only helpers (arXiv metadata, BibTeX).

## arXiv id normalization

Accept any of these and reduce to a bare id before use:

- `2301.12345`
- `arxiv:2301.12345` / `arXiv:2301.12345`
- `https://arxiv.org/abs/2301.12345`
- `https://arxiv.org/pdf/2301.12345.pdf`

```python
import re
def clean_arxiv_id(x):
    x = x.strip()
    x = re.sub(r"^(arxiv:)", "", x, flags=re.IGNORECASE)
    x = re.sub(r"https?://arxiv\.org/(abs|pdf)/", "", x)
    return x.replace(".pdf", "")
```

## Fetch arXiv metadata

The public arXiv Atom API needs no key. Prefer a real XML parser over regex for anything beyond a quick pull.

```python
import requests, xml.etree.ElementTree as ET

def arxiv_info(arxiv_id):
    aid = clean_arxiv_id(arxiv_id)
    r = requests.get(
        f"http://export.arxiv.org/api/query?id_list={aid}", timeout=10)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = ET.fromstring(r.text).find("a:entry", ns)
    if entry is None:
        return {"error": "not found"}
    return {
        "arxiv_id": aid,
        "title": " ".join(entry.findtext("a:title", "", ns).split()),
        "authors": [a.findtext("a:name", "", ns)
                    for a in entry.findall("a:author", ns)],
        "abstract": " ".join(entry.findtext("a:summary", "", ns).split()),
        "arxiv_url": f"https://arxiv.org/abs/{aid}",
        "pdf_url": f"https://arxiv.org/pdf/{aid}.pdf",
    }
```

arXiv rate-limits aggressive polling — add a short delay between calls and retry on transient failures.

## Generate BibTeX

```python
def to_bibtex(info):
    aid = info["arxiv_id"]
    key = "arxiv" + aid.replace(".", "_")
    authors = " and ".join(info.get("authors") or ["Unknown"])
    yy = int(aid.split(".")[0][:2])          # id year prefix, e.g. 23 -> 2023
    year = f"20{yy:02d}" if yy < 50 else f"19{yy:02d}"
    return (f"@article{{{key},\n"
            f"  title   = {{{info.get('title','Untitled')}}},\n"
            f"  author  = {{{authors}}},\n"
            f"  journal = {{arXiv preprint arXiv:{aid}}},\n"
            f"  year    = {{{year}}}\n}}")
```

The year is inferred from the arXiv id prefix (`YYMM.number`); confirm it for edge cases. For richer citation styles (APA/MLA), DOIs, or a bibliography across many papers, use the `citation-management` skill instead — this helper is a convenience for the arXiv-only case.

## Indexing / submitting a paper

There is no index API. Options, in order of reliability:

1. **Check existence:** GET `https://huggingface.co/papers/<id>` → 200 means it exists.
2. **Submit:** go to `https://huggingface.co/papers/submit` (or "Submit paper" on the daily papers feed) and enter the arXiv id.
3. **Link a repo** to the id (see `linking-and-metadata.md`) — this surfaces the paper under that repo and vice-versa.

## Claim authorship (Hub UI, no API)

1. Open `https://huggingface.co/papers/<arxiv_id>`.
2. Find your name in the author list and click it.
3. Choose **Claim authorship**.
4. HF team reviews the claim. Use the email associated with the paper / your HF account to speed verification.

Failure cases: claim pending for a while is normal (manual review); a mismatch between your HF email and the paper's registered author email can block it — contact HF support with proof of authorship if needed. Another user having claimed the same author slot must be resolved by HF.

## Manage profile visibility (Hub UI, no API)

**Settings → Papers** lists your claimed papers with a *Show on profile* toggle each. Turn on the papers you want pinned to your public profile; turn off the rest. There is no `toggle-visibility` API call.

## End-to-end sequences

### A. Publish new research

```text
1. Draft the paper        (article-templates.md, or scientific-writing skill)
2. Submit to arXiv        (external) -> obtain arXiv id
3. Submit/verify HF page  hf.co/papers/submit  (or check the URL)
4. Link your repos        link_paper(...) for each model/dataset/space
5. Claim authorship       paper page -> click name -> Claim
6. Pin to profile         Settings -> Papers -> Show on profile
```

### B. Link an existing paper to your artifacts

```text
1. clean_arxiv_id(...) and confirm the page exists (200)
2. link_paper(repo, id, repo_type=...) for model, dataset, space
3. verify the arxiv:<id> tag renders on each repo
```

### C. Curate an author portfolio

```text
1. Claim each paper you authored (paper page)
2. Review Settings -> Papers
3. Toggle Show on profile per paper
```

## Search

The Hub has no stable public "search papers" API for this workflow. Search in the browser:
`https://huggingface.co/papers?q=<query>` (or `?search=<query>`). For programmatic literature discovery, use `paper-lookup` / `research-lookup`.

---
name: hugging-face-paper-publisher
version: 0.1.0
description: >-
  Index and cross-link research papers on the Hugging Face Hub. Use when you
  need to make an arXiv paper discoverable on HF Paper Pages, attach an
  `arxiv:<id>` citation tag to a model/dataset/Space by editing its card, claim
  authorship, control which papers show on your profile, pull arXiv metadata, or
  emit BibTeX — all through the `huggingface_hub` Python API plus the Hub's
  web-only workflows (authorship and visibility have no API). NOT for writing the
  paper's prose or figures (use `scientific-writing` / `scientific-figure`), for
  DOI/PubMed/Scholar citation management (use `citation-management`), for
  discovering papers to read (use `paper-lookup`), or for uploading model weights
  and dataset files (use the `huggingface_hub` upload APIs directly).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (huggingface_hub)"
---

# Hugging Face Paper Publisher

## Overview

A research paper on the Hugging Face Hub lives at `https://huggingface.co/papers/<arxiv_id>`. That **Paper Page** aggregates every model, dataset, and Space that cites the paper, plus the author list, community discussion, and a "claim authorship" control. This skill covers the four things you actually do around Paper Pages:

1. **Index** — get a page created for an arXiv paper.
2. **Link** — connect your models/datasets/Spaces to the paper so an `arxiv:<id>` tag appears (the programmatic core; `huggingface_hub` edits the repo card).
3. **Claim & curate** — verify authorship and choose which papers show on your profile (Hub UI only, no API).
4. **Cite** — fetch arXiv metadata and generate BibTeX.

The one true automation surface is **card editing** via `huggingface_hub`: the Hub scans a repo's `README.md` for arXiv links and auto-derives the `arxiv:<id>` tag. Everything else is either a URL visit or a Settings toggle. Treat authorship and visibility as manual — there is no `claim` or `toggle-visibility` API, despite what some wrappers imply.

## When to Use This Skill

- You published (or found) an arXiv paper and want a HF Paper Page for it.
- You want your model/dataset/Space to show a clickable `arxiv:<id>` tag and appear under the paper's "linked repositories".
- You are listed as an author and want to claim the paper and pin it to your profile.
- You need a BibTeX entry or clean title/author/abstract pulled straight from arXiv.
- You are assembling the metadata scaffold (model/dataset card YAML) around a paper release.

## When NOT to Use This Skill

- **Writing the paper** (Introduction, Methods, figures, LaTeX math) → use `scientific-writing` / `scientific-writer` and `scientific-figure`.
- **General citation management** (DOI→BibTeX, PubMed/Scholar/Zotero, reference lists) → use `citation-management`.
- **Finding papers to read or survey** → use `paper-lookup`, `research-lookup`, or `literature-review`.
- **Uploading model weights / dataset files / building a Space** → call `huggingface_hub` upload/`create_repo` APIs directly; this skill only touches the *card* and *paper linkage*.
- **Non-arXiv venues** (journals, conference PDFs with no arXiv id). HF Paper Pages key off arXiv ids; there is no supported path for a DOI-only paper here.

## Prerequisites

```bash
pip install "huggingface_hub>=0.26" requests   # or: uv add huggingface_hub requests
export HF_TOKEN="hf_..."                        # a WRITE-scoped token
```

A write token is required for `link` (it commits to `README.md`). Read-only actions (arXiv metadata, citation, checking a page) work without one. Get a token at `https://hf.co/settings/tokens`.

## Capabilities

### 1. Index a paper on Paper Pages

There is no "index" API call. A Paper Page appears when the paper is **submitted** through the Hub UI or when a repo links its arXiv id. To check/create:

- Visit `https://huggingface.co/papers/<arxiv_id>`. If it 404s, the paper is not yet on the Hub.
- Submit it via `https://huggingface.co/papers/submit` (or the "Submit paper" button on the daily papers feed).
- Linking any repo to the arXiv id (below) also surfaces the paper.

A quick existence check without a browser:

```python
import requests
url = f"https://huggingface.co/papers/{arxiv_id}"
exists = requests.get(url, timeout=10).status_code == 200
```

### 2. Link a paper to a model / dataset / Space  ← the automation core

Editing a repo's `README.md` to include an arXiv link makes the Hub auto-add an `arxiv:<id>` tag; the repo then shows up under the paper's linked artifacts. Do this with `huggingface_hub` (`hf_hub_download` → edit card → `upload_file`, or `metadata_update`). Full, copy-pasteable Python — including the card-editing helper, batch linking, PR-based edits (`create_pr=True`), and the model/dataset YAML that Paper Pages expect — is in **[references/linking-and-metadata.md](references/linking-and-metadata.md)**.

### 3. Claim authorship & manage profile visibility (web only)

Both are Hub-UI operations with **no API**:

- **Claim:** open `https://huggingface.co/papers/<arxiv_id>`, click your name in the author list, choose *Claim authorship*, then wait for HF team verification (use the email tied to the paper/your HF account).
- **Visibility:** *Settings → Papers* toggles *Show on profile* per claimed paper.

Exact click paths, verification tips, and failure cases are in **[references/paper-workflows.md](references/paper-workflows.md)**.

### 4. Fetch arXiv metadata & generate citations

Pull title/authors/abstract from the public arXiv API (`http://export.arxiv.org/api/query?id_list=<id>`) and format a BibTeX entry — no HF token needed. arXiv-id normalization (accepts bare ids, `arxiv:` prefixes, and `arxiv.org/abs|pdf` URLs), the metadata parse, and the BibTeX builder are in **[references/paper-workflows.md](references/paper-workflows.md)**.

### 5. Structure the paper itself (optional)

If you also need to draft the article, **[references/article-templates.md](references/article-templates.md)** gives section skeletons for four styles — `standard`, `modern` (Distill-like), `arxiv`, and `ml-report` — plus card frontmatter, LaTeX-math and table-of-contents notes, and a pointer to the community `tfrere/research-article-template` Space. For serious prose, hand off to `scientific-writing`.

## Failure Modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Paper Page 404s | Paper not submitted/indexed yet | Submit at `hf.co/papers/submit`, or link a repo to its arXiv id |
| No `arxiv:` tag after linking | README has no valid `arxiv.org/abs/<id>` link | Ensure the link is in the card body or add `arxiv:<id>` under `tags:` |
| `403` / permission denied on `link` | `HF_TOKEN` lacks write scope or repo access | Use a write token that owns/can write the repo |
| Authorship claim stuck | Awaiting HF team review / email mismatch | Wait for review; claim with the paper's registered email |
| arXiv metadata empty | Wrong id or arXiv rate-limit | Verify the id; back off and retry the arXiv API |

Deeper troubleshooting lives in the two workflow/reference files above.

## References

- **[references/linking-and-metadata.md](references/linking-and-metadata.md)** — `huggingface_hub` linking code, card-YAML edits, `arxiv:` tag mechanics, batch + PR flows, error handling.
- **[references/paper-workflows.md](references/paper-workflows.md)** — end-to-end sequences (publish new / link existing / curate portfolio), authorship & visibility click paths, arXiv metadata + BibTeX generation, arXiv-id normalization.
- **[references/article-templates.md](references/article-templates.md)** — paper section skeletons, frontmatter, math/TOC notes, and the `tfrere` template pointer.

## Related Skills

- `citation-management` — DOI/PubMed/Scholar lookups, Zotero, reference lists.
- `scientific-writing` / `scientific-writer` — draft the paper's actual prose.
- `scientific-figure` — publication figures and diagrams.
- `paper-lookup` / `research-lookup` / `literature-review` — find and survey papers.

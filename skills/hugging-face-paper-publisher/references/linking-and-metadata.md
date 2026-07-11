# Linking Papers & Repo-Card Metadata

Deep reference for the automation core: connecting a Hugging Face model/dataset/Space to an arXiv paper by editing its card so the Hub attaches an `arxiv:<id>` tag.

## How the `arxiv:` tag is created

The Hub scans each repo's `README.md`. When it finds an `https://arxiv.org/abs/<id>` link (in the card body or an equivalent reference), it **auto-derives** a repository tag `arxiv:<id>`. That tag:

- renders as a clickable pill on the repo page,
- links to `https://huggingface.co/papers/<id>`,
- makes the repo appear under that paper's "linked repositories",
- is filterable/searchable across the Hub.

You do **not** create the tag yourself — you create the link and let the Hub derive the tag. You *may* also add `arxiv:<id>` explicitly under `tags:` in the card frontmatter as a belt-and-suspenders approach.

## Minimal linking helper (`huggingface_hub`)

This mirrors the real, verified flow: download the card, splice in a Paper section (preserving existing YAML frontmatter and body), re-upload. Uses only public `huggingface_hub` APIs.

```python
import re
from huggingface_hub import HfApi, hf_hub_download

def link_paper(repo_id, arxiv_id, repo_type="model", citation=None,
               create_pr=False, token=None):
    api = HfApi(token=token)  # token also read from HF_TOKEN env by default
    readme = hf_hub_download(repo_id=repo_id, filename="README.md",
                             repo_type=repo_type, token=token)
    content = open(readme, encoding="utf-8").read()

    if arxiv_id in content:          # idempotent: already linked
        return {"status": "already_linked"}

    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
    hf_url = f"https://huggingface.co/papers/{arxiv_id}"
    block = (f"\n## Paper\n\n"
             f"Based on research in **[arXiv]({arxiv_url})** | "
             f"**[Paper Page]({hf_url})**.\n\n")
    if citation:
        block += f"### Citation\n\n```bibtex\n{citation}\n```\n\n"

    # insert after YAML frontmatter if present, else prepend
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    updated = (content[:m.end()] + block + content[m.end():]) if m \
              else "---\n---\n\n" + block + content

    api.upload_file(
        path_or_fileobj=updated.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=repo_id, repo_type=repo_type,
        commit_message=f"Add paper reference: arXiv:{arxiv_id}",
        create_pr=create_pr, token=token,
    )
    return {"status": "success", "paper_url": hf_url,
            "repo_url": f"https://huggingface.co/{repo_id}"}
```

Notes:
- `repo_type` is one of `"model"`, `"dataset"`, `"space"`.
- `create_pr=True` opens a Pull Request against the repo instead of committing to `main` — use this when you do not own the repo but can propose changes.
- `upload_file` and `hf_hub_download` are stable public functions; `create_pr` is a real `upload_file` parameter.

## Editing only the frontmatter: `metadata_update`

When you want to touch the YAML card metadata (not the body) — e.g. add tags or a `license` — use `huggingface_hub.metadata_update`, which merges keys into existing frontmatter:

```python
from huggingface_hub import metadata_update

metadata_update(
    repo_id="username/model-name",
    metadata={"tags": ["arxiv:2301.12345", "text-generation"]},
    repo_type="model",
    create_pr=False,   # or True for a PR
    token=None,        # HF_TOKEN by default
)
```

`metadata_update` merges by default (list values are unioned). It is the safe way to add `arxiv:<id>` directly to `tags:` without rewriting the whole card. For richer edits, load the card object (`ModelCard.load(...)` / `DatasetCard.load(...)`), mutate `.data`, and `.push_to_hub(...)`.

## Card frontmatter that Paper Pages expect

### Model card

```yaml
---
language:
  - en
license: apache-2.0
library_name: transformers
tags:
  - text-generation
  - transformers
  - arxiv:2301.12345   # optional explicit tag
---

# Model Name

Implements the method in **[Our Paper](https://arxiv.org/abs/2301.12345)**
(see the [Paper Page](https://huggingface.co/papers/2301.12345)).

## Citation

```bibtex
@article{doe2023paper,
  title   = {Your Paper Title},
  author  = {Doe, Jane and Smith, John},
  journal = {arXiv preprint arXiv:2301.12345},
  year    = {2023}
}
```
```

### Dataset card

```yaml
---
language:
  - en
license: cc-by-4.0
task_categories:
  - text-generation
  - question-answering
size_categories:
  - 10K<n<100K
---

# Dataset Name

Introduced in **[Our Paper](https://arxiv.org/abs/2301.12345)**.
See the [Paper Page](https://huggingface.co/papers/2301.12345).
```

The Hub extracts the arXiv id from the `arxiv.org/abs/...` link in either card and creates the `arxiv:2301.12345` tag automatically.

## Batch linking

Link several papers to one repo, or one paper to several repos:

```python
for arxiv_id in ["2301.12345", "2302.67890", "2303.11111"]:
    link_paper("username/model-name", arxiv_id, repo_type="model")

for repo, rtype in [("user/model-v1", "model"),
                    ("user/train-data", "dataset"),
                    ("user/demo", "space")]:
    link_paper(repo, "2301.12345", repo_type=rtype)
```

Each call is a separate commit. Space out large batches to avoid Hub rate limits; the helper's `if arxiv_id in content` check keeps re-runs idempotent.

## Error handling

| Error | Meaning | Action |
| --- | --- | --- |
| `RepositoryNotFoundError` | wrong `repo_id`/`repo_type`, or private repo not visible to token | verify id and token scope |
| `HfHubHTTPError` 403 | token lacks write access to the repo | use a write token that can commit to the repo |
| `EntryNotFoundError` on `README.md` | repo has no card yet | create a card first (`ModelCard`/`DatasetCard` → `push_to_hub`) before splicing |
| Tag never appears | link not recognized as arXiv | ensure a literal `arxiv.org/abs/<id>` URL exists in the body, or set `tags: [arxiv:<id>]` |
| Malformed YAML after edit | frontmatter fence broken by manual edit | prefer `metadata_update` over hand-editing the `---` block |

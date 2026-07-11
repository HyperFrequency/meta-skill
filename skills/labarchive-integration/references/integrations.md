# LabArchives Third-Party Integrations

## The common pattern

Nearly every integration follows the same shape, whether the source tool has an
official LabArchives export or not:

1. **Export** data from the source app (its API or a file export).
2. **Transform** to HTML (for inline display) or a supported file type.
3. **Create** a LabArchives entry (`entries` class, HTML content).
4. **Attach** the original file to the entry for provenance.
5. **Comment** with source version, IDs, and a timestamp for traceability.

A reusable skeleton:

```python
def push_to_labarchives(client, uid, nbid, title, html, original_file=None):
    resp = client.make_call("entries", "create_entry",
        params={"uid": uid, "nbid": nbid, "title": title, "content": html})
    entry_id = extract_entry_id(resp)          # parse from the XML/JSON response
    if original_file:
        upload_attachment(client, uid, nbid, entry_id, original_file)
    return entry_id
```

`upload_attachment` is the multipart POST from `api_reference.md`.

## Protocol management — Protocols.io

Fetch a protocol via the Protocols.io API, create an entry from its HTML, and record
the protocol ID + version as a comment so the notebook links back to the source.

```python
def import_protocol(client, uid, nbid, protocol):
    entry_id = push_to_labarchives(
        client, uid, nbid, f"Protocol: {protocol['title']}", protocol["html"])
    client.make_call("entries", "create_comment",
        params={"uid": uid, "nbid": nbid, "entry_id": entry_id,
                "comment": f"Protocols.io ID {protocol['id']} v{protocol['version']}"})
    return entry_id
```

## Data analysis — GraphPad Prism (v8+)

Prism can export directly to LabArchives from its File menu; programmatically, upload
the project or exported figures as attachments. Formats: `.pzfx` (project),
`.png`/`.jpg`/`.pdf` (graphs), `.xlsx` (tables). Archive the raw data alongside the
analysis for an auditable trail.

## Molecular biology — SnapGene & Geneious

**SnapGene** documents cloning strategies and plasmid maps. Upload the `.dna` file
plus a rendered preview (`.png`/`.pdf`) so reviewers see the map without SnapGene.
Also common: `.gb`/`.gbk` (GenBank), `.fasta`.

**Geneious** exports alignments, phylogenetic trees, assembly, and variant results.
Attach `.geneious` docs plus standard formats (`.fasta`/`.fastq`, `.bam`/`.sam`,
`.vcf`) and summarize the pipeline in the entry HTML.

## Computational notebooks — Jupyter

Convert the notebook to HTML for inline display, create the entry, and attach the
original `.ipynb` plus its environment file.

```python
import nbformat
from nbconvert import HTMLExporter

def export_jupyter(client, uid, nbid, path):
    nb = nbformat.read(path, as_version=4)
    body, _ = HTMLExporter(template_name="classic").from_notebook_node(nb)
    entry_id = push_to_labarchives(
        client, uid, nbid, f"Notebook: {path}", body, original_file=path)
    return entry_id
```

Run all cells before export so outputs are captured; attach `requirements.txt` or
`environment.yml`, and note the execution timestamp + interpreter in a comment.

## Clinical research — REDCap

Pull records via the REDCap API, format them as an HTML table, and create a dated
entry — useful for linking clinical capture to a research notebook and keeping an
audit trail (21 CFR Part 11 / HIPAA considerations apply on the REDCap side).

```python
def sync_redcap(client, uid, nbid, records):
    return push_to_labarchives(
        client, uid, nbid,
        f"REDCap export {datetime.now():%Y-%m-%d}", format_html(records))
```

## Research publishing — Qeios & SciSpace

- **Qeios** — export a formatted entry, submit to the preprint platform, and keep
  bidirectional links between notebook and publication.
- **SciSpace** — import citations and PDF annotations into notebook entries; useful
  for keeping a literature review beside experiments.

## OAuth2 for app integrations

New integrations authenticate via OAuth 2.0 (authorization-code flow). Register your
app to get a client ID + secret, then:

```python
# 1. Send the user to the authorize URL (obtains a `code` at your redirect_uri)
authorize = "https://mynotebook.labarchives.com/oauth/authorize"
params = {"client_id": cid, "redirect_uri": redirect,
          "response_type": "code", "scope": "read write"}

# 2. Exchange the code for tokens
tokens = requests.post("https://mynotebook.labarchives.com/oauth/token",
    data={"client_id": cid, "client_secret": secret, "redirect_uri": redirect,
          "grant_type": "authorization_code", "code": code}).json()
access_token, refresh_token = tokens["access_token"], tokens["refresh_token"]
```

Confirm the current OAuth endpoints with LabArchives developer support — they may
differ by region/tenant. OAuth gives finer-grained, revocable, refreshable access
than static API keys and is preferred for anything user-facing.

## Custom integration template

For tools without a native path, wrap the common pattern in one class:

```python
class LabArchivesIntegration:
    def __init__(self, client, uid):
        self.client, self.uid = client, uid

    def export(self, nbid, title, source_data):
        html = self._to_html(source_data)
        resp = self.client.make_call("entries", "create_entry",
            params={"uid": self.uid, "nbid": nbid, "title": title, "content": html})
        return extract_entry_id(resp)

    def _to_html(self, data):
        ...   # tool-specific transform
```

## Integration best practices

- Record which **software version** produced the data.
- Preserve **metadata** (timestamps, user, processing parameters) in comments.
- Prefer **open formats** (CSV/JSON/HTML) for attachments.
- **Rate-limit** bulk uploads and retry with backoff (see `api_reference.md`).
- **Validate in a test notebook** before pointing at production data.

## Integration troubleshooting

- **Integration missing in UI** — not enabled by admin, or OAuth scope/permissions
  insufficient; check software version compatibility.
- **Upload fails** — file exceeds the ~2 GB/file cap, unsupported format, or quota
  exhausted.
- **Auth errors** — expired integration token, stale API keys, or missing user
  permissions.

For platform-specific issues, check the source vendor's docs and LabArchives support
(`support@labarchives.com`, `help.labarchives.com`).

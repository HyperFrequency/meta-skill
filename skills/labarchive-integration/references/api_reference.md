# LabArchives REST API Reference

> Method names below reflect the API as commonly used; LabArchives is
> backward-compatible but some method names vary by API version. Confirm exact
> names/parameters against the official docs before scripting production workflows.

## URL structure

```
https://<base_url>/api/<api_class>/<api_method>?<auth_params>&<method_params>
```

`base_url` is the regional host (see `authentication.md`). Every call carries the
institutional `access_key_id` + `access_password`; user-scoped calls also carry a
`uid`. With the `labarchivespy` wrapper, call
`client.make_call("<api_class>", "<api_method>", params={...})`, which returns a
`requests.Response`. Responses are XML by default; pass `json=true` where supported.

## Users class

### `users/user_access_info`
Authenticate a user and retrieve their UID plus accessible notebooks.

- `login_or_email` (required) — account email or username.
- `password` (required) — the user's **external-applications** password.

Returns: `uid`, and a list of notebooks (`nbid`, name, role) with account status.

```python
resp = client.make_call("users", "user_access_info",
    params={"login_or_email": email, "password": external_pw})
uid = ET.fromstring(resp.content)[0].text
```

### `users/user_info_via_id`
Retrieve profile detail for a known UID.

- `uid` (required).

Returns: name, email, institution, role/permissions, and storage quota/usage.

## Notebooks class

### `notebooks/notebook_backup`
Download a full or metadata-only copy of a notebook.

- `uid` (required)
- `nbid` (required)
- `json` (optional, default `false`) — JSON instead of XML for metadata output.
- `no_attachments` (optional, default `false`) — exclude files.

Returns:

- `no_attachments=false` → a **7z archive**: entry HTML content, original file
  attachments, metadata XML (timestamps, authors, version history), and comment
  threads/annotations. Write the raw bytes to a `.7z` file.
- `no_attachments=true` → structured **XML/JSON** with entry content only.

```python
# full backup
resp = client.make_call("notebooks", "notebook_backup",
    params={"uid": uid, "nbid": nbid, "json": "false", "no_attachments": "false"})
open("nb.7z", "wb").write(resp.content)

# metadata-only, JSON
resp = client.make_call("notebooks", "notebook_backup",
    params={"uid": uid, "nbid": nbid, "json": "true", "no_attachments": "true"})
data = json.loads(resp.content)
```

The notebook list itself comes from the `user_access_info` response (parse each
`<notebook>` for `nbid`/`name`/`role`); a dedicated list method may also exist
depending on API version.

## Entries class

Create and populate entries. Confirm exact method names against the official docs.

### create an entry
- `uid`, `nbid` (required)
- `title` (required)
- `content` (optional) — HTML body
- `date` (optional) — defaults to today

Returns: the new `entry_id`.

### add a comment
- `uid`, `nbid`, `entry_id` (required)
- `comment` (required) — HTML supported

### add a part
Attach a component (text/table/image) to an entry.
- `uid`, `nbid`, `entry_id` (required)
- `part_type` (required) — e.g. `text`, `table`, `image`
- `content` (required) — in the appropriate format

### upload an attachment
Multipart POST — **auth params go in the form body**, not the query string.

- `uid`, `nbid`, `entry_id` (required)
- `file` (required) — multipart/form-data
- `filename` (required)

```python
requests.post(f"{api_url}/entries/upload_attachment",
    files={"file": open("/path/data.csv", "rb")},
    data={"uid": uid, "nbid": nbid, "entry_id": entry_id,
          "filename": "data.csv",
          "access_key_id": key_id, "access_password": pw})
```

Common attachment types: PDF/DOCX/TXT, PNG/JPG/TIFF, CSV/XLSX/HDF5, scientific
formats (CIF/MOL/PDB), and archives (ZIP/7Z). Typical size cap ~2 GB/file.

## Site Reports class (Enterprise)

Institution-wide analytics; requires Enterprise + admin enablement.

| Method | Key params | Returns |
| ------ | ---------- | ------- |
| `detailed_usage_report` | `start_date`, `end_date`, `format?` | login frequency, entry counts, storage use, collaboration, activity over time |
| `detailed_notebook_report` | `include_settings?`, `include_members?` | notebook inventory: names/IDs, owner, dates, member counts, size, settings |
| `pdf_offline_generation_report` | `start_date`, `end_date` | PDF-export audit log: who/what/when/IP |

Dates are `YYYY-MM-DD`.

```python
client.make_call("site_reports", "detailed_usage_report",
    params={"start_date": "2026-01-01", "end_date": "2026-06-30"})
```

## Utilities class

- `utilities/institutional_login_urls` — list institutional SSO login endpoints
  (no user params; uses access-key auth).

## Response formats

XML (default):

```xml
<response>
  <uid>12345</uid>
  <email>researcher@university.edu</email>
  <notebooks>
    <notebook><nbid>67890</nbid><name>Lab Notebook 2026</name><role>owner</role></notebook>
  </notebooks>
</response>
```

JSON (`json=true` where supported):

```json
{"uid": "12345", "email": "researcher@university.edu",
 "notebooks": [{"nbid": "67890", "name": "Lab Notebook 2026", "role": "owner"}]}
```

## Error codes

| Code | Meaning | Fix |
| ---- | ------- | --- |
| 401 | Invalid credentials | Verify keys, password type, and region (see `authentication.md`) |
| 403 | Insufficient permissions | Check role and notebook access |
| 404 | Resource not found | Verify `uid`/`nbid`/`entry_id` |
| 429 | Rate limit exceeded | Exponential backoff |
| 500 | Server error | Retry, then contact support |

## Rate limiting

- Target ≤ **60 requests/min per API key**; short bursts up to ~100 may be tolerated.
- Put **1–2 s between requests** for batch/loop operations.
- Back off exponentially on 429.

LabArchives adds new methods without breaking existing ones; monitor announcements
for new capabilities.

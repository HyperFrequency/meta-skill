# File Manager

File operations are scoped to a workspace: attach data, images, and documents to
protocols; organize them in folders. Base URL `https://www.protocols.io/api/v3`.

## Search and browse

- Search: `GET /workspaces/{id}/files/search` — params `query`, `type`
  (`file`/`folder`/`all`), `folder_id` (scope), `page_size` (default 20, max 100),
  `page_id`. Returns ID, name, size, type, timestamps, path, and download URL.
- Browse a folder: `GET /workspaces/{id}/folders/{folder_id}` — use `folder_id=root`
  for the workspace root; sort with `order_by` (`name`/`size`/`created`/`modified`)
  and `order_dir`.

## Upload

`POST /workspaces/{id}/files/upload` as `multipart/form-data`:

- `file` (required)
- `folder_id` (omit or `root` for workspace root)
- `name` (optional custom filename), `description`, `tags` (comma-separated)

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@results.xlsx" -F "folder_id=67890" \
  -F "description=Trial 3 results" -F "tags=experiment,data,2025" \
  "https://www.protocols.io/api/v3/workspaces/12345/files/upload"
```

Verify processing: `GET /workspaces/{id}/files/{file_id}/status` →
`processing` / `complete` / `failed`. Confirm `complete` before referencing the file
elsewhere.

## File operations

- Download: `GET /workspaces/{id}/files/{file_id}/download` (binary; use `-o`).
- Metadata: `GET /workspaces/{id}/files/{file_id}`.
- Update metadata: `PATCH /workspaces/{id}/files/{file_id}` — `name`, `description`,
  `tags`, or `folder_id` (move).
- Delete (soft, to trash): `DELETE /workspaces/{id}/files/{file_id}`.
- Restore: `POST /workspaces/{id}/files/{file_id}/restore`.

## Folders

- Create: `POST /workspaces/{id}/folders` — `name` (required), `parent_folder_id`,
  `description`.
- Rename/update: `PATCH /workspaces/{id}/folders/{folder_id}`.
- Delete: `DELETE /workspaces/{id}/folders/{folder_id}` — add `?recursive=true` to
  remove contents too. Recursive deletion is hard to undo; confirm first.

## File types and limits

Broadly supports spreadsheets (`.xlsx/.csv/.tsv`), stats formats (`.rds/.sav/.dta`),
text/JSON/XML, images (`.png/.jpg/.tif`; scientific `.czi/.nd2/.lsm` may need special
handling), documents (`.pdf/.docx/.pptx`), code/notebooks (`.py/.ipynb/.r/.rmd`),
media, and archives (`.zip/.tar.gz`). Size caps are workspace-dependent (often
~100 MB–1 GB); large files may need chunked upload.

## Performance and errors

- Compress large datasets; parallelize batch uploads with retry + backoff.
- Cache frequently downloaded files locally; stream large downloads.
- Codes: `400` bad params · `401` bad token · `403` permission · `404` missing ·
  `413` too large · `422` validation failed · `429` rate limited · `507` storage full.

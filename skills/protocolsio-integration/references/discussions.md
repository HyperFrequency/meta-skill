# Discussions (Comments)

Comments attach either to a whole protocol or to an individual step, and support
threaded replies. Base URL `https://www.protocols.io/api/v3`.

## Protocol-level comments

- List: `GET /protocols/{id}/comments` — paginate with `page_size` (default 10, max
  50) and `page_id` (0-indexed). Each entry carries comment ID, body, author
  (name/affiliation/avatar), created/modified timestamps, and reply/thread info.
- Create: `POST /protocols/{id}/comments` — body `body` (required, HTML or Markdown),
  optional `parent_comment_id` to make it a reply.
- Update: `PATCH /protocols/{id}/comments/{comment_id}` — body `body`. Author-only.
- Delete: `DELETE /protocols/{id}/comments/{comment_id}`. Author-only. Deleting a
  parent may affect its thread.

```bash
# top-level comment
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"body":"Achieved 85% editing efficiency with this protocol."}' \
  "https://www.protocols.io/api/v3/protocols/12345/comments"

# threaded reply
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"body":"Which cell type?","parent_comment_id":67890}' \
  "https://www.protocols.io/api/v3/protocols/12345/comments"
```

## Step-level comments

Same shape, scoped to a step:

- List: `GET /protocols/{id}/steps/{step_id}/comments`
- Create: `POST /protocols/{id}/steps/{step_id}/comments` (`body`, optional `parent_comment_id`)
- Update: `PATCH /protocols/{id}/steps/{step_id}/comments/{comment_id}`
- Delete: `DELETE /protocols/{id}/steps/{step_id}/comments/{comment_id}`

Prefer step-level comments when feedback targets a specific parameter or condition —
it keeps context tight.

## Building a thread tree

To reconstruct discussion structure: fetch all comments, then group by
`parent_comment_id` (top-level comments have none). Recurse to render nested replies.

## Formatting

Bodies accept HTML or Markdown, including links. Example Markdown body:

```json
{"body":"## Note\n\nBetter results with:\n\n- 37°C\n- 2 h incubation\n\nSee [doi:10.xxxx](https://doi.org/10.xxxx)"}
```

## Permissions and errors

- Anyone can comment on a published public protocol; private protocols require access.
- Only the author can edit/delete their own comment — expect `403` otherwise.
- Common codes: `400` bad body · `401` bad token · `403` permission · `404` missing
  protocol/step/comment · `429` rate limited.

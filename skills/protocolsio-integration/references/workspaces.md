# Workspaces

Workspaces group protocols, members, and files under shared access control. Base URL
`https://www.protocols.io/api/v3`.

## List and inspect

- `GET /workspaces` — workspaces you can access. Paginate with `page_size` (max 50)
  and `page_id`. Each carries ID, name, type (personal/group/institutional), member
  count, your access level, and creation date.
- `GET /workspaces/{id}` — full metadata, member list with roles, settings, and
  protocol counts.

```bash
curl -H "Authorization: Bearer $TOKEN" "https://www.protocols.io/api/v3/workspaces"
```

## Membership

- Members: `GET /workspaces/{id}/members` (name, role, join date, activity).
- Request access: `POST /workspaces/{id}/join-request` with optional `message`.
- Join a public workspace directly: `POST /workspaces/{id}/join` (only where the
  workspace allows open joining).

## Roles (write gating)

| Role | Can do |
| --- | --- |
| Owner | full control, manage members/permissions, delete workspace |
| Admin | manage protocols and members, configure settings; no delete |
| Member | create/edit protocols, view all, comment |
| Viewer | view + comment only; **no create/edit** |

Check the caller's role before write operations — Viewer/Member mismatches surface as
`403`.

## Workspace protocols

- List: `GET /workspaces/{id}/protocols` — params `filter` (`all`/`own`/`shared`),
  `key`, `order_field`, `order_dir`, `page_size`, `page_id`, `content_format`.
- Create: `POST /workspaces/{id}/protocols` — same body as a standard protocol create
  (see `protocols.md`); the new protocol inherits workspace permissions.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://www.protocols.io/api/v3/workspaces/12345/protocols?filter=all&order_field=modified_on&order_dir=desc"
```

## Workspace types

- **Personal** — individual default, private, can share individual protocols.
- **Group** — team collaboration, shared access, role-based.
- **Institutional** — org-wide, often branded, centrally managed.

## Organizations

Organizations sit above workspaces. Bulk export:
`GET /organizations/{org_id}/export` — see `account-and-experiments.md` for format
options (`json`/`csv`/`xml`, `include_files`, `include_comments`). Use for archival,
compliance, or migration.

## Integration tips

- Cache the workspace list; don't re-fetch it per operation.
- Check roles before writes; implement an approval path for join requests.
- Sync local copies periodically rather than on every call.

## Errors

`400` bad ID/params · `401` bad token · `403` insufficient role · `404` no
workspace/access · `429` rate limited.

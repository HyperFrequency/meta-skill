# Connection & Session Management

Everything in omero-py flows through a `BlitzGateway`. This reference covers opening,
authenticating, scoping, and closing that connection.

## Opening a connection

```python
from omero.gateway import BlitzGateway

conn = BlitzGateway(username, password, host=host, port=4064, secure=True)
if conn.connect():
    ...           # do work
    conn.close()  # free the server-side session
else:
    print("Connection failed")
```

Constructor arguments:

| Arg        | Type | Notes                                                        |
| ---------- | ---- | ------------------------------------------------------------ |
| `username` | str  | OMERO account name                                           |
| `password` | str  | account password                                             |
| `host`     | str  | server hostname or IP                                        |
| `port`     | int  | default `4064`                                               |
| `secure`   | bool | `True` encrypts *all* traffic (not just login); default `False` |

`connect()` returns a bool — always check it. `secure=True` is the right default for anything
crossing an untrusted network; without it only the credential exchange is encrypted.

## Prefer the context manager

The `with` form calls `connect()` on entry and `close()` on exit, even when an exception is
raised. Use it unless you have a specific reason not to.

```python
with BlitzGateway(username, password, host=host, port=4064, secure=True) as conn:
    for project in conn.getObjects("Project"):
        print(project.getName())
```

## Reuse an existing Ice client / session

If you already created an `omero.client` (e.g. inside an OMERO.script, or to reuse a session
id), wrap it instead of re-authenticating:

```python
import omero.clients
from omero.gateway import BlitzGateway

client = omero.client(host, port)
client.createSession(username, password)   # or joinSession(session_id)
conn = BlitzGateway(client_obj=client)
```

Inside an OMERO.script you always use `BlitzGateway(client_obj=client)` — see
`scripts.md`.

## Session / user introspection

```python
user = conn.getUser()
user.getId(); user.getName(); user.getFullName()
conn.isAdmin()          # bool
conn.isFullAdmin()      # bool
conn.getCurrentAdminPrivileges()   # list of specific privileges if not full admin

ctx = conn.getEventContext()        # userId, userName, groupId, groupName, sessionId, isAdmin
conn.isConnected()                  # True while the session is live
```

## Group context (the #1 source of "object not found")

OMERO scopes data to groups. A user belongs to several; queries only see the *current* group
unless told otherwise. The current group comes from `conn.getGroupFromContext()`.

```python
# List your groups
for g in conn.getGroupsMemberOf():
    print(g.getId(), g.getName())

# Query across ALL your accessible groups (use when an ID "isn't found")
conn.SERVICE_OPTS.setOmeroGroup('-1')
image = conn.getObject("Image", image_id)

# Then pin to the object's real group before mutating it
group_id = image.getDetails().getGroup().getId()
conn.SERVICE_OPTS.setOmeroGroup(group_id)

# Reset to your default group
conn.SERVICE_OPTS.setOmeroGroup(conn.getEventContext().groupId)
```

Rule of thumb: use `'-1'` for read/search, but switch to a concrete group id before creating
or editing objects so they land in the right place.

## Admin: act as another user

Full admins can open a sub-connection that runs as another experimenter. Objects created on
`user_conn` are owned by that user.

```python
user = admin_conn.getObject("Experimenter", user_id)
user_conn = admin_conn.suConn(user.getOmeName())
try:
    for project in user_conn.listProjects():
        print(project.getName())
finally:
    user_conn.close()
```

## Credentials and robustness

- Never hardcode passwords. Read from env vars (`OMERO_USER`, `OMERO_PASSWORD`, `OMERO_HOST`,
  `OMERO_PORT`) or a config file kept out of version control.
- Wrap connection code in `try/except/finally` (or the context manager) so `close()` always runs.
- For long-running apps, sessions can time out; be prepared to reconnect, and consider a
  connection pool for web services.

## Troubleshooting

| Symptom                                   | Likely cause / fix                                                  |
| ----------------------------------------- | ------------------------------------------------------------------- |
| `Unable to contact ORB` / connect refused | wrong host/port, firewall, server down, or no network route         |
| `connect()` returns `False`               | bad username/password, inactive account, or wrong group membership  |
| Object exists in web UI but `getObject` → `None` | wrong group context — set `setOmeroGroup('-1')` and retry     |
| Session drops mid-run                      | server session timeout — reconnect or add keepalive                 |

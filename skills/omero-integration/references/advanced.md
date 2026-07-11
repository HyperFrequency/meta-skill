# Advanced Features

Permissions, deletion, filesets/original files, cross-group queries, low-level services, and
object details.

## Deleting objects (asynchronous)

`conn.deleteObjects(type, ids, wait=?)` starts a server-side delete and returns a handle.

```python
conn.deleteObjects("Image", [101, 102], wait=True)     # block until done
conn.deleteObjects("Dataset", [10], wait=False)         # fire and forget
```

Types: `Project`, `Dataset`, `Image`, `Roi`, `Annotation`, and link types like
`ImageAnnotationLink`. Deleting a container may cascade to children depending on server config.

Monitor a long delete with a callback:

```python
from omero.callbacks import CmdCallbackI
handle = conn.deleteObjects("Project", [project_id])
cb = CmdCallbackI(conn.c, handle)
while not cb.block(500):        # poll every 500 ms
    pass
resp = cb.getResponse()
if isinstance(resp, omero.cmd.ERR):
    print("delete failed:", resp)
cb.close(True)                  # also closes the handle
```

## Filesets and original files

A **fileset** is the set of original files that were imported to produce one or more images
(OMERO 5.0+). Use it to get back the exact files a user uploaded.

```python
fs = image.getFileset()                 # None for pre-5.0 imports
if fs:
    fs.getId()
    for img in fs.copyImages():         # images sharing this fileset
        img.getName()
    for of in fs.listFiles():           # original imported files
        of.getPath(), of.getName(), of.getSize()
```

Download an original file with a `RawFileStore` (close it when done):

```python
rfs = conn.createRawFileStore()
rfs.setFileId(of.getId())
size, offset, chunk = of.getSize(), 0, 1024 * 1024
with open(of.getName(), 'wb') as f:
    while offset < size:
        data = rfs.read(offset, chunk)
        f.write(data); offset += len(data)
rfs.close()
```

## Group permissions

Permission strings map to named levels:

| String   | Level          | Meaning                                   |
| -------- | -------------- | ----------------------------------------- |
| `rw----` | PRIVATE        | only owner reads/writes                   |
| `rwr---` | READ-ONLY      | members read, owner writes                |
| `rwra--` | READ-ANNOTATE  | members read and annotate                 |
| `rwrw--` | READ-WRITE     | members read and write                    |

```python
group = conn.getGroupFromContext()
perms = group.getDetails().getPermissions()
str(perms)                              # e.g. 'rwra--'

for g in conn.getGroupsMemberOf():
    g.getName(), g.getDetails().getPermissions()

grp = conn.getObject("ExperimenterGroup", group_id)
for member in grp.getMembers():
    member.getFullName(), member.getOmeName()
```

Per-object capability flags:

```python
p = image.getDetails().getPermissions()
p.canEdit(); p.canAnnotate(); p.canLink(); p.canDelete()
```

## Cross-group queries

Data is group-scoped. To search everything you can see, set the special group `-1`; then pin to
the object's real group before mutating it.

```python
conn.SERVICE_OPTS.setOmeroGroup('-1')
image = conn.getObject("Image", image_id)
if image:
    conn.SERVICE_OPTS.setOmeroGroup(image.getDetails().getGroup().getId())
# reset
conn.SERVICE_OPTS.setOmeroGroup(conn.getEventContext().groupId)
```

## Administrative operations

```python
conn.isAdmin(); conn.isFullAdmin(); conn.getCurrentAdminPrivileges()
for admin in conn.getAdministrators():
    admin.getOmeName(), admin.getFullName()
for user in conn.getObjects("Experimenter"):
    user.getOmeName(), user.getFullName(), user.getEmail()
```

Act as another user (full admin only) — see `connection.md` for `suConn`. Setting an object's
owner requires admin and is done via `ann._obj.details.owner = omero.model.ExperimenterI(uid, False)`
before `save()`.

## Services

`BlitzGateway` exposes the underlying Ice services. Close the stateful ones
(`ThumbnailStore`, `RawFileStore`) when finished.

```python
conn.getUpdateService()      # saveObject / saveAndReturnObject / saveAndReturnArray
conn.getRoiService()         # findByImage, getShapeStatsRestricted (see rois.md)
conn.getMetadataService()    # loadSpecifiedAnnotations by type + namespace
conn.getQueryService()       # HQL-style queries via ParametersI
conn.createThumbnailStore()  # setPixelsId + getThumbnail; .close()
conn.createRawFileStore()    # setFileId + read; .close()
```

HQL example:

```python
params = omero.sys.ParametersI()
params.addLong("iid", image_id)
img = conn.getQueryService().findByQuery(
    "select i from Image i where i.id = :iid", params)
```

## Object details and event context

```python
d = image.getDetails()
d.getOwner().getOmeName(); d.getGroup().getName()
d.getCreationEvent().getTime(); d.getUpdateEvent().getTime()

ctx = conn.getEventContext()   # userId, userName, groupId, groupName, sessionId, isAdmin
```

## Troubleshooting

| Symptom               | Handling                                                                 |
| --------------------- | ------------------------------------------------------------------------ |
| `SecurityViolation` on delete/edit | you don't own the object or lack group permission — check `canDelete()`/`canEdit()` |
| `getObject` → `None`  | wrong group context — retry after `setOmeroGroup('-1')`                   |
| Long delete seems hung | monitor with `CmdCallbackI` rather than assuming failure                 |
| Leaked server resources | ensure `ThumbnailStore`/`RawFileStore`/tables are `.close()`d           |

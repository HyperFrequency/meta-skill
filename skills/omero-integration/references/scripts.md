# OMERO.scripts (Server-Side Batch)

An OMERO.script is a Python program that runs **on the server** and is callable from any OMERO
client (web, Insight, CLI). The server auto-generates a parameter UI from the script's
declared inputs. Because the code runs server-side, pixel data never leaves the machine — this
is the right tool for batch processing across many images.

## Structure

```python
#!/usr/bin/env python
import omero
from omero.gateway import BlitzGateway
import omero.scripts as scripts
from omero.rtypes import rlong, rstring, robject

def run_script():
    client = scripts.client(
        'My_Script.py',
        """Human-readable description shown in the client.""",
        scripts.String("Data_Type", optional=False, grouping="1",
                       values=[rstring('Dataset'), rstring('Image')],
                       default=rstring('Dataset'),
                       description="Source of images"),
        scripts.List("IDs", optional=False, grouping="2",
                     description="Dataset or Image IDs").ofType(rlong(0)),
        version="1.0",
    )
    try:
        conn = BlitzGateway(client_obj=client)          # reuse the script's session
        params = client.getInputs(unwrap=True)          # -> plain Python dict
        message = process(conn, params)
        client.setOutput("Message", rstring(message))   # what the client shows
    finally:
        client.closeSession()                           # ALWAYS close

if __name__ == "__main__":
    run_script()
```

Key rules: build the connection with `BlitzGateway(client_obj=client)` (never re-authenticate),
read inputs via `client.getInputs(unwrap=True)`, and always `client.closeSession()` in a
`finally`.

## Parameter types

```python
scripts.String("Name", optional=False, description="...")
scripts.String("Mode", values=[rstring('Fast'), rstring('Accurate')], default=rstring('Fast'))
scripts.Long("ImageID", optional=False).ofType(rlong(0))
scripts.List("ImageIDs", optional=False).ofType(rlong(0))
scripts.Float("Threshold", optional=True, min=0.0, max=1.0, default=0.5)
scripts.Bool("SaveResults", optional=True, default=True)
```

- `grouping="1"`, `"1.1"`, `"1.2"` nests parameters in the generated UI.
- `.ofType(rlong(0))` declares the element type of a `Long`/`List`.
- `values=[...]` turns a `String` into a dropdown; `min`/`max` bound numerics.

## Reading inputs / resolving images

```python
params = client.getInputs(unwrap=True)
data_type = params.get("Data_Type", "Image")
ids = params.get("IDs", [])

def get_images(conn, params):
    if params["Data_Type"] == "Dataset":
        return [img for did in params["IDs"]
                for img in conn.getObject("Dataset", did).listChildren()]
    return [conn.getObject("Image", iid) for iid in params["IDs"]]
```

## Returning outputs

`client.setOutput(name, value)` reports results back to the client. Wrap model objects with
`robject(obj._obj)` so the client can display/link them.

```python
client.setOutput("Message", rstring("Processed 10 images"))
client.setOutput("New_Image", robject(new_image._obj))       # created image
client.setOutput("Result_File", robject(file_ann._obj))      # file annotation
client.setOutput("Results_Table", robject(file_ann._obj))    # table via its FileAnnotation
```

For creating images inside a script use `createImageFromNumpySeq` (`pixels-rendering.md`);
for tables use the `sharedResources().newTable` flow (`tables.md`).

## Deployment and testing

Scripts live under the server's script directory, e.g. `OMERO_DIR/lib/scripts/<category>/`.
Manage them with the OMERO CLI:

```bash
python My_Script.py                 # syntax check locally
omero script upload My_Script.py    # install on the server
omero script list
omero script launch <SCRIPT_ID> IDs=123
```

## Robustness patterns

```python
# progress logging (print goes to server logs and, for some clients, the UI)
for i, image in enumerate(images):
    print(f"Processing {i+1}/{len(images)}: {image.getName()}")

# collect per-item errors instead of aborting the whole run
errors = []
for image in images:
    try:
        process_image(image)
    except Exception as e:
        errors.append(f"{image.getName()}: {e}")
message = "Done" if not errors else "Completed with errors:\n" + "\n".join(errors)
```

## Guidance

- Always `try/finally` with `client.closeSession()`; a leaked session ties up the server.
- Validate parameters before heavy work; return a clear `Message` on bad input.
- Process large datasets in batches to bound memory.
- Return created objects with `robject` so users can open them from the result panel.
- Version your script and use namespaces on any annotations/outputs it creates.

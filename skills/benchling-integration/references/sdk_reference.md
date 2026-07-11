# benchling-sdk Reference

Deep patterns for the official Python client. Method names and keyword arguments
below follow the documented `benchling-sdk` conventions, but signatures do drift
between releases — when in doubt, confirm against the version you installed:
https://benchling.com/sdk-docs/ and the source at
https://github.com/benchling/benchling-sdk

## Install & initialize

```bash
uv pip install benchling-sdk          # or: pip install benchling-sdk
# preview builds (not for production): pip install --pre benchling-sdk
```

Requires Python 3.8+ and API access enabled on the tenant.

```python
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

benchling = Benchling(url="https://<tenant>.benchling.com",
                      auth_method=ApiKeyAuth("<api_key>"))
```

> Import gotcha: it is `from benchling_sdk.benchling import Benchling`, not
> `from benchling_sdk import Benchling`.

## Client resources

The `Benchling` object is the root; every domain hangs off it as a resource with a
consistent CRUD surface:

```
dna_sequences  rna_sequences  aa_sequences  custom_entities  mixtures   # registry
containers  boxes  locations  plates                                    # inventory
entries                                                                 # ELN
workflow_tasks  requests                                                # workflows
folders  projects  users  teams  registries  schemas                    # org / metadata
```

CRUD pattern (names may be resource-specific, e.g. `dna_sequence_id`):

```python
resource.create(<Model>Create(...))
resource.get_by_id("<id>")
resource.list(**server_side_filters)      # -> paginated generator
resource.update("<id>", <Model>Update(...))
resource.archive(["<id>", ...], reason=EntityArchiveReason.OTHER)
```

## Custom schema fields

Wrap field dicts with the `fields()` helper; each value is itself `{"value": ...}`:

```python
from benchling_sdk.helpers.serialization_helpers import fields

f = fields({
    "concentration": {"value": "100 ng/uL"},
    "date_prepared": {"value": "2025-10-20"},   # YYYY-MM-DD
    "quality":       {"value": "High"},         # dropdown: exact option text
})
```

Values are **strings even for numbers**; dates are `YYYY-MM-DD`; dropdown values
must exactly match a configured option or you get a validation error.

## Registry entities

### DNA / RNA / AA sequences

```python
from benchling_sdk.models import DnaSequenceCreate, DnaSequenceUpdate

seq = benchling.dna_sequences.create(
    DnaSequenceCreate(
        name="pET28a-GFP",
        bases="ATCGATCGATCG",
        is_circular=True,
        folder_id="fld_abc123",
        schema_id="ts_abc123",                       # optional
        fields=fields({"gene_name": {"value": "GFP"}}),
    )
)

got = benchling.dna_sequences.get_by_id(seq.id)
print(f"{got.name}: {len(got.bases)} bp")

benchling.dna_sequences.update(
    seq.id,
    DnaSequenceUpdate(fields=fields({"gene_name": {"value": "eGFP"}})),
)
```

RNA uses `RnaSequenceCreate` with `bases` (`AUCG...`); AA uses `AaSequenceCreate`
with `amino_acids=...` instead of `bases`. Same CRUD flow.

### Custom entities & mixtures

`CustomEntityCreate` requires a `schema_id` (the entity type is defined by your
tenant's schema). `MixtureCreate` takes an `ingredients=[IngredientCreate(...)]`
list, each referencing a `component_entity_id` and an `amount`.

### Registering into a registry

Register at creation by passing `registry_id` (the `src_...` registry) **together
with** either an explicit `entity_registry_id` **or** a `naming_strategy` — never
both of the latter two:

```python
from benchling_sdk.models import DnaSequenceCreate, NamingStrategy

benchling.dna_sequences.create(
    DnaSequenceCreate(
        name="Construct-001", bases="ATCG", is_circular=True,
        folder_id="fld_abc123",
        registry_id="src_abc123",                 # registry to register into (required to register)
        naming_strategy=NamingStrategy.NEW_IDS,    # or IDS_FROM_NAMES (names must be unique)
        # ...or, instead of naming_strategy, assign an explicit id:
        # entity_registry_id="CONSTRUCT-001",
    )
)
```

## Inventory

```python
from benchling_sdk.models import ContainerCreate, ContainerUpdate, BoxCreate

box = benchling.boxes.create(
    BoxCreate(name="Freezer-A-Box-01", schema_id="box_schema_abc",
              parent_storage_id="loc_freezer_a", barcode="BOX001")
)

container = benchling.containers.create(
    ContainerCreate(name="Sample-001", schema_id="cont_schema_abc",
                    barcode="CONT001", parent_storage_id=box.id,
                    fields=fields({"volume": {"value": "50 uL"}}))
)

benchling.containers.transfer(container.id, destination_id="box_xyz789")
benchling.containers.update(container.id,
    ContainerUpdate(fields=fields({"volume": {"value": "45 uL"}})))
```

Plates take a `wells=[WellCreate(position="A1", entity_id=...)]` list. List
containers in a box by filtering `parent_storage_id=box.id`.

## Notebook (ELN)

```python
from benchling_sdk.models import EntryCreate

entry = benchling.entries.create(
    EntryCreate(name="Cloning 2025-10-20", folder_id="fld_abc123",
                schema_id="entry_schema_abc",
                fields=fields({"objective": {"value": "Clone GFP into pET28a"}}))
)
```

Update via `EntryUpdate`; link entities/results into the entry for traceability
(the exact link resource varies by SDK version — check the reference).

## Workflow tasks

```python
from benchling_sdk.models import WorkflowTaskCreate, WorkflowTaskUpdate

task = benchling.workflow_tasks.create(
    WorkflowTaskCreate(name="PCR Amplification", workflow_id="wf_abc123",
                       assignee_id="user_abc123", schema_id="task_schema_abc")
)
benchling.workflow_tasks.update(
    task.id, WorkflowTaskUpdate(status_id="status_complete_abc"))
```

## Pagination

`list()` returns a generator of pages — memory-efficient, but **single-use**:

```python
sequences = benchling.dna_sequences.list(folder_id="fld_abc123")  # server-side filter
print("total ~", sequences.estimated_count())
for page in sequences:
    for seq in page:
        process(seq)
# re-iterating `sequences` yields nothing; call list() again for a fresh generator
```

Prefer server-side filters (`folder_id`, `schema_id`, `name`) over pulling
everything and filtering in Python. `page_size` (max 100) tunes page size.

## Async tasks

Bulk mutations return a task id; wait for it before assuming completion. The SDK
ships a task-waiting helper (module/name varies by version — e.g. a
`wait_for_task`-style helper); poll with a sensible interval and a timeout, and
handle the "expired/timeout" case:

```python
# pattern (confirm helper import for your SDK version):
result = wait_for_task(benchling, task_id,
                       interval_wait_seconds=2, max_wait_seconds=600)
```

## Error handling

Catch typed exceptions from `benchling_sdk.errors` (e.g. `NotFoundError`,
`UnauthorizedError`, a validation error, and the `BenchlingError` base):

```python
from benchling_sdk.errors import NotFoundError, BenchlingError
try:
    benchling.dna_sequences.get_by_id("seq_missing")
except NotFoundError:
    ...   # handle 404
except BenchlingError as exc:
    ...   # anything else Benchling-specific
```

## Retry configuration

The client auto-retries transient failures (`429`, `502`, `503`, `504`) with
exponential backoff. Override via a retry-strategy argument at construction to
change max retries or disable retrying — see the SDK docs for the exact
`RetryStrategy` shape for your version.

## Custom / unsupported endpoints

For endpoints the typed resources don't cover, use the raw API escape hatch on the
client (`benchling.api.*`) to issue GET/POST with optional model parsing into an
SDK model. Confirm the exact helper names against the SDK reference.

## Forward compatibility

The SDK tolerates newer API values: unknown enum values are preserved, and
unrecognized polymorphic types deserialize to `UnknownType` (from
`benchling_sdk.models`) so you can still inspect raw data instead of crashing.

## Common pitfalls

- **Generators exhaust after one pass** — re-create with `list()`.
- **Field values are strings**, even numeric ones; dropdowns need exact option text.
- **`get_by_id` vs positional args** — pass the id; keyword names are resource
  specific (`dna_sequence_id`, `container_id`, ...).
- **Import path** is `benchling_sdk.benchling`, not top-level `benchling_sdk`.

## Links

- SDK docs: https://benchling.com/sdk-docs/
- Common examples: https://docs.benchling.com/docs/common-sdk-interactions-and-examples
- Source: https://github.com/benchling/benchling-sdk

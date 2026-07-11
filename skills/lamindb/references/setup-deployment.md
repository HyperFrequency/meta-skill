# Setup and Deployment

Install, authenticate, initialize an instance, and scale from a local SQLite dev
setup to a cloud PostgreSQL production deployment. Command flags reflect current
LaminDB; check `lamin <cmd> --help` for your version.

## Install

```bash
pip install lamindb

# Extras for specific formats/backends
pip install 'lamindb[gcp]'          # Google Cloud Storage
pip install 'lamindb[aws]'          # S3 (often already available)
pip install 'lamindb[zarr]'         # array storage / streaming
pip install 'lamindb[fcs]'          # flow-cytometry formats
pip install 'lamindb[gcp,zarr,fcs]' # combined

# Module plugins
pip install bionty                  # biological ontologies
pip install lamindb-wetlab          # wet-lab entities
pip install lamindb-clinical        # OMOP clinical data model
```

```python
import lamindb as ln; print(ln.__version__)
```

## Authenticate

```bash
lamin login        # prompts for an API key from https://lamin.ai account settings
```

Authentication collects only account metadata (email, handle); your datasets
stay in your own storage. Login is required even for local-only use, to enable
instance management and collaboration.

## Initialize an instance

An instance = a database (registries + provenance) + a storage backend (bytes).

```bash
# Local SQLite (dev)
lamin init --storage ./mydata --modules bionty
lamin init --storage ./mydata --modules bionty,wetlab

# Cloud storage + local SQLite (small teams)
lamin init --storage s3://my-bucket/path
lamin init --storage gs://my-bucket/path
lamin init --storage 's3://bucket?endpoint_url=http://minio.example.com:9000'

# Cloud storage + PostgreSQL (production)
lamin init --storage s3://my-bucket/path \
  --db postgresql://user:password@host:5432/dbname \
  --modules bionty --name production
```

The instance name defaults to the storage directory name unless `--name` is set.

## Connect / switch instances

```bash
lamin connect my-project                 # your instance by name
lamin connect account_handle/my-project  # by full path
lamin connect other-user/their-project   # shared instance (needs permission)
lamin info                               # current instance details
lamin close                              # disconnect
```

## Storage backends

- **Local** — fastest, offline, simplest; no collaboration.
- **AWS S3** — scalable, durable, collaborative. Needs
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (and region), and an IAM policy
  granting `s3:GetObject/PutObject/DeleteObject/ListBucket` on the bucket.
- **Google Cloud Storage** — `gcloud auth application-default login` or a
  service-account key via `GOOGLE_APPLICATION_CREDENTIALS`.
- **S3-compatible** (MinIO, Cloudflare R2) — pass `endpoint_url` in the storage
  URI and set the corresponding access keys.

## Database backends

- **SQLite** (default) — no server, ideal for development; not safe for
  concurrent writes and limited at scale.
- **PostgreSQL** (12+) — production-ready, concurrent access, better at scale.
  Append `?sslmode=require` for encrypted connections.

```bash
# Schema migrations
lamin migrate check       # is the DB schema compatible with installed lamindb?
lamin migrate deploy      # apply migrations
```

## Cache and settings

Cloud files are cached locally on access.

```bash
lamin cache set /path/to/cache
lamin cache get
lamin settings set dev-dir /path/to/project           # base for relative keys
lamin settings set sync-git-repo https://github.com/user/repo.git
```

```python
import lamindb as ln
ln.settings.cache_dir                     # current cache location
artifact.delete_cache()                   # evict one artifact
artifact.is_cached()                      # check before re-download
print(ln.setup.settings.user)             # handle/email/name
print(ln.setup.settings.instance)         # name/storage
```

Relevant environment variables: `LAMIN_CACHE_DIR`, `LAMIN_SETTINGS_DIR`,
`LAMINDB_SYNC_GIT_REPO`. For a shared multi-user host, set a system-wide cache
path (e.g. `lamindb_cache_path=/shared/cache/lamindb`) and grant the group
read/write on that directory.

## Deployment patterns

**Local dev → cloud production.** Develop against `./dev-data`; initialize a
separate cloud instance (`s3://prod-bucket` + PostgreSQL) for production. Move
data by re-saving exported artifacts into the production instance after
`lamin connect production`.

**Multi-region.** Initialize one instance per region (e.g. `us-production`,
`eu-production`), each with region-local storage and DB, for data-residency.

**Shared storage, personal instances.** Point multiple instances at the same
storage bucket but give each user their own PostgreSQL database, so everyone
sees shared bytes through personal registries.

## Security

- Prefer environment variables or IAM roles over hardcoded credentials; rotate
  keys regularly.
- Use PostgreSQL for multi-user access control; set bucket policies.
- Require SSL/TLS on DB connections; use VPCs and IP restrictions in cloud.
- Enable encryption at rest (S3/GCS) and in transit; maintain backups
  (`pg_dump`, S3 versioning, `lamin export`).

## Troubleshooting

- **Cannot connect** → `lamin info` to confirm the instance, re-`lamin login`,
  `lamin connect <name>`.
- **Storage permission denied** → verify credentials with `aws s3 ls` /
  `gsutil ls` and check the IAM policy.
- **DB connection error** → test with `psql <url>`; run `lamin migrate check`
  for version compatibility.
- **Cache full** → `lamin cache set` a larger disk, or clear
  `ln.settings.cache_dir`.

## Best practices

1. Start local (SQLite), scale to cloud (PostgreSQL + S3/GCS) for production.
2. Install only the modules/extras you need.
3. Size the cache to your working set; put it on a fast, roomy disk.
4. Enable object-store versioning for data protection.
5. Keep instance configuration as infrastructure-as-code for reproducibility.
6. Test backup and restore before you depend on them.

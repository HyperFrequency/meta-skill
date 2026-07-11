# LlamaIndex Data Connectors Guide

300+ data connectors via LlamaHub.

## Built-in loaders

### SimpleDirectoryReader

```python
from llama_index.core import SimpleDirectoryReader

# Load all files
documents = SimpleDirectoryReader("./data").load_data()

# Filter by extension
documents = SimpleDirectoryReader(
    "./data",
    required_exts=[".pdf", ".docx", ".txt"]
).load_data()

# Recursive
documents = SimpleDirectoryReader("./data", recursive=True).load_data()
```

### Web pages

```python
from llama_index.readers.web import SimpleWebPageReader, BeautifulSoupWebReader

# Simple loader
reader = SimpleWebPageReader()
documents = reader.load_data(["https://example.com"])

# Advanced (BeautifulSoup)
reader = BeautifulSoupWebReader()
documents = reader.load_data(urls=[
    "https://docs.python.org",
    "https://numpy.org"
])
```

### PDF

```python
from llama_index.readers.file import PDFReader

reader = PDFReader()
documents = reader.load_data("paper.pdf")
```

### GitHub

```python
from llama_index.readers.github import GithubRepositoryReader

reader = GithubRepositoryReader(
    owner="facebook",
    repo="react",
    filter_file_extensions=[".js", ".jsx"],
    verbose=True
)

documents = reader.load_data(branch="main")
```

### Database (SQL)

```bash
pip install llama-index-readers-database
```

```python
from llama_index.readers.database import DatabaseReader

# Connect via URI (Postgres, MySQL, SQLite, ... any SQLAlchemy URL)
reader = DatabaseReader(uri="postgresql://user:pass@localhost:5432/db")

# Each returned row becomes one Document; supply the SELECT at load time
documents = reader.load_data(query="SELECT title, body FROM articles")
```

Note: the constructor param is `uri=` (not `sql_database_uri`). You can instead
pass a SQLAlchemy `engine=`, a prebuilt `sql_database=SQLDatabase(...)`, or the
discrete `scheme/host/port/user/password/dbname` args. `load_data(query=...)`
runs the query and maps each row to a Document.

### JSON / JSONL files

```bash
pip install llama-index-readers-json
```

```python
from llama_index.readers.json import JSONReader

reader = JSONReader(is_jsonl=False)            # is_jsonl=True for .jsonl files
documents = reader.load_data(input_file="data.json")
```

Note: `load_data` reads a **local file path** (`input_file`), not a URL — to
ingest a JSON API response, fetch it to a file first (or build `Document`
objects yourself). `levels_back` / `collapse_length` control how deeply nested
structure is flattened into the embedded text.

## LlamaHub connectors

Visit https://llamahub.ai for 300+ connectors:
- Notion, Google Docs, Confluence
- Slack, Discord, Twitter
- PostgreSQL, MongoDB, MySQL
- S3, GCS, Azure Blob
- Stripe, Shopify, Salesforce

### Install from LlamaHub

```bash
pip install llama-index-readers-notion
```

```python
from llama_index.readers.notion import NotionPageReader

reader = NotionPageReader(integration_token="your-token")
documents = reader.load_data(page_ids=["page-id"])
```

## Custom loader

```python
from llama_index.core.readers.base import BaseReader
from llama_index.core import Document

class CustomReader(BaseReader):
    def load_data(self, file_path: str):
        # Your custom loading logic
        with open(file_path) as f:
            text = f.read()
        return [Document(text=text, metadata={"source": file_path})]

reader = CustomReader()
documents = reader.load_data("data.txt")
```

## Resources

- **LlamaHub**: https://llamahub.ai
- **Data Connectors Docs**: https://developers.llamaindex.ai/python/framework/modules/data_connectors/

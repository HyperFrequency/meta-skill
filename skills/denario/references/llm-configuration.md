# LLM Provider Configuration

Denario's agents run on the LLM backends exposed by AG2 / LangGraph. In practice that means
you need credentials for at least one provider — most commonly **OpenAI** or **Google
Gemini / Vertex AI**; other AG2/LangGraph-compatible backends (Azure OpenAI, Anthropic via
compatible interfaces, custom endpoints) may also work depending on version and config.

## Supplying keys

### Environment variables

```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

Add them to `~/.bashrc` / `~/.zshrc` for persistence. On Windows use `set VAR=value` or the
System Properties → Environment Variables dialog.

### `.env` file

```env
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
```

Load it **before** importing Denario:

```python
from dotenv import load_dotenv
load_dotenv()
from denario import Denario
den = Denario(project_dir="./project")
```

### Docker

```bash
docker run -p 8501:8501 --env-file .env --rm pablovd/denario:latest

docker run -p 8501:8501 \
  -e OPENAI_API_KEY=sk-... \
  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials.json \
  -v /local/creds.json:/credentials.json \
  --rm pablovd/denario:latest
```

## Obtaining keys

### OpenAI

Create an account at platform.openai.com → API Keys → "Create new secret key" → export as
`OPENAI_API_KEY`.

### Google Vertex AI (service account)

1. In the Google Cloud Console, create/select a project and enable the **Vertex AI API**.
2. Authenticate one of two ways:
   - **User creds**: `gcloud auth application-default login`, then
     `gcloud config set project YOUR_PROJECT_ID`.
   - **Service account**:
     ```bash
     gcloud iam service-accounts create denario-sa --display-name="Denario SA"
     gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:denario-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/aiplatform.user"
     gcloud iam service-accounts keys create credentials.json \
       --iam-account=denario-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
     ```
3. Point Denario at it:
   ```python
   import os
   os.environ["GOOGLE_CLOUD_PROJECT"] = "YOUR_PROJECT_ID"
   os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/credentials.json"
   ```

Enable `aiplatform.googleapis.com` (and `compute.googleapis.com` if needed):
`gcloud services enable aiplatform.googleapis.com`.

## Model selection

Which model powers each stage is version-dependent and configured through
environment/upstream config rather than a signature this skill can pin. Consult upstream
docs for the current mechanism. Practically: cheaper/faster models (e.g. a Gemini flash
tier) speed up runs at some cost to depth; stronger models improve reasoning-heavy stages
(idea, method) at higher price.

## Cost management

- Every stage makes LLM calls; a full `idea → method → results → paper` run can be costly
  and non-deterministic. `get_results()` (code execution) is usually the heaviest.
- Monitor usage: OpenAI at platform.openai.com/usage; Google Cloud in Billing. Set billing
  alerts.
- Reuse artifacts: once an idea/method/results file is good, load it with the `set_*`
  method instead of regenerating.

## Security

- Never commit keys. Add to `.gitignore`: `.env`, `credentials.json`, `*-service-account*.json`.
- Rotate keys periodically and revoke old ones.
- Grant service accounts least privilege (`roles/aiplatform.user`, not broad admin).
- Prefer a secret manager for production over plaintext files.

## Troubleshooting

- **"API key not found"**: confirm the variable is exported (`echo $OPENAI_API_KEY`), the
  `.env` is in the working directory, and `load_dotenv()` runs *before* importing Denario.
- **Vertex auth failures**: verify `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON,
  the service account has `aiplatform.user`, and the API is enabled.
- **Rate limiting**: reduce concurrency, back off exponentially, or raise your plan limits.
- **Docker env not seen**: use `--env-file .env`, mount credential files with `-v`, and
  check inside the container with `docker exec <id> env`.

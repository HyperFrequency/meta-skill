# Benchling Authentication Reference

Benchling exposes three auth mechanisms. Pick by who is calling and how many
users share the credential.

| Method | Best for | Audit attribution |
| ------ | -------- | ----------------- |
| API key (HTTP Basic) | personal scripts, prototyping, single user | the key's owner |
| OAuth2 client credentials | apps, service accounts, production | the app (and, with user context, the user) |
| OpenID Connect (OIDC) | enterprise SSO with an existing IdP | the matched user |

All requests must use HTTPS; plain HTTP is rejected.

## 1. API key (HTTP Basic Auth)

The key is sent as the Basic-auth **username** with an **empty password**. Generate
it under Profile Settings in the Benchling UI (shown once — store it immediately).

Python SDK:

```python
import os
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

benchling = Benchling(
    url=os.environ["BENCHLING_TENANT_URL"],
    auth_method=ApiKeyAuth(os.environ["BENCHLING_API_KEY"]),
)
```

Raw HTTP (note the trailing colon = empty password):

```bash
curl -X GET https://<tenant>.benchling.com/api/v2/dna-sequences \
  -u "$BENCHLING_API_KEY:"
```

## 2. OAuth2 client credentials

Register an App in the Developer Console (admin required) to get a client ID and
secret. The SDK exchanges them for a bearer token and refreshes automatically.

```python
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.client_credentials_oauth2 import ClientCredentialsOAuth2

benchling = Benchling(
    url="https://<tenant>.benchling.com",
    auth_method=ClientCredentialsOAuth2(
        client_id=os.environ["BENCHLING_CLIENT_ID"],
        client_secret=os.environ["BENCHLING_CLIENT_SECRET"],
    ),
)
```

Raw token flow:

```bash
# 1. exchange credentials for a token
curl -X POST https://<tenant>.benchling.com/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$BENCHLING_CLIENT_ID" \
  -d "client_secret=$BENCHLING_CLIENT_SECRET"
# -> {"access_token": "...", "token_type": "Bearer", "expires_in": 3600}

# 2. call the API with the bearer token
curl -X GET https://<tenant>.benchling.com/api/v2/dna-sequences \
  -H "Authorization: Bearer <access_token>"
```

Prefer OAuth over shared API keys for any multi-user app so the audit log
attributes actions to the acting user rather than to a single key owner.

## 3. OpenID Connect (OIDC / SSO)

Enterprise only. Your IdP (Okta, Azure AD, ...) issues an ID token containing an
`email` claim; Benchling verifies it against your IdP's OpenID configuration URL and
matches the user by email. Pass the ID token as a bearer token (SDK: the OIDC auth
method; HTTP: `Authorization: Bearer <id_token>`). Requires an enterprise tenant,
a configured IdP that emits `email`, and matching user emails on both sides.

## Verifying credentials

`GET /api/v2/users/me` is the cheapest authenticated call — use it as a health
check:

```python
try:
    user = benchling.users.get_me()
    print(f"Authenticated as {user.name} <{user.email}>")
except Exception as exc:
    print(f"Auth failed: {exc}")
```

## Security practices

- **Storage:** environment variables or a secret manager (AWS Secrets Manager,
  Vault). Never commit keys, never hardcode, never share over chat/email. Add
  `.env` to `.gitignore` if you use `python-dotenv`.
- **Least privilege:** grant Apps only the orgs/teams/projects/folders they need,
  in the Developer Console. API access mirrors UI permissions — suspended users and
  archived apps lose access.
- **Rotation:** rotate on a schedule (e.g. every 90 days) and immediately on
  compromise. Generate the new credential, cut over, verify, then delete the old.
- **Network:** HTTPS only; some enterprise tenants also support IP allowlisting
  (contact Benchling support).

## Rate limits

Roughly **100 requests per 10 seconds** per user/app. Exceeding it returns `429`.
The SDK retries `429`/`5xx` with exponential backoff automatically; still, batch and
cache to avoid hammering the limit.

## Auth error matrix

| Status | Meaning | First thing to check |
| ------ | ------- | -------------------- |
| `401 Unauthorized` | missing/invalid/expired credential or malformed header | key not deleted/expired; header is `Authorization: Bearer <token>` or Basic `key:` |
| `403 Forbidden` | authenticated but not permitted | user/app access to that project/folder; grant it in Developer Console |
| `429 Too Many Requests` | rate limit hit | back off (SDK auto-retries); reduce request rate, cache |

## Advanced: custom HTTPS client

For corporate proxies or a custom CA bundle, pass your own `httpx.Client`:

```python
import httpx
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth

benchling = Benchling(
    url="https://<tenant>.benchling.com",
    auth_method=ApiKeyAuth(os.environ["BENCHLING_API_KEY"]),
    httpx_client=httpx.Client(verify="/path/to/ca-bundle.crt", timeout=30.0),
)
```

> The exact constructor keyword for a custom client and the OIDC auth-method import
> path vary across `benchling-sdk` versions — confirm against the SDK reference for
> your installed version: https://benchling.com/sdk-docs/

## Multi-tenant

Hold one `Benchling` client per tenant, keyed by name, and select the one you need:

```python
clients = {
    name: Benchling(url=cfg["url"], auth_method=ApiKeyAuth(cfg["api_key"]))
    for name, cfg in {
        "prod":    {"url": "https://prod.benchling.com",    "api_key": os.environ["PROD_API_KEY"]},
        "staging": {"url": "https://staging.benchling.com", "api_key": os.environ["STAGING_API_KEY"]},
    }.items()
}
prod_sequences = clients["prod"].dna_sequences.list()
```

## Links

- Authentication docs: https://docs.benchling.com/docs/authentication
- Developer Console: `https://<tenant>.benchling.com/developer`
- SDK docs: https://benchling.com/sdk-docs/

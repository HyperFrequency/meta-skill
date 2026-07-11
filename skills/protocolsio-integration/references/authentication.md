# Authentication

All protocols.io API v3 calls authenticate with a bearer token:

```
Authorization: Bearer <ACCESS_TOKEN>
```

Verify the exact host and paths at <https://apidoc.protocols.io/>; base URL is
`https://www.protocols.io/api/v3`.

## Token types

- **Client access token** — reaches all public content plus the *token owner's* own
  private content. Use this for scripts that operate on your own account.
- **OAuth access token** — reaches all public content plus the private content of a
  *third user* who has granted your application access. Use this when building a
  multi-user integration.

## OAuth flow

Three legs: send the user to authorize, exchange the returned code for tokens, then
refresh before expiry.

### 1. Authorize

Redirect the user to the authorize endpoint:

```
GET /oauth/authorize
  ?client_id=<CLIENT_ID>
  &redirect_uri=<REDIRECT_URI>
  &response_type=code
  &state=<RANDOM_ANTI_CSRF_STRING>
```

Always send `state` and validate it on return to defend against CSRF. `redirect_uri`
must match your registered URI exactly.

### 2. Exchange code for tokens

protocols.io redirects to `redirect_uri` with `?code=...`. Exchange it:

```
POST /oauth/token
  grant_type=authorization_code
  code=<AUTH_CODE>
  client_id=<CLIENT_ID>
  client_secret=<CLIENT_SECRET>
  redirect_uri=<REDIRECT_URI>   # must equal the value from step 1
```

Response fields:

- `access_token` — bearer token for API calls.
- `token_type` — `Bearer`.
- `expires_in` — lifetime in seconds (commonly ~1 year).
- `refresh_token` — used to mint a new access token.

### 3. Refresh

Before `expires_in` elapses:

```
POST /oauth/token
  grant_type=refresh_token
  refresh_token=<REFRESH_TOKEN>
  client_id=<CLIENT_ID>
  client_secret=<CLIENT_SECRET>
```

## Rate limits

- Standard endpoints: ~100 requests/minute per user.
- PDF export (`/view/<uri>.pdf`): ~5/min signed-in, ~3/min anonymous.

On `429`, honor `Retry-After`; back off exponentially on `5xx`.

## Security notes

- Read tokens from environment variables or a secret manager — never hardcode or log
  them, and never commit them to version control.
- Store the `refresh_token` as securely as the access token; it is a long-lived credential.
- Keep the `redirect_uri` byte-identical between the authorize and token requests, or
  the exchange fails.

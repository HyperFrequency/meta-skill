# LabArchives Authentication

## Two credential layers

LabArchives API access combines an application-level identity with a per-user
identity. You need both.

**Institutional (from your administrator)**

- `access_key_id` — institution-level identifier for the calling application.
- `access_password` — the paired secret.

These are provisioned by your LabArchives administrator and require an Enterprise
license with API access enabled. If you do not have them, contact your admin or
`support@labarchives.com`.

**User (self-configured)**

- Account email (e.g. `researcher@university.edu`).
- **External-applications password** — a dedicated API secret, distinct from the
  normal login password.

### Generating the external-applications password

1. Log into your notebook (e.g. `mynotebook.labarchives.com`, or your institutional
   URL).
2. Open **Account Settings** (your name, top-right).
3. Go to the **Security & Privacy** tab.
4. Find **External Applications** and generate/reset the password.
5. Copy it immediately — it is shown once. Treat it like an API token; rotate it if
   leaked.

## Regional endpoints

Pick the base URL that matches your tenant. Using the wrong region returns 401 even
with correct credentials.

| Region           | Base URL                            | Tenant looks like              |
| ---------------- | ----------------------------------- | ------------------------------ |
| US/International | `https://api.labarchives.com/api`   | `mynotebook.labarchives.com`   |
| Australia        | `https://auapi.labarchives.com/api` | `aunotebook.labarchives.com`   |
| UK              | `https://ukapi.labarchives.com/api` | `uknotebook.labarchives.com`   |

## Store credentials in the environment

Keep all four values out of source. Environment variables (or a secret manager) are
preferred; if you must use a file, add it to `.gitignore`.

```bash
export LA_API_URL="https://api.labarchives.com/api"
export LA_ACCESS_KEY_ID="your_key_id"
export LA_ACCESS_PASSWORD="your_access_password"
export LA_USER_EMAIL="researcher@university.edu"
export LA_USER_EXTERNAL_PASSWORD="your_external_app_password"
```

## Auth flow — Python wrapper

The community `labarchivespy` wrapper exposes `Client.make_call(api_class,
api_method, params=...)`, returning a `requests.Response`.

```python
import os, xml.etree.ElementTree as ET
from labarchivespy.client import Client

client = Client(os.environ["LA_API_URL"],
                os.environ["LA_ACCESS_KEY_ID"],
                os.environ["LA_ACCESS_PASSWORD"])

resp = client.make_call("users", "user_access_info",
    params={"login_or_email": os.environ["LA_USER_EMAIL"],
            "password": os.environ["LA_USER_EXTERNAL_PASSWORD"]})

resp.raise_for_status()
uid = ET.fromstring(resp.content)[0].text   # UID for all later calls
```

## Auth flow — raw requests (no wrapper)

Auth params travel as query-string parameters on GET calls.

```python
import os, requests

url = f'{os.environ["LA_API_URL"]}/users/user_access_info'
params = {
    "access_key_id": os.environ["LA_ACCESS_KEY_ID"],
    "access_password": os.environ["LA_ACCESS_PASSWORD"],
    "login_or_email": os.environ["LA_USER_EMAIL"],
    "password": os.environ["LA_USER_EXTERNAL_PASSWORD"],
}
r = requests.get(url, params=params, timeout=30)
r.raise_for_status()
```

Note: for **attachment uploads** the auth params go in the multipart form **body**,
not the query string (see `api_reference.md`).

## Auth flow — R

```r
library(httr); library(xml2)
r <- GET(
  paste0(Sys.getenv("LA_API_URL"), "/users/user_access_info"),
  query = list(
    access_key_id  = Sys.getenv("LA_ACCESS_KEY_ID"),
    access_password= Sys.getenv("LA_ACCESS_PASSWORD"),
    login_or_email = Sys.getenv("LA_USER_EMAIL"),
    password       = Sys.getenv("LA_USER_EXTERNAL_PASSWORD")))
uid <- xml_text(xml_find_first(read_xml(content(r, "text")), "//uid"))
```

## OAuth2 (new app integrations)

New third-party integrations use OAuth 2.0; legacy API-key auth (above) still works
for direct scripting. For an app, register with LabArchives to obtain a client ID +
secret, run the authorization-code flow, exchange the code for an access token, and
send that token on API requests. Contact LabArchives developer support for the
current OAuth endpoints. A worked flow lives in `integrations.md`.

## Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| **401 Unauthorized** | Wrong `access_key_id`/`access_password`, or whitespace in a config value | Re-verify with your admin; strip stray whitespace |
| **401** despite correct keys | Using the login password instead of the external-applications password | Regenerate and use the external-applications password |
| **401** despite correct password | Wrong regional base URL | Match the base URL to your tenant's region |
| **401**, account never worked | API access not enabled | Ask your admin to enable API access on an Enterprise license |
| **403 Forbidden** | Insufficient role, or no access to that `nbid`; account suspended | Confirm role/notebook access; check account status |
| **Empty response** | Missing required `uid`/`nbid` | Supply all required params |

### Network behind a firewall/proxy

```python
proxies = {"http": "http://proxy.example.edu:8080",
           "https": "http://proxy.example.edu:8080"}
requests.get(url, params=params, proxies=proxies)
```

Avoid `verify=False`; disabling TLS verification is for one-off testing only, never
production.

## Security practices

- Never commit credentials; use env vars or a secret manager (AWS Secrets Manager,
  Vault, OS keychain).
- Rotate the external-applications password periodically and after any suspected
  leak; regenerate API keys on a schedule.
- Apply least privilege — request only the access an integration needs, and use
  separate credentials per application.
- Review API access logs for anomalies where available.

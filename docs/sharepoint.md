# SharePoint

Pi-Plane is being taught to keep documents of work items in SharePoint document libraries, so that files that need
review and acceptance live where the organisation already keeps its documents. This page describes what is there
today, how to register the application in Microsoft Entra, and what is still to come.

> **Status: groundwork, not tried against a real tenant.** What exists is the connection to Microsoft Graph, the
> instance settings and a "Test connection" button. Nothing can be stored in SharePoint yet. The code was written
> from Microsoft's documentation and is tested against a fake Microsoft only: no step below, and no answer of Graph
> the code expects, has been confirmed against a live Microsoft 365 tenant. Steps and behaviours that most need that
> confirmation are marked **(unverified)**. The first test on a real tenant may well bring corrections.

## How Pi-Plane reaches SharePoint

- **As the application, not as the person.** Pi-Plane signs in to Microsoft Graph with the OAuth 2.0 client
  credentials flow (an app registration with a client secret). No per-user Microsoft token is asked for or stored,
  so it also works for people who sign in to Pi-Plane another way, and for background jobs.
- **Least privilege: `Sites.Selected`.** With this application permission the app can reach no site at all until a
  SharePoint administrator grants it access to a specific site. Pi-Plane never needs `Sites.Read.All` or
  `Sites.ReadWrite.All`.
- **Pi-Plane is the gate.** Because access is as the application, SharePoint's own per-user permissions are not
  applied to what people do through Pi-Plane. Membership of the Pi-Plane project will decide who sees a document
  (this comes with the document store). People who open the library in SharePoint itself are still subject to
  SharePoint's permissions.
- **Worldwide cloud only.** The client talks to `login.microsoftonline.com` and `graph.microsoft.com`, and accepts
  sites on `<tenant>.sharepoint.com`. The national clouds (US Government, China) have other hosts and are not
  supported.

## Registering the application in Microsoft Entra

You need a role that can register applications and grant admin consent (for example Cloud Application
Administrator), and a SharePoint administrator (or an owner of the site collection) for step 4.

1. **Register the app.** Entra admin center → **App registrations → New registration**. Name it (for example
   "Pi-Plane"), supported account types **Accounts in this organizational directory only**. No redirect URI is
   needed. Note the **Application (client) ID** and the **Directory (tenant) ID** from the Overview page.
2. **Add the permission.** **API permissions → Add a permission → Microsoft Graph → Application permissions →
   `Sites.Selected`**, then **Grant admin consent** for the tenant. Remove the default delegated `User.Read` if you
   like: Pi-Plane does not use it here.
3. **Create a secret.** **Certificates & secrets → New client secret**. Copy the secret **value** (not the secret
   ID); it is shown once. Note when it expires: Pi-Plane cannot renew it, and the connection stops working on that
   day. (Signing in with a certificate instead of a secret is planned, not built.)
4. **Grant the app access to the site (unverified).** `Sites.Selected` alone gives access to nothing. For each site
   Pi-Plane may use, an administrator creates a permission on the site for the application. Pi-Plane will upload
   files, so the role is `write` (`read` is enough for "Test connection").

   With Microsoft Graph (for example in Graph Explorer, signed in as an administrator who consented to
   `Sites.FullControl.All`), first find the ID of the site, then create the permission:

   ```http
   GET https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/Projects?$select=id

   POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
   Content-Type: application/json

   {
     "roles": ["write"],
     "grantedToIdentities": [
       { "application": { "id": "<Application (client) ID>", "displayName": "Pi-Plane" } }
     ]
   }
   ```

   Or with PnP PowerShell, as a SharePoint administrator:

   ```powershell
   Connect-PnPOnline -Url https://contoso.sharepoint.com/sites/Projects -Interactive
   Grant-PnPAzureADAppSitePermission -AppId "<Application (client) ID>" -DisplayName "Pi-Plane" `
     -Site https://contoso.sharepoint.com/sites/Projects -Permissions Write
   ```

   To see or remove grants later: `GET /sites/{site-id}/permissions` and
   `DELETE /sites/{site-id}/permissions/{permission-id}`, or `Get-PnPAzureADAppSitePermission` and
   `Revoke-PnPAzureADAppSitePermission`.

   Both forms are taken from Microsoft's and PnP's documentation and were **not run** by the authors of this
   integration. In particular not confirmed: the exact role names your tenant accepts, the permission the caller
   needs, and how long a new grant takes to apply.

## Configuring Pi-Plane

Open the admin app (God Mode) → **Integrations → SharePoint**.

1. Enter the **Directory (tenant) ID**, the **Application (client) ID** and the **client secret**, and save.
2. Press **Test connection**. Without a site URL it only signs in to Microsoft, which proves the three values. With
   the address of a site (for example `https://contoso.sharepoint.com/sites/Projects`) it also looks the site up
   and lists its document libraries, which proves the grant of step 4. The test always uses the saved values, so
   save before testing. The site URL is used for the test only; it is not stored.
3. Switch SharePoint on with the switch at the top. It can only be switched on once the credentials are saved.

The same values can be given through the environment before the first start; like every instance setting they are
copied into the database once, by `configure_instance`, and the admin app rules from then on.

| Key                        | Meaning                                                                                      | Default            |
| -------------------------- | -------------------------------------------------------------------------------------------- | ------------------ |
| `IS_SHAREPOINT_ENABLED`    | `1` switches the integration on.                                                             | `0`                |
| `SHAREPOINT_TENANT_ID`     | Directory (tenant) ID (a GUID), or a domain of the tenant such as `contoso.onmicrosoft.com`. | empty              |
| `SHAREPOINT_CLIENT_ID`     | Application (client) ID of the app registration (a GUID).                                    | empty              |
| `SHAREPOINT_CLIENT_SECRET` | The value of the client secret. Stored encrypted, like the other secrets of the instance.    | empty              |
| `SHAREPOINT_MAX_FILE_SIZE` | Largest file for SharePoint, in bytes, from 1 MB to 250 GB. Empty means the default.         | 524288000 (500 MB) |

`SHAREPOINT_MAX_FILE_SIZE` has nothing to do with `FILE_SIZE_LIMIT` ([file uploads](file-uploads.md)): that one
bounds what goes into Pi-Plane's own storage. Nothing enforces the SharePoint size yet, because nothing is uploaded
yet.

The apps learn whether SharePoint can be used from `is_sharepoint_enabled` in the instance information
(`GET /api/instances/`): true when it is switched on and the three credentials are saved. No credential is part of
that answer. The client secret is readable only where the other instance secrets are: by an instance administrator
in the admin app.

### What "Test connection" tells you

| Message is about                           | `error_code`            | Usual cause                                                                           |
| ------------------------------------------ | ----------------------- | ------------------------------------------------------------------------------------- |
| The client secret is not accepted          | `invalid_credentials`   | The secret ID was pasted instead of its value, or the secret belongs to another app.  |
| The client secret has expired              | `secret_expired`        | Create a new secret and save it.                                                      |
| The client ID is unknown in this tenant    | `application_not_found` | A typo, or the app is registered in another tenant.                                   |
| The tenant is unknown                      | `tenant_not_found`      | A typo in the tenant ID.                                                              |
| The application has no access to this site | `site_access_denied`    | Step 4 was not done for this site. This is what `Sites.Selected` is meant to do.      |
| No site at this address                    | `site_not_found`        | A typo in the address, or the address of a page or folder that is not under the site. |
| Graph does not accept the token            | `token_rejected`        | The `Sites.Selected` permission or the admin consent is missing.                      |
| Microsoft is limiting requests             | `throttled`             | Try again later.                                                                      |
| Microsoft could not be reached             | `transport_error`       | The API server has no route to Microsoft (firewall, proxy, DNS).                      |
| The address is not a SharePoint site       | `invalid_site_url`      | Only `https://<tenant>.sharepoint.com/...` is accepted.                               |
| Nothing is saved yet                       | `not_configured`        | Save the three credentials first.                                                     |

Which answer Microsoft really gives in each case is **unverified**: the mapping follows the documented error
numbers of the sign-in service (`AADSTS7000215`, `AADSTS7000222`, `AADSTS700016`, `AADSTS90002`, `AADSTS900023`)
and the HTTP status of Graph (403, 404, 401). It is possible, for example, that Graph answers a site without a
grant with 404 instead of 403, in which case the message will say "no site at this address". Below the message
the admin app shows what Microsoft itself said, shortened, which helps in such a case.

The API server must be able to open HTTPS connections to `login.microsoftonline.com` and `graph.microsoft.com`.
Proxy settings of the environment (`HTTPS_PROXY`) are deliberately not used by this client.

## What is not built yet

- **Storing documents.** No upload, download, thumbnail or version call exists; no document or version is recorded
  in Pi-Plane. This is the next step (the document store, with a native backend for installations without
  SharePoint).
- **Choosing a library.** A workspace administrator will pick the site, the library and a root folder in the
  workspace settings, and a project may override them. Today a site is only looked up by "Test connection".
- **Anything in the web app.** `is_sharepoint_enabled` is exposed, and nothing reads it yet.
- **Certificate credentials** in place of a client secret, and a warning before the secret expires.
- **Browser access to Microsoft.** Whether the browser can upload to and download from Microsoft directly (CORS), or
  whether Pi-Plane has to pass the bytes through, needs a real tenant to decide.
- **National clouds**, and SharePoint Server (on premises), are out of scope.

## For developers

- `apps/api/plane/utils/sharepoint/client.py`: `SharePointClient`. Every network exchange goes through `_send`
  (time-outs, a cap on the size of an answer, a bounded retry on 429 and 503 that honours `Retry-After`), every
  Graph call through `request` (bearer token, one token refresh on 401, typed errors). The token is cached in the
  Django cache (Redis) until five minutes before it expires. The secret and the tokens are kept out of logs and
  error texts. New Graph calls are small methods that build a path from validated IDs.
- `apps/api/plane/utils/sharepoint/errors.py`: the errors, each with a stable `code`.
- `apps/api/plane/utils/sharepoint/config.py`: reading the settings, `get_sharepoint_client()`,
  `is_sharepoint_enabled()`, `get_sharepoint_max_file_size()`.
- `POST /api/instances/sharepoint/test-connection/` (instance administrators; body `{"site_url": "..."}`, optional):
  `apps/api/plane/license/api/views/sharepoint.py`.
- Tests use `httpx.MockTransport`; nothing reaches a network:
  `apps/api/plane/tests/unit/utils/test_sharepoint_client.py`,
  `apps/api/plane/tests/contract/app/test_sharepoint_instance_app.py`.

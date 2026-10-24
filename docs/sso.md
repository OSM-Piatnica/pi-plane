# Single sign-on (OpenID Connect)

Pi-Plane signs people in through OpenID Connect (authorization code flow with PKCE, `state` and `nonce`). Providers are
described in `apps/api/plane/authentication/provider/oidc/`; everything else (sign-in and callback URLs, the instance
settings, the buttons on the sign-in screens, ID token validation) is shared.

| Provider           | Key           | Notes                                                                         |
| ------------------ | ------------- | ----------------------------------------------------------------------------- |
| Microsoft Entra ID | `entra`       | One tenant only. People are bound by tenant id + object id.                   |
| Google             | `google-oidc` | Optionally one Workspace domain (`hd`). Separate from the older Google login. |
| Any OIDC provider  | `oidc`        | By issuer URL (Keycloak, Okta, Authentik, ...). The email must be verified.   |

## Microsoft Entra ID

1. In the Entra admin center: **App registrations → New registration**, supported account types **Accounts in this
   organizational directory only**. Redirect URI (platform **Web**): `<your Pi-Plane URL>/auth/oidc/entra/callback/`.
2. **Certificates & secrets → New client secret**. Copy the secret **value**.
3. In Pi-Plane, open god mode → Authentication → **Microsoft Entra ID** and fill the form (or set the environment):

   ```
   IS_ENTRA_ENABLED=1
   ENTRA_CLIENT_ID=<Application (client) ID>
   ENTRA_CLIENT_SECRET=<secret value>
   ENTRA_TENANT_ID=<Directory (tenant) ID>
   ENTRA_ALLOWED_EMAIL_DOMAINS=piatnica.com.pl   # optional
   ```

The tenant id must be the GUID: `common`, `organizations` and domain names are refused, because the tenant is what
Pi-Plane trusts. A person is recognised by `tid:oid` (both immutable), so renaming a mailbox does not create a second
account and nobody else can take an account over by getting the same address.

## Google

Create an OAuth client (type **Web application**) in the Google Cloud console with the redirect URI
`<your Pi-Plane URL>/auth/oidc/google-oidc/callback/`, then set `IS_GOOGLE_OIDC_ENABLED=1`, `GOOGLE_OIDC_CLIENT_ID` and
`GOOGLE_OIDC_CLIENT_SECRET`. To accept only one Google Workspace, also set `GOOGLE_OIDC_HOSTED_DOMAIN`. People are
bound by their Google account id. The older `IS_GOOGLE_ENABLED` login keeps working independently.

## How people are matched

1. By the identity at the provider (`Account.provider_account_id`). If that is known, that user signs in.
2. Otherwise by email address. The identity is then bound to that user, **unless** the user is already bound to a
   different identity of the same provider (`OIDC_IDENTITY_MISMATCH`).
3. Otherwise a new user is created, if `<KEY>_ENABLE_SIGNUP` is `1` (or they have a workspace invite).

`<KEY>_ENABLE_SIGNUP` is independent of `ENABLE_SIGNUP` (email sign-up): a corporate instance can keep email sign-up
closed and still create accounts for everyone in its tenant. Deactivated accounts and bots are refused as with every
other sign-in. With `ENABLE_<KEY>_SYNC=1` the name is refreshed from the provider at every sign-in. No token of the
provider is stored.

## Adding another provider

Write a subclass of `OidcProviderSpec` in `providers.py` (issuer, extra settings, `validate_claims`, `map_claims`) and
add it to `OIDC_PROVIDERS` in `registry.py`. The settings (`IS_<KEY>_ENABLED`, `<KEY>_CLIENT_ID`, ...), the routes
(`/auth/oidc/<key>/`) and the entry in the `oidc_providers` list of the public instance configuration follow from the
spec. The god-mode form and the list on the authentication page come from one entry in `OIDC_PROVIDER_DEFINITIONS`
(`packages/constants/src/auth/oidc.ts`); the sign-in buttons of the web and space apps come from the server's list.
Mind what the claims can prove: take the identity from an immutable claim, and refuse tokens whose email is not
verified or whose tenant/organisation is not the expected one.

## Acknowledgements

The design was informed by the OpenID Connect work in the community forks
[paperplane](https://github.com/inomotech-foss/paperplane) and [Hangar](https://github.com/szymczag/hangar). No code
was copied from them.

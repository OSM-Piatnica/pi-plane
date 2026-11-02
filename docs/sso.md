# Single sign-on (OpenID Connect)

Pi-Plane signs people in through OpenID Connect (authorization code flow with PKCE, `state` and `nonce`). Providers are
described in `apps/api/plane/authentication/provider/oidc/`; everything else (sign-in and callback URLs, the instance
settings, the buttons on the sign-in screens, ID token validation) is shared.

| Provider           | Key           | Notes                                                                       |
| ------------------ | ------------- | --------------------------------------------------------------------------- |
| Microsoft Entra ID | `entra`       | One tenant only. People are bound by tenant id + object id.                 |
| Google             | `google-oidc` | Optionally one Workspace domain (`hd`). Replaces the former Google login.   |
| Any OIDC provider  | `oidc`        | By issuer URL (Keycloak, Okta, Authentik, ...). The email must be verified. |

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
bound by their Google account id.

> **Upgrading from the former Google login:** `IS_GOOGLE_ENABLED`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and
> `ENABLE_GOOGLE_SYNC` are no longer read, and `/auth/google/` is gone. Create the settings above (the same OAuth client
> works: add the new redirect URI to it). The old login left accounts that have no identity at the new provider, so
> people who used it are refused on their first sign-in (`OIDC_ACCOUNT_LINK_REQUIRED`) until you set
> `GOOGLE_OIDC_LINK_EXISTING_ACCOUNTS=1` for the time they sign in for the first time; see
> [How people are matched](#how-people-are-matched).

## Any OIDC provider

For Keycloak, Okta, Authentik and similar: register a client with the redirect URI
`<your Pi-Plane URL>/auth/oidc/oidc/callback/`, then set `IS_OIDC_ENABLED=1`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`
and `OIDC_ISSUER_URL` (the provider's `/.well-known/openid-configuration` is read from there), and optionally
`OIDC_DISPLAY_NAME`, the label of the sign-in button (default "Single sign-on"). The issuer URL must start with
`https://`; otherwise the provider counts as not configured and no button is shown. The provider must send
`email_verified: true`; a token without it is refused.

## How people are matched

In the settings below `<KEY>` is the provider key in capitals with `-` written as `_`: `ENTRA`, `GOOGLE_OIDC` or
`OIDC`. For Google that makes `GOOGLE_OIDC_LINK_EXISTING_ACCOUNTS`, `GOOGLE_OIDC_ENABLE_SIGNUP` and
`ENABLE_GOOGLE_OIDC_SYNC`.

1. By the identity at the provider (`Account.provider_account_id`). If that is known, that user signs in. The identity
   is the subject **together with the issuer** (for Entra, tenant id + object id), so a subject handed out by another
   issuer never matches.
2. Otherwise, if an account with that email address exists, the person is refused (`OIDC_ACCOUNT_LINK_REQUIRED`): an
   address alone never takes an account over, because anybody could have registered it with a password of their own
   before its owner first signed in. To migrate existing accounts, set `<KEY>_LINK_EXISTING_ACCOUNTS=1` for the time
   people sign in for the first time, then switch it off again. Linking binds the identity to the account **and
   replaces any password set on it**, so from then on only the provider opens it. An account already bound to a
   different identity of the provider is always refused (`OIDC_IDENTITY_MISMATCH`).
3. Otherwise a new user is created, if `<KEY>_ENABLE_SIGNUP` is `1` (or they have a workspace invite).

The user, the identity and the profile are created in one transaction, and a binding is never moved to another user.
`<KEY>_ENABLE_SIGNUP` is independent of `ENABLE_SIGNUP` (email sign-up): a corporate instance can keep email sign-up
closed and still create accounts for everyone in its tenant. Deactivated accounts and bots are refused as with every
other sign-in. With `ENABLE_<KEY>_SYNC=1` the name is refreshed from the provider at every sign-in. No token of the
provider is stored.

Entra: when the tenant sends the optional `xms_edov` claim (email domain verified), a value other than `true` or `1` (in any case) is refused.
Provider answers are limited to 1 MiB; the log names the stage of a refused sign-in and the provider's own error code and
description (never the request, which carries the secret and the code).

## Groups

Each provider can mirror the groups a person has at the provider as [user groups](user-groups.md) that are managed outside. The groups are read at every sign-in; when they cannot be read, nothing changes. Like the other settings they can be set in god mode or in the environment.

| Provider           | Settings                                                                                                                                                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Microsoft Entra ID | `ENTRA_SYNC_GROUPS=1`. All groups of the person, nested ones included, are read through Microsoft Graph with their own token; the sign-in then asks them for the permission `User.Read`.                                                                                 |
| Google             | `GOOGLE_OIDC_SYNC_GROUPS=1`, `GOOGLE_OIDC_GROUPS_ADMIN_EMAIL` and `GOOGLE_OIDC_GROUPS_SERVICE_ACCOUNT`. Needs a service account key (JSON) with domain-wide delegation of `https://www.googleapis.com/auth/admin.directory.group.readonly`, acting as a Workspace admin. |
| Any OIDC provider  | `OIDC_GROUPS_CLAIM`, the claim of the ID token that lists the groups (for example `groups`), and, if the provider only sends it for a certain scope, `OIDC_GROUPS_SCOPE`.                                                                                                |

**Which Entra data become groups.** With `ENTRA_SYNC_GROUPS=1` as the master switch, eight more switches (Authentication → Microsoft in god mode, or the environment) choose the kinds: `ENTRA_GROUPS_SECURITY`, `ENTRA_GROUPS_MICROSOFT_365` and `ENTRA_GROUPS_DISTRIBUTION` (all on by default, so every group of the person is mirrored as before), and `ENTRA_GROUPS_ADMIN_UNITS`, `ENTRA_GROUPS_DEPARTMENT`, `ENTRA_GROUPS_COMPANY`, `ENTRA_GROUPS_OFFICE` and `ENTRA_GROUPS_ORG_UNITS` (off by default). Administrative units are named `Administrative unit: <name>`, the person's department, company and office location attributes become one group per value (`Department: Sales`, `Company: Acme`, `Office: Warsaw`). People synced from on-premises Active Directory can also be grouped by their organizational unit: the OU path of their directory entry becomes nested groups (`Organizational unit: Poland` with `Sales` below it, up to 9 levels), the person is a member of the innermost one and of its parents through the nesting; cloud-only accounts have none. The sync owns the position of these groups (a hand-moved OU group is put back at the next sign-in) and never deletes groups. SharePoint's own site permission groups are not Entra objects and are not read (a Microsoft 365 group or an Entra group that has access to a site is). Reading administrative units needs the delegated Graph permission `AdministrativeUnit.Read.All` with admin consent in the tenant; if Graph refuses, the other kinds still work. Turning a kind off takes people out of its groups at their next sign-in.

The generic claim may be a list of names or one string of names separated by commas, with at most 500 entries. A path such as `/sales/poland` (Keycloak) is shown as `sales/poland`. A token without the claim changes nothing; a claim that is there but empty removes the person from the mirrored groups.

## Adding another provider

Write a subclass of `OidcProviderSpec` in `providers.py` (issuer, extra settings, `validate_claims`, `map_claims`) and
add it to `OIDC_PROVIDERS` in `registry.py`. The settings (`IS_<KEY>_ENABLED`, `<KEY>_CLIENT_ID`, ...), the routes
(`/auth/oidc/<key>/`) and the entry in the `oidc_providers` list of the public instance configuration follow from the
spec. In the front end the god-mode form comes from an entry in `OIDC_PROVIDER_DEFINITIONS`
(`packages/constants/src/auth/oidc.ts`), and a new key also has to be added to the `TOidcProviderKey` type
(`packages/types/src/instance/auth.ts`) and to the admin app's provider lists and titles (`apps/admin/hooks/oauth/`,
`apps/admin/components/common/header/core.ts`, `packages/constants/src/auth/core.ts`). The sign-in buttons of the web
and space apps come from the server's list.
Mind what the claims can prove: take the identity from an immutable claim, and refuse tokens whose email is not
verified or whose tenant/organisation is not the expected one.

## Acknowledgements

The design was informed by the OpenID Connect work in the community forks
[paperplane](https://github.com/inomotech-foss/paperplane) and [Hangar](https://github.com/szymczag/hangar). No code
was copied from them.

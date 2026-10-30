# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The OpenID Connect providers. To add one, subclass ``OidcProviderSpec`` and list it in ``registry.py``."""

import uuid

from plane.db.models import GroupSource

from . import groups
from .spec import OidcClaimsError, OidcConfigField, OidcIdentity, OidcProviderSpec


def _split_name(claims):
    first_name = claims.get("given_name") or ""
    last_name = claims.get("family_name") or ""
    full_name = claims.get("name") or ""
    if not (first_name or last_name) and full_name:
        first_name, _, last_name = full_name.partition(" ")
    return first_name, last_name, full_name


class EntraSpec(OidcProviderSpec):
    """Microsoft Entra ID (Azure AD), restricted to one tenant.

    A person is identified by tenant and object id (``tid:oid``): both are immutable, unlike the email address, which
    an administrator of the tenant can change. Tokens issued by any other tenant are refused.
    """

    def __init__(self):
        super().__init__(
            key="entra",
            name="Microsoft",
            icon="microsoft",
            # tid:oid already names the tenant
            scope_subject_to_issuer=False,
            group_source=GroupSource.ENTRA,
            fields=(
                OidcConfigField(
                    name="TENANT_ID",
                    label="Directory (tenant) ID",
                    required=True,
                    help="The GUID of your Microsoft Entra tenant. Only people of this tenant can sign in.",
                ),
                OidcConfigField(
                    name="SYNC_GROUPS",
                    label="Read groups at sign-in",
                    default="0",
                    kind="switch",
                    help=(
                        "Mirror what Entra says about each person as user groups that are managed outside. "
                        "Asks for the Microsoft Graph permission User.Read, which people grant at sign-in. "
                        "The kinds below choose what becomes a group."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_SECURITY",
                    label="Security groups",
                    default="1",
                    kind="switch",
                    help="Groups used to grant access, including mail-enabled security groups.",
                ),
                OidcConfigField(
                    name="GROUPS_MICROSOFT_365",
                    label="Microsoft 365 groups",
                    default="1",
                    kind="switch",
                    help="Groups that back Teams and SharePoint team sites.",
                ),
                OidcConfigField(
                    name="GROUPS_DISTRIBUTION",
                    label="Distribution lists",
                    default="1",
                    kind="switch",
                    help="Groups that only send mail to their members.",
                ),
                OidcConfigField(
                    name="GROUPS_ADMIN_UNITS",
                    label="Administrative units",
                    default="0",
                    kind="switch",
                    help=(
                        "The administrative units a person belongs to. Needs the Microsoft Graph delegated "
                        "permission AdministrativeUnit.Read.All with admin consent; without it no unit is mirrored."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_DEPARTMENT",
                    label="Department",
                    default="0",
                    kind="switch",
                    help=(
                        "One group per department, from the department in the person's Entra profile; "
                        "people without one are in none."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_COMPANY",
                    label="Company",
                    default="0",
                    kind="switch",
                    help=(
                        "One group per company, from the company name in the person's Entra profile; "
                        "people without one are in none."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_OFFICE",
                    label="Office location",
                    default="0",
                    kind="switch",
                    help=(
                        "One group per office, from the office location in the person's Entra profile; "
                        "people without one are in none."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_ORG_UNITS",
                    label="On-premises organizational unit",
                    default="0",
                    kind="switch",
                    help=(
                        "Nested groups of the Active Directory organizational units (OU) of the person's "
                        "on-premises account, such as Poland > Sales; the person is in the innermost one. Only for "
                        "people synced from on-premises Active Directory: blank for cloud-only accounts."
                    ),
                ),
            ),
        )

    def reads_groups(self, config):
        return str(config.get("SYNC_GROUPS")) == "1"

    def request_scopes(self, config):
        if not self.reads_groups(config):
            return self.scopes
        scopes = [self.scopes, groups.ENTRA_GROUPS_SCOPE]
        if groups.KIND_ADMIN_UNITS in groups.entra_kinds(config):
            scopes.append(groups.ENTRA_ADMIN_UNITS_SCOPE)
        return " ".join(scopes)

    def fetch_groups(self, *, access_token, email, claims, config):
        return groups.fetch_entra_groups(access_token, groups.entra_kinds(config))

    def _tenant(self, config):
        try:
            return str(uuid.UUID(str(config.get("TENANT_ID", "")).strip()))
        except ValueError:
            return None

    def is_configured(self, config):
        # "common", "organizations" and domain names are refused on purpose: the tenant is the trust anchor
        return super().is_configured(config) and self._tenant(config) is not None

    def issuer(self, config):
        return f"https://login.microsoftonline.com/{self._tenant(config)}/v2.0"

    def validate_claims(self, claims, config):
        if str(claims.get("tid", "")).lower() != self._tenant(config) or not claims.get("oid"):
            raise OidcClaimsError("OIDC_PROVIDER_ERROR")
        # Optional claim: when the tenant sends it, the email domain must be one the tenant has verified
        if "xms_edov" in claims and str(claims["xms_edov"]).lower() not in ("true", "1"):
            raise OidcClaimsError("OAUTH_PROVIDER_UNVERIFIED_EMAIL")

    def map_claims(self, claims):
        # `email` is optional in Entra tokens; the user principal name is the sign-in address of the tenant
        email = claims.get("email") or claims.get("preferred_username") or ""
        first_name, last_name, full_name = _split_name(claims)
        return OidcIdentity(
            subject=f"{str(claims['tid']).lower()}:{str(claims['oid']).lower()}",
            email=email,
            first_name=first_name,
            last_name=last_name,
            display_name=full_name,
        )


class GoogleSpec(OidcProviderSpec):
    """Google accounts, optionally restricted to one Google Workspace domain.

    Replaces the former Google OAuth login (``GOOGLE_*`` settings). People are bound by their Google account id
    (``sub``); with a hosted domain set, tokens of accounts outside that Workspace are refused.
    """

    def __init__(self):
        super().__init__(
            key="google-oidc",
            name="Google",
            icon="google",
            group_source=GroupSource.GOOGLE,
            fields=(
                OidcConfigField(
                    name="HOSTED_DOMAIN",
                    label="Google Workspace domain",
                    help="Optional. Only accounts of this Workspace domain (the hd claim) can sign in.",
                ),
                OidcConfigField(
                    name="SYNC_GROUPS",
                    label="Read groups at sign-in",
                    default="0",
                    help=(
                        "Set to 1 to mirror each person's Google Workspace groups as user groups that are managed "
                        "outside. Needs the service account and admin e-mail below."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_ADMIN_EMAIL",
                    label="Workspace admin to read groups as",
                    help="A Workspace admin the service account acts as (domain-wide delegation).",
                ),
                OidcConfigField(
                    name="GROUPS_SERVICE_ACCOUNT",
                    label="Service account key (JSON)",
                    secret=True,
                    help=(
                        "A service account key with domain-wide delegation of the scope "
                        "https://www.googleapis.com/auth/admin.directory.group.readonly."
                    ),
                ),
            ),
        )

    def reads_groups(self, config):
        return (
            str(config.get("SYNC_GROUPS")) == "1"
            and bool(config.get("GROUPS_ADMIN_EMAIL"))
            and bool(config.get("GROUPS_SERVICE_ACCOUNT"))
        )

    def fetch_groups(self, *, access_token, email, claims, config):
        return groups.fetch_google_groups(email, config.get("GROUPS_SERVICE_ACCOUNT"), config.get("GROUPS_ADMIN_EMAIL"))

    def issuer(self, config):
        return "https://accounts.google.com"

    def validate_claims(self, claims, config):
        # Fail closed: an absent claim counts as unverified (GHSA-7j95-vh8g-f365)
        if claims.get("email_verified") is not True:
            raise OidcClaimsError("OAUTH_PROVIDER_UNVERIFIED_EMAIL")
        domain = str(config.get("HOSTED_DOMAIN") or "").strip().lower().lstrip("@")
        if domain and str(claims.get("hd", "")).lower() != domain:
            raise OidcClaimsError("OIDC_EMAIL_DOMAIN_NOT_ALLOWED")

    def map_claims(self, claims):
        first_name, last_name, full_name = _split_name(claims)
        return OidcIdentity(
            subject=str(claims["sub"]),
            email=claims.get("email") or "",
            first_name=first_name,
            last_name=last_name,
            display_name=full_name,
        )


class GenericOidcSpec(OidcProviderSpec):
    """Any other OpenID Connect provider (Keycloak, Okta, Authentik, Google Workspace, ...), by its issuer URL."""

    def __init__(self):
        super().__init__(
            key="oidc",
            name="Single sign-on",
            icon="key",
            group_source=GroupSource.OIDC,
            fields=(
                OidcConfigField(
                    name="ISSUER_URL",
                    label="Issuer URL",
                    required=True,
                    help="The issuer of the provider; its /.well-known/openid-configuration is read from here.",
                ),
                OidcConfigField(
                    name="DISPLAY_NAME",
                    label="Button label",
                    default="Single sign-on",
                    help="How the sign-in button is named.",
                ),
                OidcConfigField(
                    name="GROUPS_CLAIM",
                    label="Groups claim",
                    help=(
                        "Optional. The claim of the ID token that lists the person's groups (for example groups). "
                        "When set, they are mirrored as user groups that are managed outside."
                    ),
                ),
                OidcConfigField(
                    name="GROUPS_SCOPE",
                    label="Scope that adds the groups claim",
                    help=(
                        "Optional. Some providers only put the claim in the token "
                        "when this scope (for example groups) is asked for."
                    ),
                ),
            ),
        )

    def reads_groups(self, config):
        return bool(str(config.get("GROUPS_CLAIM") or "").strip())

    def request_scopes(self, config):
        extra = str(config.get("GROUPS_SCOPE") or "").strip()
        return f"{self.scopes} {extra}" if extra and self.reads_groups(config) else self.scopes

    def fetch_groups(self, *, access_token, email, claims, config):
        return groups.groups_from_claim(claims, config.get("GROUPS_CLAIM"))

    def is_configured(self, config):
        return super().is_configured(config) and str(config.get("ISSUER_URL", "")).startswith("https://")

    def display_name(self, config):
        return config.get("DISPLAY_NAME") or self.name

    def issuer(self, config):
        return str(config["ISSUER_URL"]).strip()

    def validate_claims(self, claims, config):
        # Fail closed: an absent claim counts as unverified (GHSA-7j95-vh8g-f365)
        if claims.get("email_verified") is not True:
            raise OidcClaimsError("OAUTH_PROVIDER_UNVERIFIED_EMAIL")

    def map_claims(self, claims):
        first_name, last_name, full_name = _split_name(claims)
        return OidcIdentity(
            subject=str(claims["sub"]),
            email=claims.get("email") or "",
            first_name=first_name,
            last_name=last_name,
            display_name=full_name,
        )

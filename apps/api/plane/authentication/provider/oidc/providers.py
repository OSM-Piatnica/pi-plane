# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The OpenID Connect providers. To add one, subclass ``OidcProviderSpec`` and list it in ``registry.py``."""

import uuid

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
            fields=(
                OidcConfigField(
                    name="TENANT_ID",
                    label="Directory (tenant) ID",
                    required=True,
                    help="The GUID of your Microsoft Entra tenant. Only people of this tenant can sign in.",
                ),
            ),
        )

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


class GenericOidcSpec(OidcProviderSpec):
    """Any other OpenID Connect provider (Keycloak, Okta, Authentik, Google Workspace, ...), by its issuer URL."""

    def __init__(self):
        super().__init__(
            key="oidc",
            name="Single sign-on",
            icon="key",
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
            ),
        )

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

# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""What describes a single sign-on provider that speaks OpenID Connect.

A provider is a small ``OidcProviderSpec`` subclass (see ``providers.py``): who its issuer is, which extra settings it
needs and how to read the identity out of the claims of its ID token. The rest is shared: see ``registry.py``.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OidcConfigField:
    """An extra instance setting of a provider, stored as ``<KEY>_<name>``."""

    name: str
    label: str
    required: bool = False
    secret: bool = False
    default: str = ""
    help: str = ""


@dataclass(frozen=True)
class OidcIdentity:
    """Who signed in, as the provider says it."""

    # Stable, unique per person at the provider (never the email: those get reassigned)
    subject: str
    email: str
    first_name: str = ""
    last_name: str = ""
    display_name: str = ""


class OidcClaimsError(Exception):
    """The ID token is valid but does not describe someone we accept (wrong tenant, no email, ...)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OidcProviderSpec:
    """What is specific to one OpenID Connect provider."""

    key: str  # url slug, Account.provider and prefix of the settings: "entra" -> ENTRA_CLIENT_ID
    name: str  # the label of the button
    icon: str  # which icon the apps draw on the button
    scopes: str = "openid profile email"
    fields: tuple = field(default_factory=tuple)  # extra OidcConfigField settings

    # ---- settings -------------------------------------------------------------------------------------------------
    @property
    def prefix(self):
        return self.key.upper().replace("-", "_")

    def config_key(self, name):
        return f"{self.prefix}_{name}"

    def load_config(self):
        from plane.license.utils.instance_value import get_configuration_value

        """The provider's settings as a dict, read from the instance configuration (or the environment)."""
        names = ["CLIENT_ID", "CLIENT_SECRET", "ENABLE_SIGNUP", "ALLOWED_EMAIL_DOMAINS", *[f.name for f in self.fields]]
        defaults = {"ENABLE_SIGNUP": "1", **{f.name: f.default for f in self.fields}}
        values = get_configuration_value(
            [
                {
                    "key": self.config_key(name),
                    "default": os.environ.get(self.config_key(name), defaults.get(name, "")),
                }
                for name in names
            ]
        )
        config = dict(zip(names, values))
        (sync,) = get_configuration_value(
            [{"key": f"ENABLE_{self.prefix}_SYNC", "default": os.environ.get(f"ENABLE_{self.prefix}_SYNC", "0")}]
        )
        config["SYNC"] = sync
        return config

    def is_configured(self, config):
        required = ["CLIENT_ID", "CLIENT_SECRET", *[f.name for f in self.fields if f.required]]
        return all(config.get(name) for name in required)

    def display_name(self, config):
        return self.name

    # ---- protocol -------------------------------------------------------------------------------------------------
    def issuer(self, config):
        """The issuer URL, which is also where its discovery document lives."""
        raise NotImplementedError

    def validate_claims(self, claims, config):
        """Extra checks of the validated ID token; raise OidcClaimsError(code) to refuse the person."""

    def map_claims(self, claims):
        """The OidcIdentity of the claims."""
        raise NotImplementedError

    def config_variables(self):
        """The instance settings of the provider, in the format of ``instance_config_variables``."""
        category = self.prefix
        variables = [
            {"key": f"IS_{category}_ENABLED", "value": os.environ.get(f"IS_{category}_ENABLED", "0")},
            {"key": self.config_key("CLIENT_ID"), "value": os.environ.get(self.config_key("CLIENT_ID"))},
            {
                "key": self.config_key("CLIENT_SECRET"),
                "value": os.environ.get(self.config_key("CLIENT_SECRET")),
                "is_encrypted": True,
            },
            {
                "key": self.config_key("ENABLE_SIGNUP"),
                "value": os.environ.get(self.config_key("ENABLE_SIGNUP"), "1"),
            },
            {
                "key": self.config_key("ALLOWED_EMAIL_DOMAINS"),
                "value": os.environ.get(self.config_key("ALLOWED_EMAIL_DOMAINS"), ""),
            },
            {"key": f"ENABLE_{category}_SYNC", "value": os.environ.get(f"ENABLE_{category}_SYNC", "0")},
        ]
        for extra in self.fields:
            variables.append(
                {
                    "key": self.config_key(extra.name),
                    "value": os.environ.get(self.config_key(extra.name), extra.default) or None,
                    "is_encrypted": extra.secret,
                }
            )
        return [{"is_encrypted": False, **variable, "category": category} for variable in variables]

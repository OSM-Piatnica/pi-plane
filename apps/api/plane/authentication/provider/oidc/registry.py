# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The single sign-on providers of the instance.

Adding a provider is a spec in ``providers.py`` plus a line in ``OIDC_PROVIDERS`` below. Everything else is driven by
this registry: the sign-in and callback views, the instance settings (``IS_<KEY>_ENABLED``, ``<KEY>_CLIENT_ID``, ...),
the list of buttons the apps show and the ID token validation.
"""

import os

from .providers import EntraSpec, GenericOidcSpec

OIDC_PROVIDERS = {spec.key: spec for spec in (EntraSpec(), GenericOidcSpec())}


def get_provider_spec(key):
    return OIDC_PROVIDERS.get(key)


def oidc_config_variables():
    """The instance settings of every provider (see utils.instance_config_variables)."""
    return [variable for spec in OIDC_PROVIDERS.values() for variable in spec.config_variables()]


def enabled_oidc_providers():
    """The providers that are switched on and fully configured, as the buttons of the sign-in screens."""
    from plane.license.utils.instance_value import get_configuration_value

    flags = get_configuration_value(
        [
            {"key": f"IS_{spec.prefix}_ENABLED", "default": os.environ.get(f"IS_{spec.prefix}_ENABLED", "0")}
            for spec in OIDC_PROVIDERS.values()
        ]
    )
    providers = []
    for spec, flag in zip(OIDC_PROVIDERS.values(), flags):
        if flag != "1":
            continue
        config = spec.load_config()
        if spec.is_configured(config):
            providers.append({"key": spec.key, "name": spec.display_name(config), "icon": spec.icon})
    return providers

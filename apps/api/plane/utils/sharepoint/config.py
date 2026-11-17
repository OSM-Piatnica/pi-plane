# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The SharePoint settings of the instance, as the administrator saved them in the admin app (Integrations → SharePoint).

They are instance configuration rows of the category ``SHAREPOINT``; the client secret is stored encrypted. Until a
value is saved the environment variable of the same name applies, as for every other instance setting.
"""

import os
from dataclasses import dataclass, field

from plane.utils.file_size_limit import parse_whole_number

from .client import SharePointClient, validate_client_id, validate_tenant_id
from .errors import SharePointConfigurationError, SharePointInputError

ENABLED_KEY = "IS_SHAREPOINT_ENABLED"
TENANT_ID_KEY = "SHAREPOINT_TENANT_ID"
CLIENT_ID_KEY = "SHAREPOINT_CLIENT_ID"
CLIENT_SECRET_KEY = "SHAREPOINT_CLIENT_SECRET"
MAX_FILE_SIZE_KEY = "SHAREPOINT_MAX_FILE_SIZE"

MB = 1024 * 1024
# The largest file Pi-Plane lets a person put in SharePoint, unless the administrator says otherwise. It has nothing
# to do with FILE_SIZE_LIMIT: these files do not pass through Pi-Plane's own storage.
DEFAULT_MAX_FILE_SIZE = 500 * MB
MIN_MAX_FILE_SIZE = MB
# What SharePoint Online itself takes for one file
MAX_MAX_FILE_SIZE = 250 * 1024 * MB


@dataclass(frozen=True)
class SharePointSettings:
    enabled: bool
    tenant_id: str
    client_id: str
    # Kept out of repr, so that a settings object in a log or a traceback does not show it
    client_secret: str = field(repr=False)
    max_file_size: int = DEFAULT_MAX_FILE_SIZE

    @property
    def has_credentials(self) -> bool:
        return bool(self.tenant_id and self.client_id and self.client_secret)

    @property
    def is_usable(self) -> bool:
        """Switched on and complete: what the apps are told as ``is_sharepoint_enabled``."""
        return self.enabled and self.has_credentials


def parse_max_file_size(raw) -> int | None:
    """The size in bytes when `raw` is a whole number within the allowed range, else None."""
    size = parse_whole_number(raw)
    if size is None or size < MIN_MAX_FILE_SIZE or size > MAX_MAX_FILE_SIZE:
        return None
    return size


def get_sharepoint_settings() -> SharePointSettings:
    # Imported here: plane.license models import this package's siblings at start-up
    from plane.license.utils.instance_value import get_configuration_value

    enabled, tenant_id, client_id, client_secret, max_file_size = get_configuration_value(
        [
            {"key": ENABLED_KEY, "default": os.environ.get(ENABLED_KEY, "0")},
            {"key": TENANT_ID_KEY, "default": os.environ.get(TENANT_ID_KEY, "")},
            {"key": CLIENT_ID_KEY, "default": os.environ.get(CLIENT_ID_KEY, "")},
            {"key": CLIENT_SECRET_KEY, "default": os.environ.get(CLIENT_SECRET_KEY, "")},
            {"key": MAX_FILE_SIZE_KEY, "default": os.environ.get(MAX_FILE_SIZE_KEY, "")},
        ]
    )
    return SharePointSettings(
        enabled=str(enabled or "").strip() == "1",
        tenant_id=str(tenant_id or "").strip(),
        client_id=str(client_id or "").strip(),
        client_secret=str(client_secret or "").strip(),
        max_file_size=parse_max_file_size(max_file_size) or DEFAULT_MAX_FILE_SIZE,
    )


def is_sharepoint_enabled() -> bool:
    return get_sharepoint_settings().is_usable


def get_sharepoint_max_file_size() -> int:
    return get_sharepoint_settings().max_file_size


def get_sharepoint_client(*, require_enabled: bool = True, **client_options) -> SharePointClient:
    """
    A client with the saved credentials. Raises SharePointConfigurationError when they are not complete or, unless
    ``require_enabled`` is False (the connection test, which runs before the switch is turned on), when the
    integration is switched off. A saved value that cannot be used raises SharePointInputError.
    """
    settings = get_sharepoint_settings()
    if not settings.has_credentials:
        raise SharePointConfigurationError(
            "SharePoint is not configured: save the tenant ID, the client ID and the client secret first."
        )
    if require_enabled and not settings.enabled:
        raise SharePointConfigurationError("SharePoint is switched off on this instance.", code="disabled")
    return SharePointClient(settings.tenant_id, settings.client_id, settings.client_secret, **client_options)


def configuration_error(data) -> str | None:
    """
    What is wrong with the SharePoint values of a configuration that is about to be saved, or None. Only the keys
    that are there are looked at, and an empty value is always fine (it clears the setting).
    """
    checks = ((TENANT_ID_KEY, validate_tenant_id), (CLIENT_ID_KEY, validate_client_id))
    for key, validate in checks:
        value = str(data.get(key) or "").strip() if key in data else ""
        if value:
            try:
                validate(value)
            except SharePointInputError as error:
                return error.message
    raw_size = str(data.get(MAX_FILE_SIZE_KEY) or "").strip() if MAX_FILE_SIZE_KEY in data else ""
    if raw_size and parse_max_file_size(raw_size) is None:
        return (
            f"The largest file for SharePoint must be between {MIN_MAX_FILE_SIZE // MB} MB "
            f"and {MAX_MAX_FILE_SIZE // MB} MB."
        )
    if ENABLED_KEY in data and str(data.get(ENABLED_KEY) or "").strip() not in ("", "0", "1"):
        return "The SharePoint switch must be 0 or 1."
    return None

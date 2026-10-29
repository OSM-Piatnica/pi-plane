# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Whether the public sharing site (Space) is available.

Two things decide it. The deployment: an installation may leave Space out altogether (``ENABLE_SPACE=0`` in the
environment of the API), in which case there is nothing for the admin to switch on. And the instance admin, who can turn
Space off in the admin app (``IS_SPACE_ENABLED``) while it is deployed; this is the default. Both have to allow it.

While Space is off nothing is shared on the web: the public API answers 404, boards cannot be published, and the
apps hide the sharing options. What was published stays stored, so turning Space on again brings the boards back.
"""

import os

from plane.license.utils.instance_value import get_configuration_value

SPACE_ENABLED_KEY = "IS_SPACE_ENABLED"
_OFF = {"0", "false", "no", "off"}


def is_space_deployed() -> bool:
    """False when the installation leaves Space out (the deployment's ``ENABLE_SPACE`` is off)."""
    return os.environ.get("ENABLE_SPACE", "1").strip().lower() not in _OFF


def is_space_enabled() -> bool:
    """Whether web sharing works: Space is part of the deployment and the admin has not turned it off."""
    if not is_space_deployed():
        return False
    (value,) = get_configuration_value([{"key": SPACE_ENABLED_KEY, "default": os.environ.get(SPACE_ENABLED_KEY, "1")}])
    return str(value).strip().lower() not in _OFF

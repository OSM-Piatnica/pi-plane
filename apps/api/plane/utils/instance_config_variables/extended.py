# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from plane.authentication.provider.oidc.registry import oidc_config_variables

extended_config_variables = [*oidc_config_variables()]

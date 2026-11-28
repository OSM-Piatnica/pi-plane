# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace feature switches.

A workspace admin can switch whole parts of the product on or off for a workspace. The switch is stored per workspace
and key in ``WorkspaceFeature``; a missing row means "off".

``WORKSPACE_FEATURES`` is the list of known keys. The value says whether the feature is built ("available"): a key
that is not available cannot be switched on and is never reported as enabled, whatever the table holds. The web app
keeps the same list in ``packages/constants/src/workspace-features.ts``; a unit test of the web app compares the two.
See ``docs/workspace-features.md``.
"""

# key -> is the feature built
WORKSPACE_FEATURES = {
    "lite": False,
    "approvals": False,
    "initiatives": True,
    "wiki": False,
    "raci": True,
}


def is_known_workspace_feature(key):
    return key in WORKSPACE_FEATURES


def is_available_workspace_feature(key):
    return WORKSPACE_FEATURES.get(key, False) is True


def available_workspace_feature_keys():
    """The keys that can be switched, in the order of ``WORKSPACE_FEATURES``."""
    return [key for key, available in WORKSPACE_FEATURES.items() if available is True]


def enabled_workspace_feature_keys(workspace):
    """The available features that are switched on for the workspace, in the order of ``WORKSPACE_FEATURES``.

    Runs no query while no feature is available. Reads ``workspace.workspace_features.all()``, so a caller that
    serializes many workspaces can prefetch ``workspace_features``.
    """
    available = available_workspace_feature_keys()
    if not available:
        return []
    enabled = {feature.key for feature in workspace.workspace_features.all() if feature.is_enabled}
    return [key for key in available if key in enabled]


def is_workspace_feature_enabled(workspace, key):
    """Whether one available feature is switched on for the workspace. One query, or none while it is not built."""
    if not is_available_workspace_feature(key):
        return False
    from plane.db.models import WorkspaceFeature

    return WorkspaceFeature.objects.filter(workspace=workspace, key=key, is_enabled=True).exists()


def workspace_feature_states(workspace):
    """``{key: is_enabled}`` for every available feature."""
    enabled = set(enabled_workspace_feature_keys(workspace))
    return {key: key in enabled for key in available_workspace_feature_keys()}


def prefetch_workspace_features(queryset):
    """Prefetches the switches of every workspace of a list that serializes ``enabled_features``.

    Without it each workspace costs one query. While no feature is available nothing is read, so nothing is
    prefetched either.
    """
    if not available_workspace_feature_keys():
        return queryset
    return queryset.prefetch_related("workspace_features")


def set_workspace_feature(workspace, key, is_enabled):
    """Stores one switch. Two admins switching a feature that has no row yet can both try to create it; the one that
    loses the race to the unique constraint updates the row the other created instead of failing."""
    from django.db import IntegrityError, transaction

    from plane.db.models import WorkspaceFeature

    try:
        with transaction.atomic():
            WorkspaceFeature.objects.update_or_create(workspace=workspace, key=key, defaults={"is_enabled": is_enabled})
    except IntegrityError:
        WorkspaceFeature.objects.filter(workspace=workspace, key=key).update(is_enabled=is_enabled)

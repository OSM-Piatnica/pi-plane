# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""What a new user takes over from their workspace.

The first day of the week needs nothing here: a profile without a choice of its own follows the project, then the
workspace, wherever the page is shown. A timezone is a plain value on the user, so it is copied once, when the person
finishes onboarding and so has a workspace: from the one they last opened, else the first they joined.
"""

from plane.db.models import Workspace

DEFAULT_USER_TIMEZONE = "UTC"


def inherit_workspace_timezone(user, profile):
    """Give a user who still has the default timezone the timezone of their workspace; return whether it changed."""
    workspaces = Workspace.objects.filter(workspace_member__member=user, workspace_member__is_active=True)
    workspace = None
    if profile.last_workspace_id:
        workspace = workspaces.filter(pk=profile.last_workspace_id).first()
    if workspace is None:
        workspace = workspaces.order_by("workspace_member__created_at").first()
    if workspace is None or workspace.timezone == DEFAULT_USER_TIMEZONE:
        return False

    # Checked in the database, not on `user`, which may be a stale copy of a timezone the person has since chosen
    changed = (
        type(user)
        .objects.filter(pk=user.pk, user_timezone=DEFAULT_USER_TIMEZONE)
        .update(user_timezone=workspace.timezone)
    )
    if changed:
        user.user_timezone = workspace.timezone
    return bool(changed)

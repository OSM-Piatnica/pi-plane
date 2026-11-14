# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from plane.utils.auto_join_workspace import join_auto_join_workspace

from .workspace_project_join import process_workspace_project_invitations


def post_user_auth_workflow(user, is_signup, request):
    process_workspace_project_invitations(user=user)
    # After the invites: whoever accepted one to the company workspace is a member already and keeps that role
    join_auto_join_workspace(user)

# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Focus: next work items, what holds them up, who waits and what to approve, for the person who asks (D9)."""

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Project, Workspace
from plane.utils.focus import clamp_limit, focus


class WorkspaceFocusEndpoint(BaseAPIView):
    """GET answers the focus lists of the person who asks (``plane.utils.focus``), across their projects:

        {"today": "2027-06-07", "department_ids": ["<id>"], "raci_enabled": true,
         "next": {"count": 12, "items": [{..., "startable": true}]},
         "blocked": {"count": 2, "items": [{..., "blocked_by": [{"relation_type": "blocked_by", "holds": "start",
                                                                  "issue": {...}}],
                                            "hidden_blocked_by_count": 0}]},
         "waiting_on_us": {"count": 1, "items": [{..., "waiting_on": [...], "hidden_waiting_on_count": 0}]},
         "to_approve": {"count": 3, "items": [{..., "approver_department_ids": ["<id>"]}]},
         "overdue": {"count": 1, "items": [{..., "overdue": ["due", "finish"]}]}}

    Every work item has ``id``, ``name``, ``sequence_id``, ``project_id``, ``project_identifier``, ``state_id``,
    ``state_group``, ``priority``, ``start_date``, ``finish_date``, ``target_date``, ``assignee_ids`` and
    ``group_assignee_ids``. ``?limit=`` sets how many work items each list shows (50 by default, at most 200);
    ``count`` is always the full number.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        return Response(
            focus(request.user, workspace, limit=clamp_limit(request.GET.get("limit"))), status=status.HTTP_200_OK
        )


class ProjectFocusEndpoint(BaseAPIView):
    """The focus lists of ``WorkspaceFocusEndpoint`` for the work items of one project."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        project = Project.objects.select_related("workspace").get(pk=project_id, workspace__slug=slug)
        return Response(
            focus(request.user, project.workspace, project_id=project.id, limit=clamp_limit(request.GET.get("limit"))),
            status=status.HTTP_200_OK,
        )

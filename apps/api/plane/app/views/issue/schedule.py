# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Schedule analysis of a project: critical path, float and "needed by" dates, for the timeline."""

# Python imports
import uuid

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Project
from plane.utils.schedule_scope import analyse_scope


class ProjectScheduleAnalysisEndpoint(BaseAPIView):
    """GET answers the critical path analysis of the project's dated work items (``plane.utils.schedule_analysis``):

        {"project_start": "2027-06-07", "project_end": "2027-07-09",
         "items": {"<id>": {"earliest_start": ..., "earliest_finish": ..., "latest_start": ..., "latest_finish": ...,
                            "total_float": 4, "is_critical": false, "is_fixed": false, "needed_by": "2027-07-02"}},
         "critical_ids": ["<id>"], "cycles": [["<id>", "<id>"]],
         "undated_count": 3, "undated_linked_ids": ["<id>"],
         "weekend_days": [0, 6], "analysed_count": 12, "max_items": 2000, "truncated": false}

    ``?module=<id>`` or ``?cycle=<id>`` analyses only the work items of that module or cycle; the end of the analysis is
    then the latest finish among those.

    Archived, deleted and draft work items do not take part. A guest who only sees their own work items gets the
    analysis of those alone, like in work item lists. The analysis is computed on every request; nothing is cached.
    At most ``max_items`` dated work items are analysed (the earliest by start date), ``truncated`` says when there
    were more.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        ids = {}
        for param in ("module", "cycle"):
            raw = request.GET.get(param)
            if not raw:
                continue
            try:
                ids[f"{param}_id"] = uuid.UUID(raw)
            except ValueError:
                return Response({"error": f"{param} must be an id"}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        return Response(analyse_scope(request.user, slug, project, **ids), status=status.HTTP_200_OK)

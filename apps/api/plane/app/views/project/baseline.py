# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Baselines of a project: saved plans the timeline compares the current dates with."""

# Python imports
import uuid

# Django imports
from django.shortcuts import get_object_or_404

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import BaselineItem, Issue, Project, ProjectBaseline, ProjectMember
from plane.db.models.baseline import (
    MAX_BASELINE_DESCRIPTION_LENGTH,
    MAX_BASELINE_NAME_LENGTH,
    MAX_BASELINES_PER_PROJECT,
)
from plane.utils.baselines import BaselineLimitReached, capture_baseline, compute_variance, set_active_baseline
from plane.utils.weekend_days import default_weekend_days

ITEM_DATE_FIELDS = ("start_date", "finish_date", "target_date")


def is_restricted_guest(user, project):
    """A guest of a project that does not show guests everything sees only the work items they created."""
    return (
        not project.guest_view_all_features
        and ProjectMember.objects.filter(
            project_id=project.id, member=user, role=ROLE.GUEST.value, is_active=True
        ).exists()
    )


def serialize_baseline(baseline, with_count=True):
    return {
        "id": str(baseline.id),
        "name": baseline.name,
        "description": baseline.description,
        "is_active": baseline.is_active,
        "item_count": baseline.item_count if with_count else None,
        "created_at": baseline.created_at,
        "created_by": str(baseline.created_by_id) if baseline.created_by_id else None,
        "project": str(baseline.project_id),
    }


def clean_text(data, field, max_length, required):
    """The trimmed text of a field of the request, and an error message when it cannot be taken."""
    value = data.get(field)
    if value is None:
        value = ""
    if not isinstance(value, str):
        return None, f"{field} must be text"
    value = value.strip()
    if required and not value:
        return None, f"{field} is required"
    if len(value) > max_length:
        return None, f"{field} must not be longer than {max_length} characters"
    return value, None


class ProjectBaselinesEndpoint(BaseAPIView):
    """The baselines of a project, newest first.

    GET answers ``{"baselines": [...], "max_baselines": 20}``. POST ``{"name": ..., "description": ...}`` saves the
    current plan as a new baseline (``plane.utils.baselines.capture_baseline``), which becomes the active one.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        # the number of dated work items of the project is not for a guest who sees only their own
        with_count = not is_restricted_guest(request.user, project)
        baselines = ProjectBaseline.objects.filter(workspace__slug=slug, project_id=project_id)
        return Response(
            {
                "baselines": [serialize_baseline(baseline, with_count) for baseline in baselines],
                "max_baselines": MAX_BASELINES_PER_PROJECT,
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        name, error = clean_text(request.data, "name", MAX_BASELINE_NAME_LENGTH, required=True)
        if error is None:
            description, error = clean_text(
                request.data, "description", MAX_BASELINE_DESCRIPTION_LENGTH, required=False
            )
        if error is not None:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        try:
            baseline = capture_baseline(project.id, name, description, request.user.id)
        except BaselineLimitReached:
            return Response(
                {
                    "error": f"A project keeps at most {MAX_BASELINES_PER_PROJECT} baselines. Delete one first.",
                    "code": "baseline_limit_reached",
                    "max_baselines": MAX_BASELINES_PER_PROJECT,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serialize_baseline(baseline), status=status.HTTP_201_CREATED)


class ProjectBaselineDetailEndpoint(BaseAPIView):
    """One baseline. GET answers it with its ``items``; PATCH renames it, changes its description or makes it the
    active one (``is_active``); DELETE removes it. Deleting the active baseline leaves the project without one."""

    def get_baseline(self, slug, project_id, pk):
        return get_object_or_404(ProjectBaseline, pk=pk, workspace__slug=slug, project_id=project_id)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, pk):
        baseline = self.get_baseline(slug, project_id, pk)
        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        restricted = is_restricted_guest(request.user, project)
        items = BaselineItem.objects.filter(baseline_id=baseline.id, issue__deleted_at__isnull=True)
        if restricted:
            items = items.filter(issue__created_by=request.user)
        payload = serialize_baseline(baseline, with_count=not restricted)
        payload["items"] = [
            {
                "issue": str(issue_id),
                "start_date": start_date,
                "finish_date": finish_date,
                "target_date": target_date,
                "state_group": state_group,
                "completed_at": completed_at,
            }
            for issue_id, start_date, finish_date, target_date, state_group, completed_at in items.values_list(
                "issue_id", *ITEM_DATE_FIELDS, "state_group", "completed_at"
            )
        ]
        return Response(payload, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def patch(self, request, slug, project_id, pk):
        baseline = self.get_baseline(slug, project_id, pk)
        update_fields = []
        for field, max_length, required in (
            ("name", MAX_BASELINE_NAME_LENGTH, True),
            ("description", MAX_BASELINE_DESCRIPTION_LENGTH, False),
        ):
            if field not in request.data:
                continue
            value, error = clean_text(request.data, field, max_length, required)
            if error is not None:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
            setattr(baseline, field, value)
            update_fields.append(field)

        is_active = request.data.get("is_active")
        if is_active is not None and not isinstance(is_active, bool):
            return Response({"error": "is_active must be true or false"}, status=status.HTTP_400_BAD_REQUEST)

        if update_fields:
            baseline.updated_by = request.user
            baseline.save(update_fields=[*update_fields, "updated_at", "updated_by"], disable_auto_set_user=True)
        if is_active is not None and is_active != baseline.is_active:
            set_active_baseline(baseline, is_active)
        return Response(serialize_baseline(baseline), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, pk):
        baseline = self.get_baseline(slug, project_id, pk)
        # soft delete; the items follow in the background and are never read through a deleted baseline
        baseline.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectBaselineVarianceEndpoint(BaseAPIView):
    """GET compares the current dates of the project's work items with a baseline, for the timeline:

        {"baseline": {"id": ..., "name": ..., "is_active": true, ...},
         "items": {"<work item id>": {"in_baseline": true,
                                      "baseline_start_date": "2027-06-07", "start_date": "2027-06-09",
                                      "start_date_variance": 2,
                                      "baseline_finish_date": ..., "finish_date": ..., "finish_date_variance": 3,
                                      "baseline_target_date": ..., "target_date": ...}},
         "summary": {"baseline_end": "2027-07-02", "current_end": "2027-07-07", "end_variance": 3},
         "weekend_days": [0, 6]}

    The due date (``target_date``) is a deadline: the saved and the current one are answered, but it has no variance.
    The active baseline is used unless ``?baseline=<id>`` names another one; without any, ``baseline`` is null and
    ``items`` is empty. Variances count working days of the project, positive when the date is later than planned
    (``plane.utils.baselines``). A work item created after the baseline, or without dates then, has
    ``in_baseline: false`` and no baseline dates. Work items deleted or archived since are left out.
    ``?module=<id>`` or ``?cycle=<id>`` limits the answer to the work items of that module or cycle.

    A guest who only sees their own work items gets those alone, like in work item lists.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        params = {}
        for param in ("baseline", "module", "cycle"):
            raw = request.GET.get(param)
            if not raw:
                continue
            try:
                params[param] = uuid.UUID(raw)
            except ValueError:
                return Response({"error": f"{param} must be an id"}, status=status.HTTP_400_BAD_REQUEST)

        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        weekend_days = default_weekend_days() if project.weekend_days is None else project.weekend_days
        baselines = ProjectBaseline.objects.filter(workspace__slug=slug, project_id=project_id)
        if "baseline" in params:
            baseline = get_object_or_404(baselines, pk=params["baseline"])
        else:
            baseline = baselines.filter(is_active=True).first()
        if baseline is None:
            return Response(
                {
                    "baseline": None,
                    "items": {},
                    "summary": {"baseline_end": None, "current_end": None, "end_variance": None},
                    "weekend_days": weekend_days,
                },
                status=status.HTTP_200_OK,
            )

        restricted = is_restricted_guest(request.user, project)
        issues = Issue.issue_objects.filter(workspace__slug=slug, project_id=project_id)
        if "module" in params:
            issues = issues.filter(issue_module__module_id=params["module"], issue_module__deleted_at__isnull=True)
        if "cycle" in params:
            issues = issues.filter(issue_cycle__cycle_id=params["cycle"], issue_cycle__deleted_at__isnull=True)
        if restricted:
            issues = issues.filter(created_by=request.user)

        # two queries, whatever the size of the project
        baseline_items = {
            issue_id: dict(zip(ITEM_DATE_FIELDS, dates))
            for issue_id, *dates in BaselineItem.objects.filter(baseline_id=baseline.id).values_list(
                "issue_id", *ITEM_DATE_FIELDS
            )
        }
        items, summary = compute_variance(
            baseline_items, issues.values("id", *ITEM_DATE_FIELDS).distinct(), weekend_days
        )
        return Response(
            {
                "baseline": serialize_baseline(baseline, with_count=not restricted),
                "items": items,
                "summary": summary,
                "weekend_days": weekend_days,
            },
            status=status.HTTP_200_OK,
        )

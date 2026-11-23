# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Which work items a schedule analysis covers, and the critical ones among them.

The schedule analysis endpoint and the "critical path" filter of the work item lists share this: the work items of a
project, maybe narrowed to a module or a cycle, and for a guest who only sees their own work items, those alone.
"""

# Python imports
import uuid

# Third Party imports
from rest_framework.exceptions import ValidationError

# Module imports
from plane.utils.schedule_analysis import analyse_queryset
from plane.utils.weekend_days import default_weekend_days

# the guest role of a project member (plane.app.permissions.ROLE.GUEST)
GUEST_ROLE = 5

# Response header that names the filters of a request the server left out, comma separated; the web app tells the
# person (see plane.middleware.ignored_filters)
IGNORED_FILTERS_HEADER = "X-Ignored-Filters"
CRITICAL_FILTER = "is_critical"


def mark_filter_ignored(request, name):
    """Say that the filter ``name`` of ``request`` was left out of the answer."""
    # the middleware reads the Django request; a DRF request wraps it and does not pass attributes on
    django_request = getattr(request, "_request", request)
    ignored = getattr(django_request, "ignored_filters", None)
    if ignored is None:
        ignored = django_request.ignored_filters = []
    if name not in ignored:
        ignored.append(name)


def scoped_work_items(user, slug, project, module_id=None, cycle_id=None):
    """The work items a schedule analysis of ``project`` covers for ``user``: those of the project, narrowed to a module
    or a cycle, archived, deleted and draft ones left out (as in ``Issue.issue_objects``)."""
    from plane.db.models import Issue, ProjectMember

    scope = {}
    if module_id:
        scope["issue_module__module_id"] = module_id
        scope["issue_module__deleted_at__isnull"] = True
    if cycle_id:
        scope["issue_cycle__cycle_id"] = cycle_id
        scope["issue_cycle__deleted_at__isnull"] = True
    queryset = Issue.issue_objects.filter(workspace__slug=slug, project_id=project.id, **scope)
    is_restricted_guest = (
        not project.guest_view_all_features
        and ProjectMember.objects.filter(project_id=project.id, member=user, role=GUEST_ROLE, is_active=True).exists()
    )
    if is_restricted_guest:
        queryset = queryset.filter(created_by=user)
    return queryset


def analyse_scope(user, slug, project, module_id=None, cycle_id=None):
    """The schedule analysis (see ``analyse_queryset``) of the work items ``user`` sees in ``project``."""
    queryset = scoped_work_items(user, slug, project, module_id=module_id, cycle_id=cycle_id)
    weekend_days = default_weekend_days() if project.weekend_days is None else project.weekend_days
    return analyse_queryset(queryset, project.id, weekend_days)


def _as_uuid(raw, name):
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        raise ValidationError({"message": f"{name} must be an id", "code": "invalid_filter_scope"})


def critical_issue_ids(request):
    """The ids of the critical work items in the project (and module or cycle) of the list ``request`` is for.

    The scope is read from the URL of the request. The answer is kept on the request, so a filter that appears several
    times in one request (inside a negation, say) is computed once. Raises a validation error where the filter has
    no meaning: a list that is not of one project.

    Returns None, and marks the filter as ignored (``X-Ignored-Filters``), when the analysis is cut off at its limit:
    it describes only part of the plan, so filtering by it would silently drop work items. The list then comes back
    unfiltered by this condition and the web app tells the person.
    """
    from plane.db.models import Project

    kwargs = getattr(request, "parser_context", None) or {}
    kwargs = kwargs.get("kwargs", {})
    project_id = _as_uuid(kwargs.get("project_id"), "project")
    if project_id is None:
        raise ValidationError(
            {
                "message": "The critical path filter is only available in a list of one project",
                "code": "critical_filter_needs_project",
            }
        )
    module_id = _as_uuid(kwargs.get("module_id"), "module")
    cycle_id = _as_uuid(kwargs.get("cycle_id"), "cycle")

    cache_key = (project_id, module_id, cycle_id)
    cached = getattr(request, "_critical_issue_ids", None)
    if cached is not None and cached[0] == cache_key:
        return cached[1]

    slug = kwargs.get("slug")
    project = Project.objects.filter(pk=project_id, workspace__slug=slug).first()
    if project is None:
        raise ValidationError({"message": "Project not found", "code": "invalid_filter_scope"})
    analysis = analyse_scope(request.user, slug, project, module_id=module_id, cycle_id=cycle_id)
    if analysis["truncated"]:
        mark_filter_ignored(request, CRITICAL_FILTER)
        request._critical_issue_ids = (cache_key, None)
        return None
    ids = {uuid.UUID(issue_id) for issue_id in analysis["critical_ids"]}
    request._critical_issue_ids = (cache_key, ids)
    return ids

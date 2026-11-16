# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""All sub-work items below some work items, found with one recursive query."""

from django.db import connection
from rest_framework import status
from rest_framework.response import Response

from plane.db.models import Issue, Project
from plane.utils.work_item_edit_rule import work_item_edit_denied

# Work items nest at most this deep (the same bound as the parent rules)
MAX_DESCENDANT_DEPTH = 100
# A request that touches more sub-work items than this is refused
MAX_DESCENDANTS = 1000


class TooManyDescendantsError(Exception):
    pass


def descendant_issue_ids(*, root_ids, project_id, workspace_id) -> list[str]:
    """Ids of every sub-work item (children, their children, ...) of ``root_ids`` in the project.

    Archived and draft items are included, callers filter what they need. A work item that is itself one of the
    roots is not left out. Raises ``TooManyDescendantsError`` above ``MAX_DESCENDANTS``.
    """

    roots = [str(root_id) for root_id in root_ids if root_id]
    if not roots:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH RECURSIVE tree AS (
                SELECT issue.id, 1 AS depth
                FROM issues AS issue
                WHERE issue.parent_id = ANY(%s::uuid[])
                  AND issue.project_id = %s
                  AND issue.workspace_id = %s
                  AND issue.deleted_at IS NULL

                UNION

                SELECT child.id, tree.depth + 1
                FROM issues AS child
                INNER JOIN tree ON child.parent_id = tree.id
                WHERE child.project_id = %s
                  AND child.workspace_id = %s
                  AND child.deleted_at IS NULL
                  AND tree.depth < %s
            )
            SELECT DISTINCT id FROM tree LIMIT %s
            """,
            [roots, project_id, workspace_id, project_id, workspace_id, MAX_DESCENDANT_DEPTH, MAX_DESCENDANTS + 1],
        )
        ids = [str(row[0]) for row in cursor.fetchall()]

    if len(ids) > MAX_DESCENDANTS:
        raise TooManyDescendantsError()
    return ids


def wants_sub_issues(value) -> bool:
    """Whether a request's ``include_sub_issues`` (a body value or a query string) switches the copy on."""
    return value is True or str(value).lower() in {"1", "true", "yes"}


def with_sub_issues(user, slug, project_id, issue_ids, *, only_active):
    """``issue_ids`` plus all their sub-work items as ``(ids, None)``, or ``(None, error_response)``.

    A person the assignee edit rule keeps from changing one of the sub-work items cannot move the parent together
    with them. ``only_active`` leaves out archived and draft items (adding); removing takes them all.
    """

    workspace_id = Project.objects.filter(pk=project_id).values_list("workspace_id", flat=True).first()
    try:
        found = descendant_issue_ids(root_ids=issue_ids, project_id=project_id, workspace_id=workspace_id)
    except TooManyDescendantsError:
        return None, Response(
            {"error": f"At most {MAX_DESCENDANTS} sub-work items can be moved at once"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if only_active:
        found = [
            str(pk)
            for pk in Issue.issue_objects.filter(workspace__slug=slug, project_id=project_id, pk__in=found).values_list(
                "id", flat=True
            )
        ]
    denied = work_item_edit_denied(user, project_id, found)
    if denied is not None:
        return None, denied
    ordered = [str(pk) for pk in issue_ids]
    known = set(ordered)
    return ordered + [pk for pk in found if pk not in known], None

# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the work item hierarchy rules of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""Server-side rules for a work item's parent: same project, no cycle, an Epic has no parent."""

from django.db import connection

from plane.db.models import Issue

MAX_HIERARCHY_DEPTH = 100
# One request attaches at most this many sub-work items
MAX_SUB_WORK_ITEMS_PER_REQUEST = 100


class WorkItemInvariantError(Exception):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


def parent_ancestry_ids(*, parent_id, project_id, workspace_id):
    """The parent and all its ancestors, found in one bounded, parameterized query."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH RECURSIVE ancestry AS (
                SELECT
                    issue.id,
                    issue.parent_id,
                    ARRAY[issue.id] AS path,
                    FALSE AS cycle,
                    1 AS depth
                FROM issues AS issue
                WHERE issue.id = %s
                  AND issue.project_id = %s
                  AND issue.workspace_id = %s
                  AND issue.deleted_at IS NULL

                UNION ALL

                SELECT
                    parent.id,
                    parent.parent_id,
                    ancestry.path || parent.id,
                    parent.id = ANY(ancestry.path) AS cycle,
                    ancestry.depth + 1 AS depth
                FROM issues AS parent
                INNER JOIN ancestry ON parent.id = ancestry.parent_id
                WHERE parent.project_id = %s
                  AND parent.workspace_id = %s
                  AND parent.deleted_at IS NULL
                  AND NOT ancestry.cycle
                  AND ancestry.depth < %s
            )
            SELECT
                ancestry.id,
                ancestry.cycle,
                ancestry.depth,
                EXISTS (
                    SELECT 1
                    FROM issues AS next_parent
                    WHERE next_parent.id = ancestry.parent_id
                      AND next_parent.project_id = %s
                      AND next_parent.workspace_id = %s
                      AND next_parent.deleted_at IS NULL
                ) AS has_parent
            FROM ancestry
            ORDER BY ancestry.depth
            """,
            [
                parent_id,
                project_id,
                workspace_id,
                project_id,
                workspace_id,
                MAX_HIERARCHY_DEPTH,
                project_id,
                workspace_id,
            ],
        )
        rows = cursor.fetchall()

    if any(row[1] for row in rows):
        raise WorkItemInvariantError("parent_id", "The existing parent hierarchy contains a cycle")
    if rows and rows[-1][2] == MAX_HIERARCHY_DEPTH and rows[-1][3]:
        raise WorkItemInvariantError(
            "parent_id",
            f"Work item hierarchy cannot exceed {MAX_HIERARCHY_DEPTH} levels",
        )
    return {row[0] for row in rows}


def validate_work_item_parent(*, project_id, workspace_id, issue_type, parent, issue_id=None):
    """Check a type/parent pair before it is saved and return the parent as found in the project.

    `issue_type` is the type the work item will have afterwards, `issue_id` is None for a new work item.
    """

    if parent is None:
        return None

    scoped_parent = (
        Issue.objects.filter(pk=parent.pk, workspace_id=workspace_id, project_id=project_id)
        .only("id", "parent_id")
        .first()
    )
    if scoped_parent is None:
        raise WorkItemInvariantError("parent_id", "Parent must belong to this project")

    if issue_id is not None and scoped_parent.id == issue_id:
        raise WorkItemInvariantError("parent_id", "A work item cannot be its own parent")

    if issue_type is not None and issue_type.is_epic:
        raise WorkItemInvariantError("parent_id", "Epic work items cannot have a parent")

    ancestry_ids = parent_ancestry_ids(
        parent_id=scoped_parent.id,
        project_id=project_id,
        workspace_id=workspace_id,
    )
    if issue_id is not None and issue_id in ancestry_ids:
        raise WorkItemInvariantError("parent_id", "Parent assignment would create a cycle")
    return scoped_parent

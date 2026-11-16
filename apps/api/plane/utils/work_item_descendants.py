# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""All sub-work items below some work items, found with one recursive query."""

from django.db import connection

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

# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""The nearest Epic above a work item, as a query expression."""

from django.db.models import F, Func, UUIDField

from plane.utils.work_item_hierarchy import MAX_HIERARCHY_DEPTH


class EpicAncestor(Func):
    """The nearest Epic in a work item's parent chain, the work item itself included.

    A correlated scalar subquery, so the ORM resolves the outer work item column and the expression can group,
    partition and count like a model field. Any type with `is_epic` counts, so it works with several Epic types.
    The walk follows live (not soft-deleted) rows and stops at the hierarchy depth cap, which also bounds it on
    damaged cyclic data. It runs once per row, so it is only annotated where a grouping asks for it.
    """

    template = (
        "(WITH RECURSIVE epic_ancestry(id, parent_id, type_id, depth) AS ("
        " SELECT node.id, node.parent_id, node.type_id, 1"
        " FROM issues AS node"
        " WHERE node.id = %(expressions)s AND node.deleted_at IS NULL"
        " UNION ALL"
        " SELECT parent.id, parent.parent_id, parent.type_id, epic_ancestry.depth + 1"
        " FROM issues AS parent"
        " INNER JOIN epic_ancestry ON parent.id = epic_ancestry.parent_id"
        " WHERE parent.deleted_at IS NULL AND epic_ancestry.depth < " + str(int(MAX_HIERARCHY_DEPTH)) + ""
        ")"
        " SELECT epic_ancestry.id"
        " FROM epic_ancestry"
        " INNER JOIN issue_types ON issue_types.id = epic_ancestry.type_id"
        " WHERE issue_types.is_epic"
        " ORDER BY epic_ancestry.depth"
        " LIMIT 1)"
    )
    output_field = UUIDField()

    def __init__(self, expression=None, **extra):
        super().__init__(expression if expression is not None else F("id"), **extra)

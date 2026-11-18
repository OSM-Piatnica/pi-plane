# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""The nearest Epic above a work item, as a query expression."""

from django.db.models import F, Func, UUIDField
from django.db.models.expressions import RawSQL

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


def epic_tree_ids(epic_ids=None) -> RawSQL:
    """The ids of the work items that sit under the given Epics (the Epics themselves included), as a subquery.

    This is the same membership as `EpicAncestor`, found the other way round: from the Epics down instead of from
    every work item up. The cost is the size of the Epic subtrees, not of the instance, so it is what a filter uses
    where the grouping would have to walk the parent chain of every work item.

    - `epic_ids=None` takes every Epic of the instance (a small set); its complement is "under no Epic".
    - A child that is itself an Epic is not entered: it is the nearest Epic of its own subtree, as in
      `EpicAncestor`, and starts a tree of its own.
    - Soft-deleted work items end a branch, and the depth is capped, as in `EpicAncestor`.
    - An id that is not an Epic gives nothing.
    """

    if epic_ids is None:
        roots, params = "TRUE", []
    else:
        roots, params = "root.id = ANY(%s::uuid[])", [[str(epic_id) for epic_id in epic_ids]]
    sql = (
        "WITH RECURSIVE epic_tree(id, depth) AS ("
        " SELECT root.id, 1"
        " FROM issues AS root"
        " INNER JOIN issue_types AS root_type ON root_type.id = root.type_id AND root_type.is_epic"
        " WHERE root.deleted_at IS NULL AND " + roots + " UNION ALL"
        " SELECT child.id, epic_tree.depth + 1"
        " FROM issues AS child"
        " INNER JOIN epic_tree ON child.parent_id = epic_tree.id"
        " LEFT JOIN issue_types AS child_type ON child_type.id = child.type_id"
        " WHERE child.deleted_at IS NULL"
        " AND epic_tree.depth < " + str(int(MAX_HIERARCHY_DEPTH)) + " AND NOT COALESCE(child_type.is_epic, FALSE)"
        ") SELECT id FROM epic_tree"
    )
    return RawSQL(sql, params)

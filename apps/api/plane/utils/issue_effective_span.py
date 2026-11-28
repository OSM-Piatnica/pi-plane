# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The dates a work item stands for in its dependencies: its own, widened by those of its sub-work items.

A parent has its own start and finish dates, and the timeline also draws the span of the work items below it (the
roll-up, ``issue_hierarchy.date_rollup``). Where the roll-up reaches past the parent's own dates, the parent counts
with the wider span **when it is the predecessor** of a timeline relation: a sub-work item that ends late makes the
parent end late for what depends on it. A parent without dates of its own counts with the roll-up alone.

As the successor a work item counts with its own dates only. Sub-work items do not take over the predecessors of
their parent, and a parent is not held back by what holds back its sub-work items.

The spans are worked out over planned dates: ``set_dates`` records the dates a change (or a planned shift) gives a
work item, and the roll-ups of its ancestors follow. ``stored_span`` gives the span as it is saved now.
"""

import uuid
from contextlib import contextmanager

from plane.utils.issue_hierarchy import IssueTree, date_rollup
from plane.utils.issue_relation_constraints import _as_date

# A parent chain longer than this is corrupt data (a loop the tree did not catch); it is not followed further
MAX_DEPTH = 100


def _key(issue_id):
    return issue_id if isinstance(issue_id, uuid.UUID) else uuid.UUID(str(issue_id))


def widen(own_start, own_finish, rollup):
    """``(start, finish)`` of own dates widened by a roll-up (``date_rollup``'s result, or None)."""
    start, finish = _as_date(own_start), _as_date(own_finish)
    if not rollup:
        return start, finish
    rollup_start, rollup_end = rollup.get("start_date"), rollup.get("target_date")
    starts = [day for day in (start, rollup_start) if day is not None]
    ends = [day for day in (finish, rollup_end) if day is not None]
    return (min(starts) if starts else None), (max(ends) if ends else None)


def is_later(after, before) -> bool:
    """Whether a date moved later; gaining a date counts, losing one does not."""
    return after is not None and (before is None or after > before)


class EffectiveSpans:
    """Effective spans of work items, with the planned dates of some of them applied. One per request."""

    def __init__(self):
        self._trees = {}
        # work item id -> (start, finish) planned for it, and the dates it has saved, for the trees loaded later
        self._planned = {}
        self._stored = {}

    def tree(self, project_id) -> IssueTree:
        tree = self._trees.get(project_id)
        if tree is None:
            tree = IssueTree.for_project(project_id, fields=("start_date", "finish_date"))
            for key, dates in self._planned.items():
                node = tree.node(key)
                if node is not None:
                    self._stored.setdefault(key, (node["start_date"], node["finish_date"]))
                    node["start_date"], node["finish_date"] = dates
            self._trees[project_id] = tree
        return tree

    def set_dates(self, issue_id, start_date, finish_date):
        """Plan these dates for a work item: its own span and the roll-ups above it use them from now on."""
        key = _key(issue_id)
        dates = (_as_date(start_date), _as_date(finish_date))
        self._planned[key] = dates
        for tree in self._trees.values():
            node = tree.node(key)
            if node is not None:
                self._stored.setdefault(key, (node["start_date"], node["finish_date"]))
                node["start_date"], node["finish_date"] = dates

    def own_dates(self, issue) -> dict:
        """The work item's own dates, planned or saved."""
        planned = self._planned.get(_key(issue.id))
        if planned is not None:
            return {"start_date": planned[0], "finish_date": planned[1]}
        return {"start_date": _as_date(issue.start_date), "finish_date": _as_date(issue.finish_date)}

    def span(self, issue, own=None) -> dict:
        """The dates ``issue`` counts with as a predecessor: ``own`` dates (default: planned or saved) widened."""
        own = own if own is not None else self.own_dates(issue)
        tree = self.tree(issue.project_id)
        rollup = date_rollup(tree, issue.id) if issue.id in tree else None
        start, finish = widen(own.get("start_date"), own.get("finish_date"), rollup)
        return {"start_date": start, "finish_date": finish}

    def stored_span(self, issue) -> dict:
        """The span as saved now, without any planned dates."""
        with self._saved_dates(issue.project_id):
            return self.span(issue, {"start_date": issue.start_date, "finish_date": issue.finish_date})

    @contextmanager
    def _saved_dates(self, project_id):
        tree = self.tree(project_id)
        swapped = []
        for key, dates in self._stored.items():
            node = tree.node(key)
            if node is not None:
                swapped.append((node, node["start_date"], node["finish_date"]))
                node["start_date"], node["finish_date"] = dates
        try:
            yield
        finally:
            for node, start, finish in swapped:
                node["start_date"], node["finish_date"] = start, finish

    def ancestors(self, issue) -> list:
        """The ids of the work items above ``issue``, nearest first."""
        tree = self.tree(issue.project_id)
        found = []
        seen = {issue.id}
        node = tree.node(issue.id)
        while node is not None and len(found) < MAX_DEPTH:
            parent_id = node["parent_id"]
            if parent_id is None or parent_id in seen or parent_id not in tree:
                break
            seen.add(parent_id)
            found.append(parent_id)
            node = tree.node(parent_id)
        return found

    def descendants(self, issue) -> list:
        """The ids of every work item below ``issue``, at any depth."""
        tree = self.tree(issue.project_id)
        return tree.descendants(issue.id) if issue.id in tree else []

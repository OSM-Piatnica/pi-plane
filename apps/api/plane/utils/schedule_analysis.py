# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Schedule analysis of a project: the critical path, float and "needed by" dates.

The analysis is the critical path method over the work items that have a start and a finish date and the timeline
relations between them (``blocked_by``, ``start_before``, ``finish_before``, ``start_before_finish``, each with its
lag).
Days are working days of the project, counted exactly as the relation rules and the "move dependents" offer count
them (``issue_relation_constraints``, ``issue_reschedule``): the requirement a predecessor puts on a successor is
``issue_reschedule._successor_requirement``, and a work item that moves keeps its length in working days
(``issue_reschedule._move_to``).

The rules, in short (``docs/critical-path.md`` has them for people):

* **What is analysed.** Work items with both dates. One with no dates or only one date is left out and counted; the
  ones that have a timeline relation are listed, because a chain is broken there. One whose finish is before its start
  is left out the same way, but counted on its own (``inverted_count``).
* **Planned dates are the starting point.** Pi-Plane does not schedule work items by itself, people set the dates. So
  the planned start is a "start no earlier than" bound: the earliest start is the later of the planned start and what
  the predecessors allow. In a plan that keeps every relation the earliest dates are the planned dates; where a
  relation is broken the earliest dates fall later than the planned ones.
* **The project end** is the latest earliest finish among the analysed work items.
* **Latest dates.** A work item without (open) successors may finish as late as the project end. Otherwise its latest
  finish is what keeps every successor within its own latest dates.
* **Total float** is the number of working days from the earliest to the latest finish. A work item with no float is
  **critical**: any delay to it moves the project end.
* **Critical links.** A relation is on the critical path when it is driving: both of its work items are critical and
  the date it asks of the successor is the successor's earliest date, so that it has no slack of its own. A relation
  between two critical work items that leaves the successor room (it could start or finish later as far as this
  relation goes) is not critical.
* **Fixed points.** Completed and cancelled work items are not moved by the analysis and have no float: their dates
  stay as planned. They still hold back their successors in the forward pass (like the date rules do), but ask
  nothing of their predecessors in the backward pass, as a late predecessor can no longer delay them.
* **Due dates** (``target_date``) never make a work item critical. They feed a separate backward pass that gives
  ``needed_by``: the latest finish that still lets every open work item downstream meet its due date. A completed or
  cancelled work item stops the chain: its due date, and those beyond it, do not count. It is None when nothing
  counted downstream has a due date. A work item's own due date is not part of its own ``needed_by``.
* **Hierarchy is ignored.** Every dated work item is a node of its own; a parent is not a predecessor of its
  sub-work items and relations of a parent do not pass down to them.
  The analysis also takes a parent with its own dates only, not with the span widened by its sub-work items that the
  date rules and the "move dependents" offer use (``issue_effective_span``): the sub-work items are nodes of their
  own already, and the critical path through a parent's span is a separate question (see the D8c note in
  ``docs/plans/workflow-roadmap.md``).
* **Cycles.** Work items that depend on each other in a circle are reported. The relations inside such a circle are
  left out of the analysis, relations in and out of it still count.
* **Relations to work items outside the analysed set** (another project, undated, outside the scope) are ignored.
"""

from collections import defaultdict
from datetime import date

from plane.utils.issue_relation_constraints import STORED_TIMELINE_RELATION_TYPES
from plane.utils.issue_reschedule import (
    NOT_MOVED_GROUPS,
    _move_to,
    _successor_requirement,
    _working_days_between,
)
from plane.utils.work_item_duration import (
    add_working_days,
    count_working_days,
    effective_finish,
    effective_start,
    shift_working_days,
    subtract_working_days,
    to_work_item_date,
)

# More dated work items than this are not analysed in one go: the first ones by start date are, and the answer says so
MAX_ANALYSED_ITEMS = 2000

# A stored relation ``issue <type> related_issue`` as (predecessor is the issue?, rule seen from the predecessor)
_STORED_AS_PREDECESSOR_RULE = {
    "blocked_by": (False, "blocking"),
    "start_before": (True, "start_before"),
    "finish_before": (True, "finish_before"),
    "start_before_finish": (True, "start_before_finish"),
}
assert set(_STORED_AS_PREDECESSOR_RULE) == set(STORED_TIMELINE_RELATION_TYPES)


def _strongly_connected(node_ids, successors):
    """Tarjan's algorithm without recursion: the groups of nodes that can all reach each other."""
    index_of, low, on_stack, stack, groups = {}, {}, set(), [], []
    counter = 0
    for root in node_ids:
        if root in index_of:
            continue
        work = [(root, iter(successors.get(root, ())))]
        index_of[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, children = work[-1]
            advanced = False
            for child in children:
                if child not in index_of:
                    index_of[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, iter(successors.get(child, ()))))
                    advanced = True
                    break
                if child in on_stack:
                    low[node] = min(low[node], index_of[child])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index_of[node]:
                group = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    group.append(member)
                    if member == node:
                        break
                groups.append(group)
    return groups


def _topological_order(node_ids, edges_out, edges_in):
    """Kahn's algorithm; the graph has no cycle left when this is called."""
    waiting = {node_id: len(edges_in.get(node_id, ())) for node_id in node_ids}
    ready = [node_id for node_id in node_ids if waiting[node_id] == 0]
    order = []
    while ready:
        node_id = ready.pop()
        order.append(node_id)
        for _, successor_id, _ in edges_out.get(node_id, ()):
            waiting[successor_id] -= 1
            if waiting[successor_id] == 0:
                ready.append(successor_id)
    return order


def _latest_finish_bound(rule, lag, successor_latest_start, successor_latest_finish, length, weekend_days):
    """The latest finish a predecessor may have for its successor to keep its latest dates: the rule of
    ``_successor_requirement`` read backwards."""
    if rule == "blocking":
        return shift_working_days(successor_latest_start, -(1 + lag), weekend_days)
    if rule == "finish_before":
        return shift_working_days(successor_latest_finish, -lag, weekend_days)
    # the two rules that bind the predecessor's start: its finish follows from its length
    anchor = successor_latest_start if rule == "start_before" else successor_latest_finish
    return add_working_days(shift_working_days(anchor, -lag, weekend_days), length, weekend_days)


def analyse_schedule(items, relations, weekend_days=()):
    """Run the analysis described in the module docstring.

    :param items: dicts with ``id``, ``start_date``, ``finish_date``, and optionally ``target_date`` (the due date)
        and ``state_group``
    :param relations: ``(issue_id, related_issue_id, relation_type, lag_days)`` as stored (forward types only)
    :param weekend_days: the project's non-working days, 0 = Sunday ... 6 = Saturday
    :return: dict with ``project_start``, ``project_end``, ``items`` (id -> result), ``critical_ids``,
        ``critical_links``, ``cycles``, ``undated_count``, ``inverted_count`` and ``undated_linked_ids``; dates are
        ``date`` objects
    """
    nodes = {}
    # left out: work items without both dates, and those whose finish is before their start
    undated, inverted = set(), set()
    for item in items:
        start, finish = to_work_item_date(item.get("start_date")), to_work_item_date(item.get("finish_date"))
        if start is None or finish is None:
            undated.add(item["id"])
            continue
        if finish < start:
            inverted.add(item["id"])
            continue
        start, finish = effective_start(start, weekend_days), effective_finish(finish, weekend_days)
        if finish < start:
            # a range made only of weekend days lasts one day, the working day after it
            finish = start
        due = to_work_item_date(item.get("target_date"))
        nodes[item["id"]] = {
            "start_date": start,
            "finish_date": finish,
            "length": max(count_working_days(start, finish, weekend_days), 1),
            "due": effective_finish(due, weekend_days) if due else None,
            "is_fixed": item.get("state_group") in NOT_MOVED_GROUPS,
        }

    # predecessor -> [(rule, successor, lag)] and the same edges by successor
    edges_out, edges_in = defaultdict(list), defaultdict(list)
    undated_linked = set()
    for issue_id, related_id, relation_type, lag in relations:
        mapping = _STORED_AS_PREDECESSOR_RULE.get(relation_type)
        if mapping is None or issue_id == related_id:
            continue
        undated_linked.update(end for end in (issue_id, related_id) if end in undated or end in inverted)
        if issue_id not in nodes or related_id not in nodes:
            continue
        issue_is_predecessor, rule = mapping
        predecessor_id, successor_id = (issue_id, related_id) if issue_is_predecessor else (related_id, issue_id)
        edges_out[predecessor_id].append((rule, successor_id, lag or 0))
        edges_in[successor_id].append((rule, predecessor_id, lag or 0))

    # circles of work items: reported, and the relations inside one are dropped so that the rest can be analysed
    groups = _strongly_connected(
        list(nodes), {node_id: [successor_id for _, successor_id, _ in out] for node_id, out in edges_out.items()}
    )
    cycles = [group for group in groups if len(group) > 1]
    if cycles:
        cycle_of = {node_id: index for index, group in enumerate(cycles) for node_id in group}

        def crosses(first, second):
            return cycle_of.get(first) is None or cycle_of.get(first) != cycle_of.get(second)

        edges_out = defaultdict(
            list,
            {node_id: [edge for edge in out if crosses(node_id, edge[1])] for node_id, out in edges_out.items()},
        )
        edges_in = defaultdict(
            list,
            {node_id: [edge for edge in inn if crosses(edge[1], node_id)] for node_id, inn in edges_in.items()},
        )

    order = _topological_order(list(nodes), edges_out, edges_in)

    # forward pass: earliest dates
    earliest = {}
    for node_id in order:
        node = nodes[node_id]
        dates = {"start_date": node["start_date"], "finish_date": node["finish_date"]}
        if not node["is_fixed"]:
            required = {"start_date": None, "finish_date": None}
            for rule, predecessor_id, lag in edges_in.get(node_id, ()):
                predecessor = earliest[predecessor_id]
                field_name, bound = _successor_requirement(
                    rule, predecessor["start_date"], predecessor["finish_date"], lag, weekend_days
                )
                if required[field_name] is None or bound > required[field_name]:
                    required[field_name] = bound
            # a later start first, then a later finish: each move keeps the length and only ever goes later
            for field_name in ("start_date", "finish_date"):
                bound = required[field_name]
                if bound is not None and bound > dates[field_name]:
                    dates["start_date"], dates["finish_date"] = _move_to(dates, field_name, bound, weekend_days)
        earliest[node_id] = dates

    project_end = max((dates["finish_date"] for dates in earliest.values()), default=None)
    project_start = min((dates["start_date"] for dates in earliest.values()), default=None)

    def backward(own_bound):
        """Latest finish per open node: ``own_bound(node_id)`` (or None) and what the open successors need."""
        latest = {}
        from_successors = {}
        for node_id in reversed(order):
            node = nodes[node_id]
            if node["is_fixed"]:
                continue
            needed = None
            for rule, successor_id, lag in edges_out.get(node_id, ()):
                successor = latest.get(successor_id)
                if successor is None:
                    continue
                bound = _latest_finish_bound(rule, lag, successor[0], successor[1], node["length"], weekend_days)
                if needed is None or bound < needed:
                    needed = bound
            from_successors[node_id] = needed
            bounds = [bound for bound in (own_bound(node_id), needed) if bound is not None]
            if bounds:
                finish = min(bounds)
                latest[node_id] = (subtract_working_days(finish, node["length"], weekend_days), finish)
        return latest, from_successors

    latest, _ = backward(lambda node_id: project_end)
    _, needed_by = backward(lambda node_id: nodes[node_id]["due"])

    results = {}
    critical_ids = []
    for node_id in order:
        node, dates = nodes[node_id], earliest[node_id]
        if node["is_fixed"]:
            latest_start, latest_finish, total_float = dates["start_date"], dates["finish_date"], None
        else:
            latest_start, latest_finish = latest[node_id]
            total_float = _working_days_between(dates["finish_date"], latest_finish, weekend_days)
        is_critical = total_float is not None and total_float <= 0
        if is_critical:
            critical_ids.append(node_id)
        results[node_id] = {
            "earliest_start": dates["start_date"],
            "earliest_finish": dates["finish_date"],
            "latest_start": latest_start,
            "latest_finish": latest_finish,
            "total_float": total_float,
            "is_critical": is_critical,
            "is_fixed": node["is_fixed"],
            "needed_by": needed_by.get(node_id),
        }

    # driving relations between critical work items: the successor's earliest date is exactly what the relation asks
    critical_links = []
    critical = set(critical_ids)
    for predecessor_id in order:
        if predecessor_id not in critical:
            continue
        predecessor = earliest[predecessor_id]
        for rule, successor_id, lag in edges_out.get(predecessor_id, ()):
            if successor_id not in critical:
                continue
            field_name, bound = _successor_requirement(
                rule, predecessor["start_date"], predecessor["finish_date"], lag, weekend_days
            )
            if bound >= earliest[successor_id][field_name]:
                critical_links.append({"source": predecessor_id, "target": successor_id, "relation_type": rule})

    return {
        "project_start": project_start,
        "project_end": project_end,
        "items": results,
        "critical_ids": critical_ids,
        "critical_links": critical_links,
        "cycles": cycles,
        "undated_count": len(undated),
        "inverted_count": len(inverted),
        "undated_linked_ids": sorted(undated_linked, key=str),
    }


def _iso(value):
    return value.isoformat() if isinstance(value, date) else value


def serialize_analysis(analysis: dict) -> dict:
    """The analysis as JSON: ids as strings, dates as ISO strings."""
    return {
        "project_start": _iso(analysis["project_start"]),
        "project_end": _iso(analysis["project_end"]),
        "items": {
            str(issue_id): {key: _iso(value) for key, value in result.items()}
            for issue_id, result in analysis["items"].items()
        },
        "critical_ids": [str(issue_id) for issue_id in analysis["critical_ids"]],
        "critical_links": [
            {"source": str(link["source"]), "target": str(link["target"]), "relation_type": link["relation_type"]}
            for link in analysis["critical_links"]
        ],
        "cycles": [[str(issue_id) for issue_id in cycle] for cycle in analysis["cycles"]],
        "undated_count": analysis["undated_count"],
        "inverted_count": analysis["inverted_count"],
        "undated_linked_ids": [str(issue_id) for issue_id in analysis["undated_linked_ids"]],
    }


def analyse_queryset(queryset, project_id, weekend_days, max_items=MAX_ANALYSED_ITEMS):
    """Analyse the work items of ``queryset``: those of project ``project_id`` the person may see, maybe narrowed to
    a module or a cycle.

    Nothing is cached, every call computes from five queries: the dated work items, the project's timeline
    relations, the left-out work items those relations touch and counts of the undated and the inverted ones. Work
    items whose finish is before their start do not count as dated here, nor towards the cap. When more than
    ``max_items`` work items are dated, only the first ones by start date are analysed and ``truncated`` is set: the
    answer then describes a cut-off network and must not be shown as the critical path of the whole scope.
    """
    from django.db.models import F, Q

    from plane.db.models import IssueRelation

    is_dated = Q(start_date__isnull=False, finish_date__isnull=False)
    is_inverted = is_dated & Q(finish_date__lt=F("start_date"))
    rows = list(
        queryset.filter(is_dated & ~is_inverted)
        .order_by("start_date", "finish_date", "sequence_id")
        .values("id", "start_date", "finish_date", "target_date", "state__group")[: max_items + 1]
    )
    truncated = len(rows) > max_items
    rows = rows[:max_items]
    items = [{**row, "state_group": row["state__group"]} for row in rows]
    analysed_ids = {row["id"] for row in rows}

    relations = list(
        IssueRelation.objects.filter(
            issue__project_id=project_id,
            related_issue__project_id=project_id,
            relation_type__in=STORED_TIMELINE_RELATION_TYPES,
        ).values_list("issue_id", "related_issue_id", "relation_type", "lag_days")
    )
    # left-out work items only matter where a relation links them to an analysed one
    linked_ids = set()
    for issue_id, related_id, _, _ in relations:
        if issue_id in analysed_ids and related_id not in analysed_ids:
            linked_ids.add(related_id)
        elif related_id in analysed_ids and issue_id not in analysed_ids:
            linked_ids.add(issue_id)
    undated = queryset.exclude(is_dated)
    items += list(
        queryset.filter(~is_dated | is_inverted).filter(id__in=linked_ids).values("id", "start_date", "finish_date")
    )

    payload = serialize_analysis(analyse_schedule(items, relations, weekend_days))
    payload.update(
        {
            "undated_count": undated.count(),
            "inverted_count": queryset.filter(is_inverted).count(),
            "weekend_days": list(weekend_days or ()),
            "analysed_count": len(analysed_ids),
            "max_items": max_items,
            "truncated": truncated,
        }
    )
    return payload

# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Epics are left out of the progress numbers of modules and cycles.

An Epic is a work item with children, so counting it next to them counts the same work twice. Epics still show in
the lists of a module or cycle. A work item without a type counts, like any other that is not an Epic.

Two forms, for the two ways the numbers are built:

- a query over work items (``Issue.issue_objects.filter(issue_module__module_id=...)``) uses
  ``Issue.progress_objects`` instead of ``Issue.issue_objects``;
- a count over the work items of a cycle or module (``Count("issue_cycle__issue__id", filter=Q(...))``) adds
  ``not_epic_q("issue_cycle__issue__")`` to the filter.
"""

from django.db.models import Q


def not_epic_q(prefix: str = "") -> Q:
    """The work items behind ``prefix`` that are not Epics, written as a positive condition.

    ``prefix`` is the path to the work item, for example ``"issue_cycle__issue__"``. It is not ``~Q(...)`` on
    purpose: a negated condition across a reverse relation becomes a subquery and would drop the whole cycle
    when it has one Epic, instead of leaving that one work item out of the count.
    """

    return Q(**{f"{prefix}type__is_epic": False}) | Q(**{f"{prefix}type__isnull": True})

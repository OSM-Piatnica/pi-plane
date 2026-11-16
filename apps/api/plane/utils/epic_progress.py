# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Epics and reviews are left out of the progress numbers of modules and cycles.

An Epic is a work item with children, so counting it next to them counts the same work twice. A review is one step
of an approval, so counting it next to the approval counts one acceptance several times. Both still show in the
lists of a module or cycle. A work item without a type counts, like any other of a counted kind. The kinds that
are left out are `PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS`.

Two forms, for the two ways the numbers are built:

- a query over work items (``Issue.issue_objects.filter(issue_module__module_id=...)``) uses
  ``Issue.progress_objects`` instead of ``Issue.issue_objects``;
- a count over the work items of a cycle or module (``Count("issue_cycle__issue__id", filter=Q(...))``) adds
  ``not_epic_q("issue_cycle__issue__")`` to the filter.
"""

from django.db.models import Q

from plane.db.models.issue_type import PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS, IssueTypeKind

# Written as the kinds that count, so that the condition stays positive (see `not_epic_q`)
PROGRESS_COUNTED_KINDS = tuple(kind for kind in IssueTypeKind.values if kind not in PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS)


def not_epic_q(prefix: str = "") -> Q:
    """The work items behind ``prefix`` that count in progress (not Epics, not reviews), as a positive condition.

    ``prefix`` is the path to the work item, for example ``"issue_cycle__issue__"``. It is not ``~Q(...)`` on
    purpose: a negated condition across a reverse relation becomes a subquery and would drop the whole cycle
    when it has one Epic, instead of leaving that one work item out of the count.
    """

    return Q(**{f"{prefix}type__kind__in": PROGRESS_COUNTED_KINDS}) | Q(**{f"{prefix}type__isnull": True})

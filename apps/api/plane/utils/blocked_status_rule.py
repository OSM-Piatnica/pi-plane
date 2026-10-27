# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project rule: a work item cannot be started or completed while a work item that blocks it is still open.

The rule is switched on per project with ``Project.is_blocked_status_rule_enabled``, next to the parent rule and, like
it, independent of the state workflow. A blocker is a work item the item is *blocked by*; once it is completed or
cancelled it no longer holds the item back. Only a move into the ``started`` or ``completed`` group is refused: the
item may still sit in backlog or todo, or be cancelled.
"""

from typing import Optional

from django.db.models import Exists, OuterRef

from plane.db.models import Issue, State
from plane.db.models.state import StateGroup
from plane.utils.issue_timeline_relation_validation import issue_display_ref

BLOCKED_TARGET_GROUPS = (StateGroup.STARTED.value, StateGroup.COMPLETED.value)
FINISHED_GROUPS = (StateGroup.COMPLETED.value, StateGroup.CANCELLED.value)

# How many blockers the message names before it says "and N more"
MAX_NAMED_BLOCKERS = 3


def open_blockers(item_ref):
    """Work items that block the item and are not done yet; ``item_ref`` is a work item id or an ``OuterRef``."""
    return Issue.issue_objects.filter(
        issue_related__issue_id=item_ref,
        issue_related__relation_type="blocked_by",
        issue_related__deleted_at__isnull=True,
    ).exclude(state__group__in=FINISHED_GROUPS)


def has_open_blockers(item_ref=OuterRef("pk")):
    """Subquery expression for filtering work items that are still held back by an open blocker."""
    return Exists(open_blockers(item_ref))


def blocked_status_error(issue: Issue, to_state_id) -> Optional[str]:
    """The reason moving ``issue`` to ``to_state_id`` is refused by the rule, or None when it is allowed."""
    if not to_state_id or not issue.project.is_blocked_status_rule_enabled:
        return None

    group = State.all_state_objects.filter(pk=to_state_id).values_list("group", flat=True).first()
    if group not in BLOCKED_TARGET_GROUPS:
        return None

    blockers = list(open_blockers(issue.pk).select_related("project").order_by("created_at"))
    if not blockers:
        return None

    named = ", ".join(issue_display_ref(blocker) for blocker in blockers[:MAX_NAMED_BLOCKERS])
    more = len(blockers) - MAX_NAMED_BLOCKERS
    if more > 0:
        named += f" and {more} more"
    action = "started" if group == StateGroup.STARTED.value else "completed"
    noun = "work item that is" if len(blockers) == 1 else "work items that are"
    return f"This work item cannot be {action} while it is blocked by {len(blockers)} {noun} not done: {named}."

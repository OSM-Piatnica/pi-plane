# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Project rule: a work item cannot be completed while it still has open sub-items.

The rule is switched on per project with ``Project.is_parent_completion_rule_enabled``. It is independent of
the state workflow (``is_workflow_enabled``): it needs no flows and is not paused with a workflow. Only a move
into the ``completed`` group is blocked, and sub-items in ``completed`` or ``cancelled`` count as finished.
Archived and draft sub-items are ignored, like everywhere else work items are counted.
"""

from typing import Optional

from django.db.models import Exists, OuterRef
from rest_framework import status
from rest_framework.exceptions import APIException

from plane.db.models import Issue, State
from plane.db.models.state import StateGroup

BLOCKED_TARGET_GROUPS = (StateGroup.COMPLETED.value,)
FINISHED_GROUPS = (StateGroup.COMPLETED.value, StateGroup.CANCELLED.value)


def open_sub_items(parent_ref):
    """Sub-items that are not finished; ``parent_ref`` is a work item id or an ``OuterRef``."""
    return Issue.issue_objects.filter(parent_id=parent_ref).exclude(state__group__in=FINISHED_GROUPS)


def has_open_sub_items(parent_ref=OuterRef("pk")):
    """Subquery expression for filtering parents that still have open sub-items."""
    return Exists(open_sub_items(parent_ref))


def parent_completion_error(issue: Issue, to_state_id) -> Optional[str]:
    """The reason moving ``issue`` to ``to_state_id`` is refused by the rule, or None when it is allowed."""
    if not to_state_id or not issue.project.is_parent_completion_rule_enabled:
        return None

    group = State.all_state_objects.filter(pk=to_state_id).values_list("group", flat=True).first()
    if group not in BLOCKED_TARGET_GROUPS:
        return None

    count = open_sub_items(issue.pk).count()
    if not count:
        return None
    noun = "sub-item is" if count == 1 else "sub-items are"
    return f"This work item cannot be completed while {count} {noun} not done."


# Reopening a finished sub-item under a completed parent
#
# The parent is reopened with it, because it can no longer count as complete. The person has to confirm that
# first (``reopen_parent`` in the request); without it the move is refused with the code below and the list of
# parents that would be reopened, so a client can ask and send the request again.

REOPEN_REQUIRED_CODE = "parent_reopen_required"


class ParentReopenRequired(APIException):
    """Answers 400 with the payload as it is. A ``ValidationError`` raised inside a serializer would have every
    value wrapped in a list, and clients look for ``code`` as a plain string."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, payload: dict):
        self.detail = payload


def is_reopen_confirmed(data) -> bool:
    value = data.get("reopen_parent") if hasattr(data, "get") else None
    return value is True or (isinstance(value, str) and value.lower() in ("true", "1"))


def parents_to_reopen(issue: Issue, to_state_id) -> list:
    """Completed ancestors (nearest first) that reopening ``issue`` into ``to_state_id`` would reopen."""
    if not to_state_id or not issue.project.is_parent_completion_rule_enabled:
        return []

    groups = dict(State.all_state_objects.filter(pk__in=[to_state_id, issue.state_id]).values_list("pk", "group"))
    if groups.get(issue.state_id) not in FINISHED_GROUPS or groups.get(to_state_id) in FINISHED_GROUPS:
        return []

    chain = []
    seen = {issue.pk}
    parent = Issue.issue_objects.filter(pk=issue.parent_id).select_related("state").first() if issue.parent_id else None
    while parent and parent.pk not in seen and parent.state.group in BLOCKED_TARGET_GROUPS:
        chain.append(parent)
        seen.add(parent.pk)
        parent = (
            Issue.issue_objects.filter(pk=parent.parent_id).select_related("state").first()
            if parent.parent_id
            else None
        )
    return chain


def reopen_confirmation_payload(issue: Issue, to_state_id, confirmed: bool) -> Optional[dict]:
    """The error body to answer with when the move needs confirming, or None when it can go ahead."""
    if confirmed:
        return None
    parents = parents_to_reopen(issue, to_state_id)
    if not parents:
        return None
    return {
        "error": "Reopening this work item will also reopen its completed parent.",
        "code": REOPEN_REQUIRED_CODE,
        "parents": [{"id": str(p.id), "name": p.name, "sequence_id": p.sequence_id} for p in parents],
    }


def reopen_state_for(parent: Issue):
    """The state a reopened parent goes back to.

    The state it was in before it was completed, read from its activity; if that is unknown or no longer an
    open state (an imported work item, a deleted state), the project's first started state, else its default.
    """
    from plane.db.models import IssueActivity

    previous_id = (
        IssueActivity.objects.filter(issue_id=parent.pk, field="state", new_identifier=parent.state_id)
        .order_by("-created_at")
        .values_list("old_identifier", flat=True)
        .first()
    )
    if previous_id:
        previous = State.objects.filter(pk=previous_id, project_id=parent.project_id).first()
        if previous and previous.group not in FINISHED_GROUPS:
            return previous
    project_states = State.objects.filter(project_id=parent.project_id)
    return (
        project_states.filter(group=StateGroup.STARTED.value).order_by("sequence").first()
        or project_states.filter(default=True).first()
        or project_states.filter(group=StateGroup.UNSTARTED.value).order_by("sequence").first()
    )


def reopen_parents(issue: Issue, previous_state_id, actor_id) -> None:
    """Reopen the completed ancestors of ``issue``, which has just left a finished state. Call after saving it."""
    import json

    from django.utils import timezone

    from plane.bgtasks.issue_activities_task import issue_activity

    if not issue.project.is_parent_completion_rule_enabled:
        return
    # The ancestors are still completed; ``issue`` already holds the new state, so judge by the old one
    previous = Issue(pk=issue.pk, parent_id=issue.parent_id, state_id=previous_state_id, project=issue.project)
    chain = parents_to_reopen(previous, issue.state_id)
    if not chain:
        return
    for parent in chain:
        old_state_id = parent.state_id
        target = reopen_state_for(parent)
        if not target:
            continue
        parent.state = target
        parent.updated_by_id = actor_id
        parent.save(update_fields=["state", "updated_at", "updated_by_id"])
        issue_activity.delay(
            type="issue.activity.updated",
            requested_data=json.dumps({"state_id": str(target.id)}),
            actor_id=str(actor_id),
            issue_id=str(parent.id),
            project_id=str(parent.project_id),
            current_instance=json.dumps({"state_id": str(old_state_id)}),
            epoch=int(timezone.now().timestamp()),
            notification=True,
            # the parent is reopened as a side effect of what the person did to the sub-item: the people of the
            # parent are told, but the person is not subscribed to it by the activity
            subscriber=False,
        )

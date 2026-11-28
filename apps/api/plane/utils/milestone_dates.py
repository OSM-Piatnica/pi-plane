# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The date rule of a milestone: a point in the schedule, so its start date always equals its finish date.

A work item whose type is of the `milestone` kind lasts one day. When a request sends only one of the two dates, the
other follows it; when it sends both, the finish date decides (it is where the timeline draws the diamond), and a
cleared finish with a start sent leaves the start. A duration that is sent is dropped: the dates decide it (1). A
work item that becomes a milestone is collapsed onto its finish date (else its start date).

The due date (`target_date`) is never read or written here: it stays the milestone's deadline.
"""

from django.core.exceptions import ValidationError

from plane.db.models import IssueType, IssueTypeKind


def is_milestone_type(issue_type) -> bool:
    return issue_type is not None and getattr(issue_type, "kind", None) == IssueTypeKind.MILESTONE


def apply_milestone_dates(instance, payload, issue_type) -> None:
    """Make `payload` (a serializer's attrs or a date update) keep a milestone at one day; changes it in place.

    `issue_type` is the type the work item ends up with. Nothing happens for any other kind.
    """

    if not is_milestone_type(issue_type):
        return

    payload.pop("duration", None)
    start_in, finish_in = "start_date" in payload, "finish_date" in payload

    if finish_in:
        day = payload["finish_date"] if payload["finish_date"] is not None else payload.get("start_date")
    elif start_in:
        day = payload["start_date"]
    else:
        # Only the type changes (or neither date was sent): collapse the dates the work item already has
        current_type_id = getattr(instance, "type_id", None)
        if instance is None or current_type_id == getattr(issue_type, "id", None):
            return
        start, finish = getattr(instance, "start_date", None), getattr(instance, "finish_date", None)
        if start == finish:
            return
        day = finish if finish is not None else start

    payload["start_date"] = day
    payload["finish_date"] = day


def milestone_payload_for_logging(instance, data) -> dict:
    """A copy of a raw request body with the milestone rule applied, so the activity feed reports both dates."""

    # `data[key]`: a QueryDict gives the last value, as the serializer reads it
    payload = {key: data[key] for key in data}
    if "type_id" in payload:
        try:
            issue_type = IssueType.objects.filter(pk=payload["type_id"]).first() if payload["type_id"] else None
        except (ValueError, ValidationError):
            # Not an id: the serializer refuses the request
            return payload
    else:
        issue_type = getattr(instance, "type", None)
    apply_milestone_dates(instance, payload, issue_type)
    return payload

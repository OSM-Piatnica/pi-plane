# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Single backend rule for a work item's planning dates. Creation, details, grid, bulk edits,
imports and integrations all go through `resolve_work_item_dates`.

Field meanings
  start_date   current planned first day of work
  finish_date  current planned / forecast last day of work (schedule endpoint)
  target_date  the due date: a deadline or commitment. The name is kept for API compatibility.
  completed_at actual completion timestamp

All three planning dates are nullable and independent. The only relationship is the schedule
invariant `start_date <= finish_date`. Due is never compared with start or finish.

Initial equality rule
  The first time a user manually enters either finish or due, the other one may be defaulted to
  the same date, once. The interactive client asks for this with `initialize_paired_date`; the
  server decides whether it is allowed. After that, `dates_initialized` stays set for good, even
  if both dates are cleared. API and import callers that do not send the flag never get copying.
"""

from dataclasses import dataclass, field

from plane.utils.work_item_duration import (
    DURATION_DATE_FIELDS,
    reconcile_work_item_duration,
    to_work_item_date,
)

# Write-only request key used by the interactive client to request the one-time default.
INITIALIZE_PAIRED_DATE_KEY = "initialize_paired_date"
# Write-only: a creation form shows both values before saving, so it sends both and names the one it
# copied from the other. The server verifies eligibility and records the provenance.
PAIRED_DATE_DEFAULTED_KEY = "paired_date_defaulted"

ORIGIN_MANUAL = "manual"
ORIGIN_DEFAULTED = "defaulted"
ORIGIN_MIGRATED = "migrated"

FINISH_BEFORE_START_MESSAGE = "Finish must be on or after start."

NOTICE_DUE_DEFAULTED = "due_date_defaulted"
NOTICE_FINISH_DEFAULTED = "finish_date_defaulted"
NOTICE_FINISH_NOT_DEFAULTED = "finish_date_not_defaulted"


class WorkItemDateError(ValueError):
    """The requested dates break the schedule invariant. Nothing must be saved."""


@dataclass
class DateResolution:
    """
    :param fields: values to merge into the payload before it is saved. Dates are ISO strings so
        the same dict can be written into activity payloads; `to_model_values` converts them.
    :param notices: machine readable explanations for the client, e.g. a defaulted due date
    """

    fields: dict = field(default_factory=dict)
    notices: list = field(default_factory=list)

    def to_model_values(self):
        values = {}
        for key, value in self.fields.items():
            if key in DURATION_DATE_FIELDS or key == "target_date":
                values[key] = to_work_item_date(value)
            else:
                values[key] = value
        return values


def validate_schedule(start_date, finish_date):
    """Raise when both schedule endpoints exist and finish is before start."""
    start = to_work_item_date(start_date)
    finish = to_work_item_date(finish_date)
    if start is not None and finish is not None and finish < start:
        raise WorkItemDateError(FINISH_BEFORE_START_MESSAGE)


def _current(instance, name):
    return to_work_item_date(getattr(instance, name, None)) if instance is not None else None


def _initialization_fields(instance, payload):
    """
    Work out the one-time default and the provenance bookkeeping for this payload.

    Returns (fields, notices). Never raises.
    """
    finish_in = "finish_date" in payload
    due_in = "target_date" in payload
    if not finish_in and not due_in:
        # Start-only (or duration-only) edits do not consume the opportunity.
        return {}, []

    fields = {"dates_initialized": True}
    notices = []

    if finish_in:
        fields["finish_date_origin"] = ORIGIN_MANUAL if payload.get("finish_date") else None
    if due_in:
        fields["target_date_origin"] = ORIGIN_MANUAL if payload.get("target_date") else None

    already_consumed = instance is not None and bool(getattr(instance, "dates_initialized", False))
    requested = bool(payload.get(INITIALIZE_PAIRED_DATE_KEY))

    # A form that already shows both values: no copying here, only provenance for the copied one.
    copied = payload.get(PAIRED_DATE_DEFAULTED_KEY)
    if finish_in and due_in and copied in ("finish_date", "target_date") and not already_consumed:
        finish = to_work_item_date(payload.get("finish_date"))
        due = to_work_item_date(payload.get("target_date"))
        if finish is not None and finish == due:
            origin_key = "finish_date_origin" if copied == "finish_date" else "target_date_origin"
            code = NOTICE_FINISH_DEFAULTED if copied == "finish_date" else NOTICE_DUE_DEFAULTED
            fields[origin_key] = ORIGIN_DEFAULTED
            notices.append({"code": code, "date": finish.isoformat()})
        return fields, notices

    # Supplying both fields (including an explicit null) bypasses copying.
    if already_consumed or not requested or (finish_in and due_in):
        return fields, notices

    if finish_in:
        supplied = to_work_item_date(payload.get("finish_date"))
        if supplied is not None and _current(instance, "target_date") is None:
            fields["target_date"] = supplied.isoformat()
            fields["target_date_origin"] = ORIGIN_DEFAULTED
            notices.append({"code": NOTICE_DUE_DEFAULTED, "date": supplied.isoformat()})
    else:
        supplied = to_work_item_date(payload.get("target_date"))
        if supplied is not None and _current(instance, "finish_date") is None:
            start = payload["start_date"] if "start_date" in payload else getattr(instance, "start_date", None)
            start = to_work_item_date(start)
            if start is not None and supplied < start:
                # A copy would manufacture an invalid schedule. Keep the deadline alone.
                notices.append({"code": NOTICE_FINISH_NOT_DEFAULTED, "date": supplied.isoformat()})
            else:
                fields["finish_date"] = supplied.isoformat()
                fields["finish_date_origin"] = ORIGIN_DEFAULTED
                notices.append({"code": NOTICE_FINISH_DEFAULTED, "date": supplied.isoformat()})

    return fields, notices


def resolve_work_item_dates(instance, payload, weekend_days=()):
    """
    Apply every date rule to one create/update payload.

    :param instance: the stored work item, or None on creation
    :param payload: incoming data; key presence signals intent, a key holding None means "clear"
    :param weekend_days: the project's non-working days (0 = Sunday ... 6 = Saturday); the duration counts working days
    :return: DateResolution with the derived fields to merge over the payload
    :raises WorkItemDateError: the schedule would end before it starts
    """
    if payload is None:
        return DateResolution()

    init_fields, notices = _initialization_fields(instance, payload)
    merged = {**payload, **init_fields}
    derived = reconcile_work_item_duration(instance, merged, weekend_days)

    # `fields` holds only what the rules changed or derived; the caller's own keys stay theirs.
    fields = {**init_fields, **derived}
    final = {**merged, **fields}

    start = final["start_date"] if "start_date" in final else getattr(instance, "start_date", None)
    finish = final["finish_date"] if "finish_date" in final else getattr(instance, "finish_date", None)
    validate_schedule(start, finish)

    return DateResolution(fields=fields, notices=notices)


def resolve_for_logging(instance, payload, weekend_days=()):
    """
    Same as `resolve_work_item_dates` but never raises, for activity logging of a payload the
    serializer will reject (or has rejected) anyway.
    """
    try:
        return resolve_work_item_dates(instance, payload, weekend_days).fields
    except WorkItemDateError:
        return {}


# --- Date status -------------------------------------------------------------------------------


def date_statuses(*, finish_date, due_date, today, is_active, completed_on=None, due_at_completion=None):
    """
    Derive the independent date-only statuses. `today` and `completed_on` are dates in the project
    time zone (workspace time zone as fallback); the caller converts, this function never reads a
    clock.

    :param is_active: the item is not completed or cancelled
    :param completed_on: project-local date the item was completed on, if it was
    :param due_at_completion: the due date that applied when it was completed
    :return: dict of booleans
    """
    finish = to_work_item_date(finish_date)
    due = to_work_item_date(due_date)
    today = to_work_item_date(today)
    completed = to_work_item_date(completed_on)
    due_then = to_work_item_date(due_at_completion)

    return {
        # The due day itself is not overdue until it ends.
        "overdue": bool(is_active and due is not None and today > due),
        "forecast_misses_deadline": bool(is_active and finish is not None and due is not None and finish > due),
        "forecast_unknown": bool(is_active and due is not None and finish is None),
        # A schedule warning only, never deadline overdue.
        "planned_finish_passed": bool(is_active and finish is not None and finish < today),
        "completed_late": bool(completed is not None and due_then is not None and completed > due_then),
    }


# --- Serializer glue ---------------------------------------------------------------------------


def apply_date_rules(instance, attrs, weekend_days=()):
    """
    Run the date rules inside a DRF serializer's `validate` and merge the result into `attrs`.

    Pops the write-only `initialize_paired_date` flag so it never reaches the model. Returns the
    notices for the caller to expose; `weekend_days` are the project's non-working days. Raises
    `serializers.ValidationError` when the schedule is invalid.
    """
    from rest_framework import serializers

    try:
        resolution = resolve_work_item_dates(instance, attrs, weekend_days)
    except WorkItemDateError:
        # The only failure is the finish-before-start invariant, so report the fixed message rather
        # than anything derived from the exception.
        raise serializers.ValidationError({"finish_date": [FINISH_BEFORE_START_MESSAGE]})

    attrs.update(resolution.to_model_values())
    attrs.pop(INITIALIZE_PAIRED_DATE_KEY, None)
    attrs.pop(PAIRED_DATE_DEFAULTED_KEY, None)
    return resolution.notices

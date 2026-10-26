# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Work item duration is measured in whole working days, inclusive of both the start and the target date.
A work item that starts and ends on the same day lasts 1 day, so the shortest valid duration is 1.

The project's weekend days (0 = Sunday ... 6 = Saturday, see ``plane.utils.weekend_days``) are not counted:
  * a range's duration is the number of working days in it, but at least 1, so a range made only of weekend
    days still lasts 1 day;
  * the target date of a duration is its Nth working day on or after the start date, and the start date is its
    Nth working day on or before the target date, so a start or target that falls on a weekend day counts from
    the nearest working day;
  * holidays are not modelled, only the weekly pattern.
Every function takes ``weekend_days``; without it no day is skipped.

This module mirrors `packages/utils/src/work-item/duration.ts`. The web app derives the same values
optimistically because `PATCH` on a work item answers with `204 No Content`, so both sides have to
agree. Keep the two implementations in sync.
"""

import math
from datetime import date, datetime, timedelta

WORK_ITEM_DURATION_MIN = 1

DURATION_DATE_FIELDS = ("start_date", "target_date")


def to_work_item_date(value):
    """
    Parse a date coming from a model instance or a JSON payload.

    Callers that hand the reconciled values to a serializer rather than to a raw request payload
    need this to turn the returned ISO strings back into `date` objects.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    raise TypeError(f"Unsupported date value: {type(value)!r}")


def _off_days(weekend_days):
    """The weekend days as a set; a week with no working day is treated as one without weekend, never as a trap."""
    off = {int(day) for day in (weekend_days or ()) if 0 <= int(day) <= 6}
    return off if len(off) < 7 else set()


def _weekday(day):
    """The day of the week numbered like the weekend days: 0 is Sunday (``date.weekday()`` has Monday as 0)."""
    return (day.weekday() + 1) % 7


def count_working_days(start, target, weekend_days=()):
    """Working days from ``start`` to ``target``, both included; 0 when the range is backwards."""
    off = _off_days(weekend_days)
    total = (target - start).days + 1
    if total <= 0:
        return 0
    full_weeks, extra = divmod(total, 7)
    count = full_weeks * (7 - len(off))
    first_extra = start + timedelta(days=full_weeks * 7)
    return count + sum(1 for offset in range(extra) if _weekday(first_extra + timedelta(days=offset)) not in off)


def add_working_days(start, count, weekend_days=()):
    """The ``count``th working day on or after ``start`` (``count`` is at least 1)."""
    off = _off_days(weekend_days)
    day = start
    while _weekday(day) in off:
        day += timedelta(days=1)
    weeks, remaining = divmod(count - 1, 7 - len(off))
    day += timedelta(days=weeks * 7)
    while remaining > 0:
        day += timedelta(days=1)
        if _weekday(day) not in off:
            remaining -= 1
    return day


def subtract_working_days(target, count, weekend_days=()):
    """The ``count``th working day on or before ``target`` (``count`` is at least 1)."""
    off = _off_days(weekend_days)
    day = target
    while _weekday(day) in off:
        day -= timedelta(days=1)
    weeks, remaining = divmod(count - 1, 7 - len(off))
    day -= timedelta(days=weeks * 7)
    while remaining > 0:
        day -= timedelta(days=1)
        if _weekday(day) not in off:
            remaining -= 1
    return day


def normalize_work_item_duration(value):
    """Coerce any user or API supplied duration into a valid stored value."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    # floor(x + 0.5) matches JavaScript's Math.round, unlike Python's banker's rounding
    rounded = int(math.floor(parsed + 0.5))
    return max(rounded, WORK_ITEM_DURATION_MIN)


def calculate_work_item_duration(start_date, target_date, weekend_days=()):
    """
    Derive the duration in working days from a date range, counting both ends.

    Returns None when either date is missing. The result may be <= 0 when the dates are ordered
    incorrectly, which lets callers detect an invalid range; a range in the right order lasts at least 1 day.
    """
    start = to_work_item_date(start_date)
    target = to_work_item_date(target_date)
    if start is None or target is None:
        return None
    if target < start:
        return (target - start).days + 1
    return max(count_working_days(start, target, weekend_days), WORK_ITEM_DURATION_MIN)


def calculate_target_date_from_duration(start_date, duration, weekend_days=()):
    """Derive the target date by treating the start date as the anchor."""
    start = to_work_item_date(start_date)
    normalized = normalize_work_item_duration(duration)
    if start is None or normalized is None:
        return None
    return add_working_days(start, normalized, weekend_days).isoformat()


def calculate_start_date_from_duration(target_date, duration, weekend_days=()):
    """Derive the start date by treating the target date as the anchor."""
    target = to_work_item_date(target_date)
    normalized = normalize_work_item_duration(duration)
    if target is None or normalized is None:
        return None
    return subtract_working_days(target, normalized, weekend_days).isoformat()


def reconcile_work_item_duration(instance, payload, weekend_days=()):
    """
    Keep `duration`, `start_date` and `target_date` consistent after a single edit.

    Rules, in the order they are applied:
      - Editing ``duration``
          * cleared            -> dates are left untouched
          * start date present -> start date is the anchor, target date is recalculated
          * only target date   -> target date is the anchor, start date is recalculated
          * no dates at all    -> duration is stored on its own
      - Editing ``start_date`` / ``target_date``
          * both dates present -> duration is recalculated from the range
          * both dates present but ordered backwards -> the existing length is preserved and the
            date the caller did not touch is shifted, so the payload stays valid
          * only one date left and a duration exists -> the still empty date is derived from the
            duration, but a date the caller explicitly cleared is never resurrected
          * both dates cleared -> duration survives as a standalone estimate

    :param instance: the work item before the edit, or None when creating one
    :param payload: the incoming request data; presence of a key signals intent, including None
    :param weekend_days: the project's non-working days, 0 = Sunday ... 6 = Saturday
    :return: dict of fields to overwrite in the payload, containing only the derived values
    """
    if payload is None:
        return {}

    current_start = to_work_item_date(getattr(instance, "start_date", None))
    current_target = to_work_item_date(getattr(instance, "target_date", None))
    current_duration = getattr(instance, "duration", None)

    start_date_changed = "start_date" in payload
    target_date_changed = "target_date" in payload

    start_date = to_work_item_date(payload.get("start_date")) if start_date_changed else current_start
    target_date = to_work_item_date(payload.get("target_date")) if target_date_changed else current_target

    result = {}

    # Duration driven: the caller sent a duration, so the dates follow it.
    if "duration" in payload:
        duration = normalize_work_item_duration(payload.get("duration"))
        result["duration"] = duration
        if duration is None:
            return result

        if start_date:
            result["target_date"] = calculate_target_date_from_duration(start_date, duration, weekend_days)
        elif target_date:
            result["start_date"] = calculate_start_date_from_duration(target_date, duration, weekend_days)
        return result

    if not start_date_changed and not target_date_changed:
        return result

    # Date driven: the caller sent a date, so the duration follows the dates.
    if start_date and target_date:
        next_duration = calculate_work_item_duration(start_date, target_date, weekend_days)

        if next_duration is not None and next_duration >= WORK_ITEM_DURATION_MIN:
            result["duration"] = next_duration
            return result

        # The new range is ordered backwards. Keep the length the work item already had and move the
        # opposite end instead, so a slipped start date drags the target date along with it.
        previous_duration = (
            normalize_work_item_duration(current_duration)
            or normalize_work_item_duration(calculate_work_item_duration(current_start, current_target, weekend_days))
            or WORK_ITEM_DURATION_MIN
        )

        result["duration"] = previous_duration
        if start_date_changed:
            result["target_date"] = calculate_target_date_from_duration(start_date, previous_duration, weekend_days)
        else:
            result["start_date"] = calculate_start_date_from_duration(target_date, previous_duration, weekend_days)
        return result

    duration = normalize_work_item_duration(current_duration)
    if duration is None:
        return result

    # Only fill in a date that is still empty and that the caller did not just clear.
    if start_date and not target_date and not target_date_changed:
        result["target_date"] = calculate_target_date_from_duration(start_date, duration, weekend_days)
    elif target_date and not start_date and not start_date_changed:
        result["start_date"] = calculate_start_date_from_duration(target_date, duration, weekend_days)

    return result

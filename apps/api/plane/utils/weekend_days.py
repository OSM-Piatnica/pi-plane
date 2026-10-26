# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The days of the week that count as non-working time.

Days are numbered like ``start_of_the_week``: 0 is Sunday, 6 is Saturday. A workspace has a list, a new project copies
it, and a person can have a list of their own (``None`` follows the workspace). At least one day has to stay a working
day, otherwise nothing could be scheduled.
"""

from django.core.exceptions import ValidationError

DEFAULT_WEEKEND_DAYS = (6, 0)


def default_weekend_days():
    """A fresh list each time, as a model default must not share one object between rows."""
    return [0, 6]


def validate_weekend_days(value):
    if value is None:
        return
    if not isinstance(value, list) or not all(isinstance(day, int) and not isinstance(day, bool) for day in value):
        raise ValidationError("Weekend days must be a list of day numbers, 0 (Sunday) to 6 (Saturday).")
    if any(day < 0 or day > 6 for day in value):
        raise ValidationError("Weekend days must be between 0 (Sunday) and 6 (Saturday).")
    if len(set(value)) != len(value):
        raise ValidationError("Weekend days must not repeat a day.")
    if len(value) > 6:
        raise ValidationError("At least one day of the week has to be a working day.")


def normalize_weekend_days(value):
    """The days sorted, for storing; ``None`` stays ``None``."""
    return None if value is None else sorted(value)

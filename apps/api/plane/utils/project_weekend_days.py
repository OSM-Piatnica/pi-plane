# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Reading a project's weekend days where only its id is at hand (serializers, views, background tasks)."""

from plane.utils.weekend_days import default_weekend_days


def get_project_weekend_days(project_id):
    """The project's non-working days; Saturday and Sunday when there is no such project."""
    from plane.db.models import Project

    if not project_id:
        return default_weekend_days()
    days = Project.objects.filter(pk=project_id).values_list("weekend_days", flat=True).first()
    return default_weekend_days() if days is None else days

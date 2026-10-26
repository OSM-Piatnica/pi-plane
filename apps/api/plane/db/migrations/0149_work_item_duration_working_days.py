# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations

from plane.utils.work_item_duration import WORK_ITEM_DURATION_MIN, calculate_work_item_duration

BATCH_SIZE = 1000


def count_working_days_only(apps, schema_editor):
    """Durations used to count every calendar day; they count working days now, so the stored ones are recalculated
    from the dates with each project's own weekend days (Saturday and Sunday for every project that exists)."""
    Project = apps.get_model("db", "Project")
    Issue = apps.get_model("db", "Issue")
    # `_base_manager`: a historical model has none of the custom managers the live one declares
    for project in Project._base_manager.all().only("id", "weekend_days").iterator():
        batch = []
        issues = Issue._base_manager.filter(
            project_id=project.id, deleted_at__isnull=True, start_date__isnull=False, target_date__isnull=False
        ).only("id", "start_date", "target_date", "duration")
        for issue in issues.iterator(chunk_size=BATCH_SIZE):
            duration = calculate_work_item_duration(issue.start_date, issue.target_date, project.weekend_days)
            if duration is None or duration < WORK_ITEM_DURATION_MIN or duration == issue.duration:
                continue
            issue.duration = duration
            batch.append(issue)
            if len(batch) >= BATCH_SIZE:
                Issue._base_manager.bulk_update(batch, ["duration"])
                batch = []
        if batch:
            Issue._base_manager.bulk_update(batch, ["duration"])


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0148_weekend_days"),
    ]

    operations = [
        # Counting calendar days again would need the weekend days at the time; the dates are untouched either way
        migrations.RunPython(count_working_days_only, migrations.RunPython.noop),
    ]

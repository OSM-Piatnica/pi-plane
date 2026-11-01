# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models

DAYS = [(0, "Sunday"), (1, "Monday"), (2, "Tuesday"), (3, "Wednesday"), (4, "Thursday"), (5, "Friday"), (6, "Saturday")]


class Migration(migrations.Migration):
    """
    A new workspace and a new project start their week on Monday. Only the default changes: the first day of
    every existing workspace and project stays as it is (set it in the workspace or project settings).
    """

    dependencies = [
        ("db", "0154_issue_finish_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workspace",
            name="start_of_the_week",
            field=models.PositiveSmallIntegerField(choices=DAYS, default=1),
        ),
        migrations.AlterField(
            model_name="project",
            name="start_of_the_week",
            field=models.PositiveSmallIntegerField(choices=DAYS, default=1),
        ),
    ]

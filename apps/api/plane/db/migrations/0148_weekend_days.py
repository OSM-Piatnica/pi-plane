# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models

import plane.utils.weekend_days


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0147_start_of_the_week_workspace_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="weekend_days",
            field=models.JSONField(
                default=plane.utils.weekend_days.default_weekend_days,
                validators=[plane.utils.weekend_days.validate_weekend_days],
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="weekend_days",
            field=models.JSONField(
                default=plane.utils.weekend_days.default_weekend_days,
                validators=[plane.utils.weekend_days.validate_weekend_days],
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="weekend_days",
            field=models.JSONField(
                blank=True,
                default=None,
                null=True,
                validators=[plane.utils.weekend_days.validate_weekend_days],
            ),
        ),
    ]

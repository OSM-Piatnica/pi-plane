# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0144_project_blocked_status_rule"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_assignee_edit_rule_enabled",
            field=models.BooleanField(default=False),
        ),
    ]

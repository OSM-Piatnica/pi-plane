# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0149_work_item_duration_working_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="workspace_admin_message",
            field=models.BooleanField(default=True),
        ),
    ]

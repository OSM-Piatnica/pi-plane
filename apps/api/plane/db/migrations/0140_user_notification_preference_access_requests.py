# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0139_project_copy_job"),
    ]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="project_access_request",
            field=models.BooleanField(default=True),
        ),
    ]

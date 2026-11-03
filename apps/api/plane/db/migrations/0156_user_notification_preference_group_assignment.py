# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0155_start_of_the_week_default_monday"),
    ]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="group_assignment",
            field=models.BooleanField(default=False),
        ),
    ]

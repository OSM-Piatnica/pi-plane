# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0136_project_visibility_tiers"),
    ]
    operations = [
        migrations.AlterField(
            model_name="usernotificationpreference",
            name="property_change",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="usernotificationpreference",
            name="state_change",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="usernotificationpreference",
            name="email_frequency",
            field=models.CharField(
                choices=[("instant", "Instant"), ("hourly", "Hourly digest"), ("daily", "Daily digest")],
                default="instant",
                max_length=10,
            ),
        ),
    ]

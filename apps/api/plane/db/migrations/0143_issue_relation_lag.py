# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0142_issue_relation_unique_per_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="issuerelation",
            name="lag_days",
            field=models.IntegerField(default=0),
        ),
    ]

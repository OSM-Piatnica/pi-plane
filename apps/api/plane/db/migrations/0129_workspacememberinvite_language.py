# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026 Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0128_issue_duration"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspacememberinvite",
            name="language",
            field=models.CharField(default="en", max_length=10),
        ),
    ]

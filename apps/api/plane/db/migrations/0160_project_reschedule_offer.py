# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    # Numbered 0160 because 0157 to 0159 are taken by pull requests that merge first; when this is rebased, point
    # the dependency at the then-latest migration.
    dependencies = [
        ("db", "0159_initiatives"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_reschedule_offer_enabled",
            field=models.BooleanField(default=True),
        ),
    ]

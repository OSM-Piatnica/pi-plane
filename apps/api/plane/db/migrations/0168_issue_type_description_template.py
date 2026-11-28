# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Work item type description templates (A3 of the roadmap).

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0167_project_document_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="issuetype",
            name="description_template",
            field=models.TextField(blank=True, null=True),
        ),
    ]

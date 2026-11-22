# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


def set_kind_from_is_epic(apps, schema_editor):
    """Existing Epic types get the Epic kind; every other type keeps the default. Soft-deleted rows included."""

    IssueType = apps.get_model("db", "IssueType")
    IssueType._base_manager.filter(is_epic=True).update(kind="epic")


def keep_is_epic(apps, schema_editor):
    """Going back drops `kind`; `is_epic` already holds what the Epic kind said."""


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0157_departments"),
    ]

    operations = [
        migrations.AddField(
            model_name="issuetype",
            name="kind",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("epic", "Epic"),
                    ("milestone", "Milestone"),
                    ("approval", "Approval"),
                    ("review", "Review"),
                ],
                db_index=True,
                default="standard",
                max_length=20,
            ),
        ),
        migrations.RunPython(set_kind_from_is_epic, keep_is_epic),
        migrations.AddConstraint(
            model_name="issuetype",
            constraint=models.CheckConstraint(
                condition=models.Q(("is_epic", True), ("kind", "epic"))
                | (models.Q(("is_epic", False)) & ~models.Q(("kind", "epic"))),
                name="issue_type_is_epic_matches_kind",
            ),
        ),
    ]

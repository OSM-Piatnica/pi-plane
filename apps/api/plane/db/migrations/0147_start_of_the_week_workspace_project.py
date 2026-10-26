# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models

DAYS = [(0, "Sunday"), (1, "Monday"), (2, "Tuesday"), (3, "Wednesday"), (4, "Thursday"), (5, "Friday"), (6, "Saturday")]


def follow_the_default(apps, schema_editor):
    """Sunday was the default for every profile, so it cannot be told apart from a choice: those people now follow
    the project's setting, which is Sunday until someone changes it. Any other day was picked on purpose and stays."""
    Profile = apps.get_model("db", "Profile")
    Profile.objects.filter(start_of_the_week=0).update(start_of_the_week=None)


def back_to_sunday(apps, schema_editor):
    Profile = apps.get_model("db", "Profile")
    Profile.objects.filter(start_of_the_week__isnull=True).update(start_of_the_week=0)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0146_project_relation_type_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="start_of_the_week",
            field=models.PositiveSmallIntegerField(choices=DAYS, default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="start_of_the_week",
            field=models.PositiveSmallIntegerField(choices=DAYS, default=0),
        ),
        migrations.AlterField(
            model_name="profile",
            name="start_of_the_week",
            field=models.PositiveSmallIntegerField(blank=True, choices=DAYS, default=None, null=True),
        ),
        migrations.RunPython(follow_the_default, back_to_sunday),
    ]

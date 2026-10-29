# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models

SCHEDULE_TYPES = ("start_before", "finish_before", "start_before_finish")
TRACEABILITY_TYPES = ("implemented_by", "caused_by", "cloned_by", "tested_by")


def enable_groups_in_use(apps, schema_editor):
    """The new default is off for these groups; keep them on where the project already has such relations."""
    Project = apps.get_model("db", "Project")
    IssueRelation = apps.get_model("db", "IssueRelation")
    for flag, types in (
        ("is_relation_schedule_enabled", SCHEDULE_TYPES),
        ("is_relation_traceability_enabled", TRACEABILITY_TYPES),
    ):
        project_ids = (
            IssueRelation.objects.filter(relation_type__in=types, deleted_at__isnull=True)
            .values_list("project_id", flat=True)
            .distinct()
        )
        Project.objects.filter(id__in=list(project_ids)).update(**{flag: True})


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0145_project_assignee_edit_rule"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_relation_schedule_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="project",
            name="is_relation_traceability_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="project",
            name="is_relation_relates_to_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="project",
            name="is_relation_duplicate_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(enable_groups_in_use, migrations.RunPython.noop),
    ]

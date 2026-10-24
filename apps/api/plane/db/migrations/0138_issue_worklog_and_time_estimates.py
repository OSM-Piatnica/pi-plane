# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0137_notification_preference_quieter_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="estimate",
            name="type",
            field=models.CharField(
                choices=[("categories", "Categories"), ("points", "Points"), ("time", "Time")],
                default="categories",
                max_length=255,
            ),
        ),
        migrations.CreateModel(
            name="IssueWorkLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "duration",
                    models.PositiveIntegerField(
                        help_text="Logged time in minutes",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(1440),
                        ],
                    ),
                ),
                ("description", models.TextField(blank=True, max_length=5000)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="worklogs", to="db.issue"
                    ),
                ),
                (
                    "logged_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="worklogs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workspace_%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Issue Work Log",
                "verbose_name_plural": "Issue Work Logs",
                "db_table": "issue_worklogs",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(fields=["issue"], name="issue_workl_issue_i_dfe2f9_idx"),
                    models.Index(fields=["project", "logged_by"], name="issue_workl_project_194538_idx"),
                    models.Index(fields=["workspace", "created_at"], name="issue_workl_workspa_07d0ac_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("duration__gte", 1), ("duration__lte", 1440)),
                        name="issue_worklog_duration_range",
                    )
                ],
            },
        ),
    ]

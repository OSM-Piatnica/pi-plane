# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Numbered 0163 because 0162 was reserved for the baselines change (#539), which was renumbered to
# 0164_project_baselines and depends on this migration. 0162 is intentionally unused.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0161_workspace_features_default_app"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_raci_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="IssueRaci",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("responsible", "Responsible"),
                            ("approver", "Approver"),
                            ("consulted", "Consulted"),
                            ("informed", "Informed"),
                        ],
                        max_length=20,
                    ),
                ),
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
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="issue_raci", to="db.usergroup"
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="issue_raci", to="db.issue"
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="project_%(class)s", to="db.project"
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
                "verbose_name": "Issue RACI",
                "verbose_name_plural": "Issue RACI",
                "db_table": "issue_raci",
                "ordering": ("-created_at",),
                "indexes": [models.Index(fields=["group", "role"], name="issue_raci_group_role_idx")],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("deleted_at__isnull", True)),
                        fields=("issue", "group"),
                        name="issue_raci_unique_issue_group_when_deleted_at_null",
                    )
                ],
            },
        ),
    ]

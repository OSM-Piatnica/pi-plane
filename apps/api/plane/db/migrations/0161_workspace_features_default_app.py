# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0156_user_notification_preference_group_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspaceuserproperties",
            name="default_app",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.CreateModel(
            name="WorkspaceFeature",
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
                ("key", models.CharField(max_length=50)),
                ("is_enabled", models.BooleanField(default=False)),
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
                        related_name="workspace_features",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Workspace Feature",
                "verbose_name_plural": "Workspace Features",
                "db_table": "workspace_features",
                "ordering": ("-created_at",),
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("deleted_at__isnull", True)),
                        fields=("workspace", "key"),
                        name="workspace_feature_unique_workspace_key_when_deleted_at_null",
                    )
                ],
                "unique_together": {("workspace", "key", "deleted_at")},
            },
        ),
    ]

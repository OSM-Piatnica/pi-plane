# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0156_user_notification_preference_group_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="usergroup",
            name="kind",
            field=models.CharField(
                choices=[("group", "Group"), ("department", "Department")], default="group", max_length=20
            ),
        ),
        migrations.AddField(
            model_name="usergroup",
            name="code",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="usergroup",
            name="color",
            field=models.CharField(blank=True, default="", max_length=9),
        ),
        migrations.AddField(
            model_name="usergroup",
            name="sort_order",
            field=models.FloatField(default=65535),
        ),
        migrations.AddField(
            model_name="usergroup",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddConstraint(
            model_name="usergroup",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("deleted_at__isnull", True), ("kind", "department"), models.Q(("code", ""), _negated=True)
                ),
                fields=("workspace", "code"),
                name="user_group_unique_department_code_when_deleted_at_null",
            ),
        ),
        migrations.AddField(
            model_name="usergroupmember",
            name="via_department",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="workspacemember",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="department_members",
                to="db.usergroup",
            ),
        ),
    ]

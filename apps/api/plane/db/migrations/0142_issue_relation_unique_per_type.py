# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Two work items can be related in several ways at once, as long as each type is used once."""

    dependencies = [
        ("db", "0141_user_notification_preference_access_requests"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="issuerelation",
            name="issue_relation_unique_issue_related_issue_when_deleted_at_null",
        ),
        migrations.AlterUniqueTogether(
            name="issuerelation",
            unique_together={("issue", "related_issue", "relation_type", "deleted_at")},
        ),
        migrations.AddConstraint(
            model_name="issuerelation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("issue", "related_issue", "relation_type"),
                name="issue_relation_unique_issue_related_issue_type_when_deleted_at_null",
            ),
        ),
    ]

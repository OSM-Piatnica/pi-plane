# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from django.db import migrations, models

logger = logging.getLogger("plane.migrations")


def backfill_finish_date(apps, schema_editor):
    """
    Split the legacy end date into a planned finish and a due date.

    Until now `target_date` was both the end of the timeline bar and the deadline. It stays the due
    date, and every work item whose schedule it ended gets the same value as its finish date so the
    displayed schedule does not change. The copy is marked `migrated`.

    Safe to rerun: only rows without a finish date are touched. Rows whose legacy range is
    backwards (start after target) are left alone for explicit review; neither their start nor
    their due date is moved. They can be found with
    `start_date > target_date AND finish_date IS NULL`.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE issues
            SET finish_date = target_date,
                finish_date_origin = 'migrated'
            WHERE target_date IS NOT NULL
              AND finish_date IS NULL
              AND (start_date IS NULL OR start_date <= target_date)
            """
        )
        copied = cursor.rowcount

        cursor.execute(
            "SELECT COUNT(*) FROM issues "
            "WHERE target_date IS NOT NULL AND finish_date IS NULL AND start_date > target_date"
        )
        incompatible = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM issues WHERE target_date IS NOT NULL")
        retained = cursor.fetchone()[0]

        # Finish dates of drafts are copied the same way so publishing a draft keeps its schedule.
        cursor.execute(
            """
            UPDATE draft_issues
            SET finish_date = target_date,
                finish_date_origin = 'migrated'
            WHERE target_date IS NOT NULL
              AND finish_date IS NULL
              AND (start_date IS NULL OR start_date <= target_date)
            """
        )

        # The version history stores the finish date too; older versions keep what they had.
        cursor.execute(
            """
            UPDATE issue_versions
            SET finish_date = target_date
            WHERE target_date IS NOT NULL
              AND finish_date IS NULL
              AND (start_date IS NULL OR start_date <= target_date)
            """
        )

    logger.info(
        "finish_date migration: copied=%s retained_due=%s incompatible_for_review=%s",
        copied,
        retained,
        incompatible,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0152_user_notification_preference_workspace_admin_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="finish_date",
            field=models.DateField(blank=True, null=True),
        ),
        # Existing rows get `True`: their editing history is unknown, so the one-time initialization
        # must not fire for them. New rows default to `False` (see AlterField below).
        migrations.AddField(
            model_name="issue",
            name="dates_initialized",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="issue",
            name="dates_initialized",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="issue",
            name="finish_date_origin",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="issue",
            name="target_date_origin",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="issue",
            name="due_date_at_completion",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="draftissue",
            name="finish_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="draftissue",
            name="dates_initialized",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="draftissue",
            name="dates_initialized",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="draftissue",
            name="finish_date_origin",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="draftissue",
            name="target_date_origin",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="issueversion",
            name="finish_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_finish_date, migrations.RunPython.noop),
        # Completed items keep the deadline they were completed against.
        migrations.RunSQL(
            """
            UPDATE issues i
            SET due_date_at_completion = i.target_date
            FROM states s
            WHERE s.id = i.state_id AND s."group" = 'completed'
              AND i.due_date_at_completion IS NULL AND i.target_date IS NOT NULL
            """,
            migrations.RunSQL.noop,
        ),
    ]

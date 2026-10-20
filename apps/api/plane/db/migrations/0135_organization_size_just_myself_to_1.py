# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations

OLD_VALUE = "Just myself"
NEW_VALUE = "1"


def just_myself_to_one(apps, schema_editor):
    """Store the solo company size as the language-neutral "1" instead of the English "Just myself".

    Soft-deleted workspaces are updated too, so a restored one does not keep the old value.
    """
    apps.get_model("db", "Workspace")._base_manager.filter(organization_size=OLD_VALUE).update(
        organization_size=NEW_VALUE
    )


def one_to_just_myself(apps, schema_editor):
    apps.get_model("db", "Workspace")._base_manager.filter(organization_size=NEW_VALUE).update(
        organization_size=OLD_VALUE
    )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0134_reset_project_deploy_board_identity"),
    ]

    operations = [
        migrations.RunPython(just_myself_to_one, one_to_just_myself),
    ]

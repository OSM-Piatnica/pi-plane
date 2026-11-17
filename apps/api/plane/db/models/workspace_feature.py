# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel


class WorkspaceFeature(BaseModel):
    """One feature switch of a workspace. No row means the feature is off.

    The known keys and whether each is built are in ``plane.utils.workspace_features``; the key is not a choice
    field, so adding a feature needs no migration.
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="workspace_features")
    key = models.CharField(max_length=50)
    is_enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ["workspace", "key", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "key"],
                condition=models.Q(deleted_at__isnull=True),
                name="workspace_feature_unique_workspace_key_when_deleted_at_null",
            )
        ]
        verbose_name = "Workspace Feature"
        verbose_name_plural = "Workspace Features"
        db_table = "workspace_features"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.workspace.name} {self.key}"

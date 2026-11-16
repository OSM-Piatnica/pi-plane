# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Django imports
from django.db import models
from django.db.models import Q

# Module imports
from .project import ProjectBaseModel
from .base import BaseModel


class IssueTypeKind(models.TextChoices):
    """What the system does with a work item type. Set by code; the name, icon and properties are the user's."""

    STANDARD = "standard", "Standard"
    EPIC = "epic", "Epic"
    MILESTONE = "milestone", "Milestone"
    APPROVAL = "approval", "Approval"
    REVIEW = "review", "Review"


# Position of a kind in the hierarchy: a child's level is never above its parent's
ISSUE_TYPE_KIND_LEVELS = {
    IssueTypeKind.STANDARD: 0,
    IssueTypeKind.EPIC: 1,
    IssueTypeKind.MILESTONE: 0,
    IssueTypeKind.APPROVAL: 0,
    IssueTypeKind.REVIEW: -1,
}
# Kinds whose work items are created and moved by the system: a user cannot switch a work item into or out of them
SYSTEM_MANAGED_ISSUE_TYPE_KINDS = frozenset({IssueTypeKind.APPROVAL, IssueTypeKind.REVIEW})
# Kinds left out of the progress numbers of modules and cycles: an Epic is counted through its children, a review
# through its approval
PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS = frozenset({IssueTypeKind.EPIC, IssueTypeKind.REVIEW})


class IssueType(BaseModel):
    workspace = models.ForeignKey("db.Workspace", related_name="issue_types", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    logo_props = models.JSONField(default=dict)
    # Kept for upstream code and the public API; always equal to `kind == "epic"` (see `save` and the constraint)
    is_epic = models.BooleanField(default=False)
    kind = models.CharField(max_length=20, choices=IssueTypeKind.choices, default=IssueTypeKind.STANDARD, db_index=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    level = models.FloatField(default=0)
    external_source = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Issue Type"
        verbose_name_plural = "Issue Types"
        db_table = "issue_types"
        constraints = [
            models.CheckConstraint(
                condition=Q(is_epic=True, kind="epic") | (Q(is_epic=False) & ~Q(kind="epic")),
                name="issue_type_is_epic_matches_kind",
            )
        ]

    def __str__(self):
        return self.name

    def _remember_kind(self):
        # Remembered so that `save` can tell which of the two fields the caller changed
        if not {"kind", "is_epic"} & self.get_deferred_fields():
            self._loaded_kind = self.kind
            self._loaded_is_epic = self.is_epic

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._remember_kind()
        return instance

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)
        self._remember_kind()

    def sync_kind_and_is_epic(self):
        """Make `is_epic` and `kind` agree before a save.

        A changed `kind` decides. Otherwise `is_epic`, which upstream code and the type form write, moves the type
        between the standard and the Epic kind; it never changes a milestone, approval or review type.
        """

        epic, standard = IssueTypeKind.EPIC, IssueTypeKind.STANDARD
        if hasattr(self, "_loaded_kind"):
            kind_changed = self.kind != self._loaded_kind
            is_epic_changed = self.is_epic != self._loaded_is_epic
        else:
            # A new row, or one loaded without these fields: an explicit kind is anything but the default
            kind_changed = self.kind != standard
            is_epic_changed = not kind_changed
        if not kind_changed and is_epic_changed and self.kind in (epic, standard):
            self.kind = epic if self.is_epic else standard
        self.is_epic = self.kind == epic

    def save(self, *args, **kwargs):
        self.sync_kind_and_is_epic()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and {"kind", "is_epic"} & set(update_fields):
            kwargs["update_fields"] = list({*update_fields, "kind", "is_epic"})
        super().save(*args, **kwargs)
        self._remember_kind()


class ProjectIssueType(ProjectBaseModel):
    issue_type = models.ForeignKey("db.IssueType", related_name="project_issue_types", on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ["project", "issue_type", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "issue_type"],
                condition=Q(deleted_at__isnull=True),
                name="project_issue_type_unique_project_issue_type_when_deleted_at_null",
            )
        ]
        verbose_name = "Project Issue Type"
        verbose_name_plural = "Project Issue Types"
        db_table = "project_issue_types"
        ordering = ("project", "issue_type")

    def __str__(self):
        return f"{self.project} - {self.issue_type}"

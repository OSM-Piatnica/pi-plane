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
    # HTML that the create form puts into the description of a new work item of this type while it is empty
    description_template = models.TextField(blank=True, null=True)
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
        # The kind the database holds, remembered so that `save` can tell a kind the caller changed from one that
        # was only loaded. Called only right after the field was read from or written to the database: a value
        # the caller set in memory must never be taken for the stored one
        if "kind" in self.__dict__:
            self._loaded_kind = self.__dict__["kind"]

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "kind" in field_names:
            instance._remember_kind()
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        # Django also comes here to load one deferred field (`fields=[name]`), so only a reloaded kind counts
        if fields is None or "kind" in fields:
            self._remember_kind()

    def sync_kind_and_is_epic(self):
        """Make `is_epic` and `kind` agree before a save.

        A changed `kind` decides. Otherwise `is_epic`, which upstream code and the type form write, moves the type
        between the standard and the Epic kind; it never changes a milestone, approval or review type.

        Only the stored kind is remembered. The stored flag always matches it (the check constraint), so a flag
        that disagrees with an unchanged kind is a flag the caller changed.
        """

        epic, standard = IssueTypeKind.EPIC, IssueTypeKind.STANDARD
        # Reading the kind loads it when it was deferred, which also remembers the stored value
        kind, is_epic = self.kind, self.is_epic
        if hasattr(self, "_loaded_kind"):
            kind_changed = kind != self._loaded_kind
        else:
            # A new row: an explicit kind is anything but the default
            kind_changed = kind != standard
        if not kind_changed and is_epic != (kind == epic) and kind in (epic, standard):
            self.kind = epic if is_epic else standard
        self.is_epic = self.kind == epic

    def save(self, *args, **kwargs):
        self.sync_kind_and_is_epic()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and {"kind", "is_epic"} & set(update_fields):
            kwargs["update_fields"] = list({*update_fields, "kind", "is_epic"})
        super().save(*args, **kwargs)
        # A save limited to other fields did not write these two, so what is remembered still holds
        if kwargs.get("update_fields") is None or "kind" in kwargs["update_fields"]:
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

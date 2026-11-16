# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .base import BaseModel


class InitiativeKind(models.TextChoices):
    """The two levels of one model: a goal states an outcome, an initiative is a body of work toward it."""

    GOAL = "goal", "Goal"
    INITIATIVE = "initiative", "Initiative"


class InitiativeStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class InitiativeHealth(models.TextChoices):
    ON_TRACK = "on_track", "On track"
    AT_RISK = "at_risk", "At risk"
    OFF_TRACK = "off_track", "Off track"


class Initiative(BaseModel):
    """A goal or an initiative of a workspace. Projects and Epics are linked to initiatives, initiatives to goals."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="initiatives")
    kind = models.CharField(max_length=20, choices=InitiativeKind.choices, default=InitiativeKind.INITIATIVE)
    # The goal an initiative works toward; a goal never has a parent. Deleting the goal leaves its initiatives
    parent = models.ForeignKey(
        "db.Initiative", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    description_html = models.TextField(blank=True, default="<p></p>")
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="initiative_leads"
    )
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=InitiativeStatus.choices, default=InitiativeStatus.PLANNED)
    # Nobody has judged it yet when empty; a status update sets it
    health = models.CharField(max_length=20, choices=InitiativeHealth.choices, null=True, blank=True)
    logo_props = models.JSONField(default=dict, blank=True)
    color = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind=InitiativeKind.INITIATIVE) | Q(parent__isnull=True),
                name="initiative_goal_has_no_parent",
            ),
            models.CheckConstraint(
                condition=Q(start_date__isnull=True)
                | Q(target_date__isnull=True)
                | Q(start_date__lte=models.F("target_date")),
                name="initiative_start_date_not_after_target_date",
            ),
        ]
        indexes = [models.Index(fields=["workspace", "kind"], name="initiative_workspace_kind_idx")]
        verbose_name = "Initiative"
        verbose_name_plural = "Initiatives"
        db_table = "initiatives"
        ordering = ("sort_order", "-created_at")

    def clean(self):
        super().clean()
        if self.kind not in InitiativeKind.values:
            raise ValidationError({"kind": "The kind is either a goal or an initiative."})
        if self.status not in InitiativeStatus.values:
            raise ValidationError({"status": "Unknown status."})
        if self.health is not None and self.health not in InitiativeHealth.values:
            raise ValidationError({"health": "Unknown health."})
        if self.parent_id is not None:
            if self.kind == InitiativeKind.GOAL:
                raise ValidationError({"parent": "A goal cannot have a parent."})
            if self.parent_id == self.id:
                raise ValidationError({"parent": "An initiative cannot be its own parent."})
            parent = self.parent
            if parent.kind != InitiativeKind.GOAL:
                raise ValidationError({"parent": "The parent of an initiative must be a goal."})
            if parent.workspace_id != self.workspace_id:
                raise ValidationError({"parent": "The parent goal must belong to the same workspace."})
        if self.start_date and self.target_date and self.start_date > self.target_date:
            raise ValidationError({"target_date": "The target date cannot be before the start date."})

    def save(self, *args, **kwargs):
        self.clean()
        if self._state.adding and self.sort_order == 65535:
            # A new one goes to the end of the list
            largest = Initiative.objects.filter(workspace_id=self.workspace_id).aggregate(
                largest=models.Max("sort_order")
            )["largest"]
            if largest is not None:
                self.sort_order = largest + 10000
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} <{self.workspace_id}>"


def _only_under_an_initiative(initiative):
    if initiative.kind != InitiativeKind.INITIATIVE:
        raise ValidationError({"initiative": "Projects and Epics are linked to initiatives, not to goals."})


class InitiativeProject(BaseModel):
    """A project that belongs to an initiative. A project can belong to more than one."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="initiative_projects")
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name="project_links")
    project = models.ForeignKey("db.Project", on_delete=models.CASCADE, related_name="initiative_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["initiative", "project"],
                condition=Q(deleted_at__isnull=True),
                name="initiative_project_unique_initiative_project_when_deleted_at_null",
            )
        ]
        verbose_name = "Initiative Project"
        verbose_name_plural = "Initiative Projects"
        db_table = "initiative_projects"
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        _only_under_an_initiative(self.initiative)
        if self.project.workspace_id != self.initiative.workspace_id:
            raise ValidationError({"project": "The project must belong to the workspace of the initiative."})

    def save(self, *args, **kwargs):
        self.workspace_id = self.initiative.workspace_id
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.initiative_id} {self.project_id}"


class InitiativeEpic(BaseModel):
    """An Epic that belongs to an initiative, on its own or next to its project."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="initiative_epics")
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name="epic_links")
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="initiative_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["initiative", "issue"],
                condition=Q(deleted_at__isnull=True),
                name="initiative_epic_unique_initiative_issue_when_deleted_at_null",
            )
        ]
        verbose_name = "Initiative Epic"
        verbose_name_plural = "Initiative Epics"
        db_table = "initiative_epics"
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        _only_under_an_initiative(self.initiative)
        issue = self.issue
        if issue.workspace_id != self.initiative.workspace_id:
            raise ValidationError({"issue": "The Epic must belong to the workspace of the initiative."})
        if issue.type_id is None or not issue.type.is_epic:
            raise ValidationError({"issue": "Only an Epic can be linked to an initiative."})

    def save(self, *args, **kwargs):
        self.workspace_id = self.initiative.workspace_id
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.initiative_id} {self.issue_id}"


class InitiativeUpdate(BaseModel):
    """A periodic status note: how it is going, in words and as a health."""

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="initiative_updates")
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="initiative_updates"
    )
    health = models.CharField(max_length=20, choices=InitiativeHealth.choices)
    text = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Initiative Update"
        verbose_name_plural = "Initiative Updates"
        db_table = "initiative_updates"
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        if self.health not in InitiativeHealth.values:
            raise ValidationError({"health": "Unknown health."})

    def save(self, *args, **kwargs):
        self.workspace_id = self.initiative.workspace_id
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.initiative_id} {self.health}"

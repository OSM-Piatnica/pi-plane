# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
RACI on work items: the role a department has on a work item.

A department (a user group of kind "department") has at most one role on a work item: responsible, approver,
consulted or informed. Several departments may share a role. The roles are stored by these neutral names; the
letters (R / A / C / I, or O / Z / K / I in Polish) are a matter of the interface.

RACI is switched on in two places, both off by default: for the workspace (the workspace feature ``raci``, see
``docs/workspace-features.md``) and per project (``Project.is_raci_enabled``). While either is off the rows are kept and
neither served nor matched by filters, so switching it back on brings them back.

Who may change the roles: the admins of the project and its lead. Whoever can see the work item can read them.

What happens to the rows when the department changes follows what departments do to people:

* a department that is switched off keeps its roles (they are still shown), and cannot be given a new or another one;
* a department that is deleted, or turned back into a plain group, loses its roles.
"""

import uuid

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db import transaction
from django.db.models import F, JSONField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, JSONObject

from plane.db.models import GroupKind, IssueRaci, ProjectMember, RaciRole, UserGroup, WorkspaceMember
from plane.utils.departments import department_memberships
from plane.utils.workspace_features import enabled_workspace_feature_keys

RACI_FEATURE = "raci"

ADMIN = 20
MY_DEPARTMENT = "my_department"
RACI_DISABLED_MESSAGE = "RACI is not enabled for this project."
RACI_EDIT_MESSAGE = "Only a project admin or the project lead can change RACI."
ROLES = tuple(RaciRole.values)


RACI_ERRORS = {
    "not_a_list": "RACI is a list of departments with their roles.",
    "bad_entry": "Each RACI entry needs a group_id and a role.",
    "unknown_role": f"Unknown role. The roles are: {', '.join(ROLES)}.",
    "bad_group_id": "Each RACI entry needs the id of a department.",
    "duplicate_group": "A department can have only one role on a work item.",
    "not_a_department": "Only departments of this workspace can have a role.",
    "inactive_group": "A department that is switched off cannot be given a role.",
}


class RaciError(ValueError):
    """A list of roles that cannot be stored; ``code`` keys the fixed text in ``RACI_ERRORS`` shown to the asker."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code

    @property
    def public_message(self):
        """The fixed text for this error; never built from the exception itself."""
        return RACI_ERRORS.get(self.code, "These RACI roles cannot be saved.")


def workspace_raci_enabled(workspace):
    """Whether the workspace has the RACI feature switched on."""
    return RACI_FEATURE in enabled_workspace_feature_keys(workspace)


def project_raci_enabled(project):
    """Whether RACI is on for a project: in its workspace and in the project itself."""
    return bool(project.is_raci_enabled) and workspace_raci_enabled(project.workspace)


def can_edit_raci(user, project):
    """The admins of the project and its lead; a workspace admin who is in the project counts as its admin."""
    membership = ProjectMember.objects.filter(project=project, member=user, is_active=True).first()
    if membership is None:
        return False
    if membership.role == ADMIN or project.project_lead_id == user.id:
        return True
    return WorkspaceMember.objects.filter(
        workspace_id=project.workspace_id, member=user, role=ADMIN, is_active=True
    ).exists()


def _live_rows():
    """The rows that count: of a living department, in a project (and a workspace) that has RACI on."""
    return IssueRaci.objects.filter(
        deleted_at__isnull=True,
        project__is_raci_enabled=True,
        workspace__workspace_features__key=RACI_FEATURE,
        workspace__workspace_features__is_enabled=True,
        workspace__workspace_features__deleted_at__isnull=True,
        group__deleted_at__isnull=True,
        group__kind=GroupKind.DEPARTMENT,
    )


def raci_annotation():
    """
    The roles on a work item as ``[{"group_id": ..., "role": ...}]``, to annotate a queryset of work items with.

    One subquery for the whole list, and an empty list for a work item of a project that has RACI off.
    """
    return Coalesce(
        Subquery(
            _live_rows()
            .filter(issue_id=OuterRef("pk"))
            .values("issue_id")
            .annotate(rows=ArrayAgg(JSONObject(group_id=F("group_id"), role=F("role"))))
            .values("rows")
        ),
        Value([], output_field=ArrayField(JSONField())),
    )


def issue_raci(issue_id):
    """The roles on one work item, whatever the switch of its project says: ``[{"group_id", "role"}]``."""
    rows = (
        IssueRaci.objects.filter(issue_id=issue_id, group__kind=GroupKind.DEPARTMENT, group__deleted_at__isnull=True)
        .order_by("group__sort_order", "group__name")
        .values_list("group_id", "role")
    )
    return [{"group_id": str(group_id), "role": role} for group_id, role in rows]


def clean_raci(workspace_id, issue_id, entries):
    """
    Check a requested list of ``{"group_id", "role"}`` and return it as ``{group id: role}``.

    Every group must be a department of the workspace, named once. A department that is switched off can keep the
    role it has on the work item (unchanged), and cannot be given a new or a different one.
    """
    if not isinstance(entries, list):
        raise RaciError("not_a_list")
    wanted = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RaciError("bad_entry")
        role = entry.get("role")
        if role not in ROLES:
            raise RaciError("unknown_role")
        try:
            group_id = uuid.UUID(str(entry.get("group_id")))
        except ValueError:
            raise RaciError("bad_group_id") from None
        if group_id in wanted:
            raise RaciError("duplicate_group")
        wanted[group_id] = role

    departments = dict(
        UserGroup.objects.filter(workspace_id=workspace_id, id__in=list(wanted), kind=GroupKind.DEPARTMENT).values_list(
            "id", "is_active"
        )
    )
    if len(departments) != len(wanted):
        raise RaciError("not_a_department")
    present = dict(IssueRaci.objects.filter(issue_id=issue_id).values_list("group_id", "role"))
    if any(not is_active and present.get(group_id) != wanted[group_id] for group_id, is_active in departments.items()):
        raise RaciError("inactive_group")
    return wanted


def set_issue_raci(issue, wanted, actor=None):
    """
    Make the roles on a work item exactly ``wanted`` (``{group id: role}``).

    Returns ``(before, after)`` as lists of ``{"group_id", "role"}`` for the activity of the work item.
    """
    before = issue_raci(issue.id)
    with transaction.atomic():
        rows = {row.group_id: row for row in IssueRaci.objects.select_for_update().filter(issue=issue)}
        gone = [row.pk for group_id, row in rows.items() if group_id not in wanted]
        if gone:
            IssueRaci.objects.filter(pk__in=gone).delete()
        created = []
        for group_id, role in wanted.items():
            row = rows.get(group_id)
            if row is None:
                created.append(
                    IssueRaci(
                        issue=issue,
                        group_id=group_id,
                        role=role,
                        project_id=issue.project_id,
                        workspace_id=issue.workspace_id,
                        created_by=actor,
                        updated_by=actor,
                    )
                )
            elif row.role != role:
                row.role = role
                row.updated_by = actor
                row.save(update_fields=["role", "updated_by", "updated_at"])
        if created:
            IssueRaci.objects.bulk_create(created, batch_size=100)
    return before, issue_raci(issue.id)


def raci_changes(before, after):
    """
    What differs between two lists of ``{"group_id", "role"}``: ``[(group id, old role, new role)]``.

    The old role is ``None`` for a department that was added, the new one for a department that was removed.
    """
    old = {str(entry["group_id"]): entry["role"] for entry in before or []}
    new = {str(entry["group_id"]): entry["role"] for entry in after or []}
    changes = []
    for group_id in sorted(set(old) | set(new)):
        if old.get(group_id) != new.get(group_id):
            changes.append((group_id, old.get(group_id), new.get(group_id)))
    return changes


def remove_department_roles(group_ids):
    """A group that is deleted, or stops being a department, has no role on any work item."""
    IssueRaci.objects.filter(group_id__in=list(group_ids)).delete()


def split_department_tokens(values):
    """Split a filter value (list or comma separated text) into (department ids, my_department). Rubbish is ignored."""
    if values is None:
        return set(), False
    if isinstance(values, str):
        values = values.split(",")
    ids = set()
    mine = False
    for raw in values:
        token = str(raw).strip()
        if not token or token == "null":
            continue
        if token == MY_DEPARTMENT:
            mine = True
            continue
        try:
            ids.add(uuid.UUID(token))
        except ValueError:
            continue
    return ids, mine


def department_ids_of(user, workspace_id):
    """
    The departments of a person in a workspace: the active department groups they belong to directly.

    One per person today (decision 13, #508); a set, so that "my department" keeps working if that changes.
    """
    if user is None or not getattr(user, "id", None) or workspace_id is None:
        return set()
    return set(department_memberships(workspace_id, [user.id]).values_list("group_id", flat=True))


def issue_raci_q(user, workspace_id, values, role=None):
    """
    A Q matching the work items (use it on a queryset of Issue) on which one of the departments has a role:
    any role, or the given one. ``my_department`` stands for the department of the person who asks.

    A filter that is left with no department to match finds nothing instead of everything.
    """
    ids, mine = split_department_tokens(values)
    if mine:
        ids |= department_ids_of(user, workspace_id)
    if not ids:
        return Q(pk__in=[])
    rows = _live_rows().filter(group_id__in=ids)
    if workspace_id is not None:
        rows = rows.filter(workspace_id=workspace_id)
    if role is not None:
        rows = rows.filter(role=role)
    return Q(pk__in=rows.values("issue_id"))


def issue_raci_q_for_request(request, values, role=None):
    """``issue_raci_q`` for the person and the workspace of a request (the workspace is taken from the URL)."""
    from plane.utils.group_filters import workspace_id_from_slug

    if request is None:
        return issue_raci_q(None, None, values, role)
    context = getattr(request, "parser_context", None) or {}
    slug = (context.get("kwargs") or {}).get("slug")
    return issue_raci_q(getattr(request, "user", None), workspace_id_from_slug(slug), values, role)

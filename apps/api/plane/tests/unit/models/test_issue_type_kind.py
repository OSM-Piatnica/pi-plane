# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`IssueType.kind` says what the system does with a type; `is_epic` stays equal to `kind == "epic"`.

Covers the sync in `save()`, the check constraint that guards writes that skip `save()`, the data step of
migration 0158, the type each kind gets on demand, and the progress manager that leaves out Epics and reviews.
"""

from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from plane.db.models import (
    ISSUE_TYPE_KIND_LEVELS,
    PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS,
    SYSTEM_MANAGED_ISSUE_TYPE_KINDS,
    Cycle,
    CycleIssue,
    Issue,
    IssueType,
    IssueTypeKind,
    Project,
    ProjectIssueType,
)
from plane.utils.epic_progress import not_epic_q
from plane.utils.project_issue_types import (
    SYSTEM_MANAGED_TYPE_CODE,
    EpicsNotAvailableError,
    WorkItemTypesNotEnabledError,
    ensure_project_epic_type,
    ensure_project_kind_type,
    issue_type_assignment_error,
    linked_kind_types,
    workspace_kind_type,
)

migration = import_module("plane.db.migrations.0158_issue_type_kind")

CONSTRAINT_NAME = "issue_type_is_epic_matches_kind"
SYSTEM_KINDS = [IssueTypeKind.EPIC, IssueTypeKind.MILESTONE, IssueTypeKind.APPROVAL, IssueTypeKind.REVIEW]


def _type(workspace, name, **fields):
    return IssueType.objects.create(workspace=workspace, name=name, **fields)


def _stored(issue_type):
    return IssueType.all_objects.values_list("kind", "is_epic").get(pk=issue_type.pk)


@pytest.fixture
def project(db, workspace, create_user):
    return Project.objects.create(
        name="Kinds", identifier="KI", workspace=workspace, created_by=create_user, is_issue_type_enabled=True
    )


@pytest.mark.unit
class TestKindConstants:
    def test_every_kind_has_a_level(self):
        assert set(ISSUE_TYPE_KIND_LEVELS) == set(IssueTypeKind)
        assert ISSUE_TYPE_KIND_LEVELS[IssueTypeKind.EPIC] == 1
        assert ISSUE_TYPE_KIND_LEVELS[IssueTypeKind.REVIEW] == -1
        assert {ISSUE_TYPE_KIND_LEVELS[kind] for kind in ("standard", "milestone", "approval")} == {0}

    def test_system_managed_and_progress_excluded_kinds(self):
        assert SYSTEM_MANAGED_ISSUE_TYPE_KINDS == {"approval", "review"}
        assert PROGRESS_EXCLUDED_ISSUE_TYPE_KINDS == {"epic", "review"}


@pytest.mark.unit
class TestKindAndIsEpicStayInSync:
    @pytest.mark.django_db
    def test_a_new_type_is_standard(self, workspace):
        assert _stored(_type(workspace, "Task")) == ("standard", False)

    @pytest.mark.django_db
    def test_a_new_type_with_is_epic_gets_the_epic_kind(self, workspace):
        assert _stored(_type(workspace, "Epic", is_epic=True)) == ("epic", True)

    @pytest.mark.django_db
    def test_a_new_type_of_the_epic_kind_gets_is_epic(self, workspace):
        assert _stored(_type(workspace, "Epic", kind=IssueTypeKind.EPIC)) == ("epic", True)

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["milestone", "approval", "review"])
    def test_other_kinds_are_never_is_epic(self, workspace, kind):
        # An explicit kind decides, even when the caller also sets the flag
        assert _stored(_type(workspace, kind, kind=kind, is_epic=True)) == (kind, False)

    @pytest.mark.django_db
    def test_setting_the_flag_on_a_loaded_type_moves_the_kind(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Task").pk)
        issue_type.is_epic = True
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)

    @pytest.mark.django_db
    def test_clearing_the_flag_on_a_loaded_type_moves_the_kind_back(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Epic", is_epic=True).pk)
        issue_type.is_epic = False
        issue_type.save()
        assert _stored(issue_type) == ("standard", False)

    @pytest.mark.django_db
    def test_the_flag_follows_the_instance_across_saves_and_refreshes(self, workspace):
        issue_type = _type(workspace, "Task")
        issue_type.is_epic = True
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)
        issue_type.refresh_from_db()
        issue_type.is_epic = False
        issue_type.save()
        assert _stored(issue_type) == ("standard", False)

    @pytest.mark.django_db
    def test_changing_the_kind_of_a_loaded_type_moves_the_flag(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Epic", is_epic=True).pk)
        issue_type.kind = IssueTypeKind.MILESTONE
        issue_type.save()
        assert _stored(issue_type) == ("milestone", False)
        issue_type.kind = IssueTypeKind.EPIC
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)

    @pytest.mark.django_db
    def test_the_flag_does_not_turn_a_system_managed_type_into_an_epic(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Approval", kind=IssueTypeKind.APPROVAL).pk)
        issue_type.is_epic = True
        issue_type.save()
        assert _stored(issue_type) == ("approval", False)

    @pytest.mark.django_db
    def test_loading_a_deferred_field_does_not_lose_a_changed_flag(self, workspace):
        # Django loads a deferred field through `refresh_from_db(fields=[name])`; the flag set before that
        # read is a change by the caller, not the stored value
        issue_type = IssueType.objects.defer("description").get(pk=_type(workspace, "Task").pk)
        issue_type.is_epic = True
        assert issue_type.description == ""
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)

        issue_type = IssueType.objects.defer("description").get(pk=issue_type.pk)
        issue_type.is_epic = False
        assert issue_type.description == ""
        issue_type.save()
        assert _stored(issue_type) == ("standard", False)

    @pytest.mark.django_db
    def test_a_partial_refresh_does_not_lose_a_changed_flag_or_kind(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Task").pk)
        issue_type.is_epic = True
        issue_type.refresh_from_db(fields=["name"])
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)

        issue_type = IssueType.objects.get(pk=issue_type.pk)
        issue_type.kind = IssueTypeKind.MILESTONE
        issue_type.refresh_from_db(fields=["name"])
        issue_type.save()
        assert _stored(issue_type) == ("milestone", False)

    @pytest.mark.django_db
    def test_a_refresh_of_the_flag_takes_the_stored_value(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Task").pk)
        IssueType.objects.filter(pk=issue_type.pk).update(is_epic=True, kind=IssueTypeKind.EPIC)
        issue_type.refresh_from_db(fields=["is_epic", "kind"])
        issue_type.is_epic = False
        issue_type.save()
        assert _stored(issue_type) == ("standard", False)

    @pytest.mark.django_db
    def test_a_type_loaded_without_the_two_fields_keeps_them(self, workspace):
        epic = _type(workspace, "Epic", is_epic=True)
        issue_type = IssueType.objects.only("id", "name").get(pk=epic.pk)
        issue_type.name = "Theme"
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)

        issue_type = IssueType.objects.only("id", "name").get(pk=epic.pk)
        issue_type.is_epic = False
        issue_type.save()
        assert _stored(issue_type) == ("standard", False)

    @pytest.mark.django_db
    def test_a_save_of_other_fields_does_not_forget_a_changed_flag(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Task").pk)
        issue_type.is_epic = True
        issue_type.name = "Theme"
        issue_type.save(update_fields=["name"])
        assert _stored(issue_type) == ("standard", False)
        issue_type.save()
        assert _stored(issue_type) == ("epic", True)

    @pytest.mark.django_db
    def test_update_fields_with_one_of_the_two_writes_both(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Task").pk)
        issue_type.is_epic = True
        issue_type.save(update_fields=["is_epic"])
        assert _stored(issue_type) == ("epic", True)

    @pytest.mark.django_db
    def test_saving_another_field_keeps_the_kind(self, workspace):
        issue_type = IssueType.objects.get(pk=_type(workspace, "Review", kind=IssueTypeKind.REVIEW).pk)
        issue_type.name = "Review step"
        issue_type.save()
        assert _stored(issue_type) == ("review", False)

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "change",
        [{"is_epic": True}, {"kind": "epic"}],
        ids=["flag-without-kind", "kind-without-flag"],
    )
    def test_the_constraint_refuses_a_bulk_update_of_only_one_field(self, workspace, change):
        issue_type = _type(workspace, "Task")
        with pytest.raises(IntegrityError), transaction.atomic():
            IssueType.objects.filter(pk=issue_type.pk).update(**change)
        assert _stored(issue_type) == ("standard", False)

    @pytest.mark.django_db
    def test_a_bulk_update_of_both_fields_is_fine(self, workspace):
        issue_type = _type(workspace, "Task")
        IssueType.objects.filter(pk=issue_type.pk).update(is_epic=True, kind=IssueTypeKind.EPIC)
        assert _stored(issue_type) == ("epic", True)


@pytest.mark.unit
class TestKindMigration:
    @pytest.mark.django_db
    def test_epic_types_get_the_epic_kind_and_the_rest_stay_standard(self, workspace):
        # Rows as they are before the migration: the flag is set, the kind still holds the column default. The
        # constraint is what the migration adds last, so it is taken away for the length of this test
        constraint = next(c for c in IssueType._meta.constraints if c.name == CONSTRAINT_NAME)
        with connection.schema_editor() as editor:
            editor.remove_constraint(IssueType, constraint)
        epic = _type(workspace, "Epic")
        deleted_epic = _type(workspace, "Old epic")
        task = _type(workspace, "Task")
        IssueType.objects.filter(pk__in=[epic.pk, deleted_epic.pk]).update(is_epic=True)
        IssueType.objects.filter(pk=deleted_epic.pk).update(deleted_at=timezone.now())
        assert _stored(epic) == ("standard", True)

        migration.set_kind_from_is_epic(django_apps, None)

        assert _stored(epic) == ("epic", True)
        assert _stored(deleted_epic) == ("epic", True)
        assert _stored(task) == ("standard", False)
        # Every row now satisfies the constraint the migration adds. The foreign key checks of the rows made above
        # run first: PostgreSQL does not alter a table that still has them pending
        connection.check_constraints()
        with connection.schema_editor() as editor:
            editor.add_constraint(IssueType, constraint)

    def test_the_migration_follows_0156_and_adds_the_constraint(self):
        assert migration.Migration.dependencies == [("db", "0157_departments")]
        names = [type(operation).__name__ for operation in migration.Migration.operations]
        assert names == ["AddField", "RunPython", "AddConstraint"]
        assert migration.Migration.operations[2].constraint.name == CONSTRAINT_NAME


@pytest.mark.unit
class TestKindTypeOnDemand:
    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", SYSTEM_KINDS)
    def test_the_type_is_created_once_and_linked(self, workspace, project, kind):
        first = ensure_project_kind_type(project, kind)
        again = ensure_project_kind_type(project, kind)

        assert first.id == again.id
        assert first.kind == kind
        assert first.is_epic is (kind == IssueTypeKind.EPIC)
        assert IssueType.objects.filter(workspace=workspace, kind=kind).count() == 1
        assert list(linked_kind_types(project, kind)) == [first]
        link = ProjectIssueType.objects.get(project=project, issue_type=first)
        assert link.level == max(ISSUE_TYPE_KIND_LEVELS[kind], 0)
        assert link.is_default is False

    @pytest.mark.django_db
    def test_the_oldest_active_type_of_the_kind_is_used(self, workspace, project):
        oldest = _type(workspace, "Sign-off", kind=IssueTypeKind.APPROVAL)
        _type(workspace, "Another", kind=IssueTypeKind.APPROVAL)
        assert ensure_project_kind_type(project, IssueTypeKind.APPROVAL).id == oldest.id

    @pytest.mark.django_db
    def test_a_name_taken_by_another_kind_does_not_hand_back_that_type(self, workspace, project):
        _type(workspace, "Review")
        _type(workspace, "Review work item")
        review_type = ensure_project_kind_type(project, IssueTypeKind.REVIEW)
        assert review_type.kind == IssueTypeKind.REVIEW

    @pytest.mark.django_db
    def test_both_epic_names_taken_by_other_kinds_still_gives_an_epic_type(self, workspace, project):
        _type(workspace, "Epic")
        _type(workspace, "Epic work item")
        epic_type = ensure_project_kind_type(project, IssueTypeKind.EPIC)
        assert epic_type.kind == IssueTypeKind.EPIC
        assert epic_type.is_epic is True

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", SYSTEM_KINDS)
    def test_creation_takes_turns_per_workspace(self, workspace, project, kind):
        def workspace_locks(queries):
            return [q["sql"] for q in queries if "FOR UPDATE" in q["sql"] and '"workspaces"' in q["sql"]]

        # The first call makes the type, under a lock on the workspace row, and looks again once it holds the lock
        with CaptureQueriesContext(connection) as first:
            created = workspace_kind_type(workspace.id, kind)
        assert len(workspace_locks(first.captured_queries)) == 1
        # Later calls find the type and do not lock
        with CaptureQueriesContext(connection) as second:
            assert workspace_kind_type(workspace.id, kind).id == created.id
        assert workspace_locks(second.captured_queries) == []

    @pytest.mark.django_db
    def test_a_type_made_by_another_request_while_waiting_for_the_lock_is_used(self, workspace, project, monkeypatch):
        # What a second request sees: no type on the first look, then the type the first request committed
        from plane.utils import project_issue_types

        other = _type(workspace, "Sign-off", kind=IssueTypeKind.APPROVAL)
        real = project_issue_types._workspace_kind_types
        looks = []

        def first_look_is_empty(workspace_id, kind):
            looks.append(kind)
            return real(workspace_id, kind).none() if len(looks) == 1 else real(workspace_id, kind)

        monkeypatch.setattr(project_issue_types, "_workspace_kind_types", first_look_is_empty)

        assert workspace_kind_type(workspace.id, IssueTypeKind.APPROVAL).id == other.id
        assert len(looks) == 2
        assert IssueType.objects.filter(workspace=workspace, kind=IssueTypeKind.APPROVAL).count() == 1

    @pytest.mark.django_db
    def test_the_standard_kind_has_no_system_type(self, workspace, project):
        with pytest.raises(ValueError):
            ensure_project_kind_type(project, IssueTypeKind.STANDARD)
        with pytest.raises(ValueError):
            workspace_kind_type(workspace.id, "standard")

    @pytest.mark.django_db
    def test_types_must_be_enabled_in_the_project(self, workspace, project):
        project.is_issue_type_enabled = False
        project.save()
        with pytest.raises(WorkItemTypesNotEnabledError):
            ensure_project_kind_type(project, IssueTypeKind.MILESTONE)
        # The Epics switch raises the same error under its old name
        with pytest.raises(EpicsNotAvailableError):
            ensure_project_epic_type(project)
        assert ensure_project_kind_type(project, IssueTypeKind.MILESTONE, require_types_enabled=False) is not None

    @pytest.mark.django_db
    def test_the_epics_helper_is_the_epic_kind(self, workspace, project):
        epic_type = ensure_project_epic_type(project)
        assert epic_type.kind == IssueTypeKind.EPIC
        assert epic_type.name == "Epic"
        assert ensure_project_kind_type(project, IssueTypeKind.EPIC).id == epic_type.id


@pytest.mark.unit
class TestTypeAssignment:
    @pytest.fixture
    def types(self, workspace, project):
        made = {kind: _type(workspace, f"{kind} type", kind=kind) for kind in IssueTypeKind.values}
        made["other"] = _type(workspace, "Bug")
        for issue_type in made.values():
            ProjectIssueType.objects.create(project=project, issue_type=issue_type, workspace=workspace)
        return made

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current,new",
        [
            ("standard", "approval"),
            ("standard", "review"),
            ("epic", "approval"),
            ("milestone", "review"),
            ("approval", "standard"),
            ("approval", "epic"),
            ("review", "standard"),
            ("review", "milestone"),
            ("approval", "review"),
            ("review", "approval"),
        ],
    )
    def test_an_existing_work_item_cannot_switch_into_or_out_of_a_system_managed_kind(
        self, project, types, current, new
    ):
        error = issue_type_assignment_error(project.id, types[new], types[current])
        assert error is not None
        assert error.error_code == SYSTEM_MANAGED_TYPE_CODE

    @pytest.mark.django_db
    @pytest.mark.parametrize("new", ["approval", "review"])
    def test_an_existing_work_item_without_a_type_cannot_switch_either(self, project, types, new):
        error = issue_type_assignment_error(project.id, types[new], None, existing=True)
        assert error is not None
        assert error.error_code == SYSTEM_MANAGED_TYPE_CODE

    @pytest.mark.django_db
    @pytest.mark.parametrize("new", IssueTypeKind.values)
    def test_a_new_work_item_can_have_any_kind(self, project, types, new):
        assert issue_type_assignment_error(project.id, types[new], None) is None
        assert issue_type_assignment_error(project.id, types[new], None, existing=False) is None

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current,new",
        [("standard", "epic"), ("epic", "standard"), ("standard", "milestone"), ("standard", "other")],
    )
    def test_other_switches_are_allowed(self, project, types, current, new):
        assert issue_type_assignment_error(project.id, types[new], types[current]) is None

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["approval", "review"])
    def test_keeping_the_same_system_managed_type_is_allowed(self, project, types, kind):
        assert issue_type_assignment_error(project.id, types[kind], types[kind], existing=True) is None

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["approval", "review"])
    def test_the_type_of_a_system_managed_work_item_cannot_be_cleared(self, project, types, kind):
        for existing in (None, True):
            error = issue_type_assignment_error(project.id, None, types[kind], existing=existing)
            assert error is not None
            assert error.error_code == SYSTEM_MANAGED_TYPE_CODE

    @pytest.mark.django_db
    @pytest.mark.parametrize("kind", ["standard", "epic", "milestone"])
    def test_other_types_can_be_cleared(self, project, types, kind):
        assert issue_type_assignment_error(project.id, None, types[kind]) is None
        assert issue_type_assignment_error(project.id, None, None, existing=True) is None
        assert issue_type_assignment_error(project.id, None, None) is None

    @pytest.mark.django_db
    def test_other_reasons_have_no_code(self, workspace, project, types):
        unlinked = _type(workspace, "Unlinked")
        error = issue_type_assignment_error(project.id, unlinked, types["standard"])
        assert error == "Issue type is not enabled for this project"
        assert getattr(error, "error_code", None) is None


@pytest.mark.unit
class TestProgressLeavesOutEpicsAndReviews:
    @pytest.fixture
    def items(self, workspace, project, create_user):
        made = {}
        for kind in IssueTypeKind.values:
            issue = Issue(name=kind, project=project, workspace=workspace, type=_type(workspace, kind, kind=kind))
            issue.save(created_by_id=create_user.id)
            made[kind] = issue
        untyped = Issue(name="untyped", project=project, workspace=workspace)
        untyped.save(created_by_id=create_user.id)
        made["untyped"] = untyped
        return made

    @pytest.mark.django_db
    def test_the_progress_manager(self, project, items):
        names = set(Issue.progress_objects.filter(project=project).values_list("name", flat=True))
        assert names == {"standard", "milestone", "approval", "untyped"}
        # The list manager still has all of them
        assert Issue.issue_objects.filter(project=project).count() == len(items)

    @pytest.mark.django_db
    def test_the_count_condition(self, workspace, project, create_user, items):
        from django.db.models import Count

        cycle = Cycle.objects.create(name="Sprint", project=project, workspace=workspace, owned_by=create_user)
        for issue in items.values():
            CycleIssue.objects.create(cycle=cycle, issue=issue, project=project, workspace=workspace)

        counted = Cycle.objects.filter(pk=cycle.pk).aggregate(
            total=Count("issue_cycle__issue__id", filter=not_epic_q("issue_cycle__issue__"), distinct=True)
        )["total"]
        assert counted == 4
        assert set(Issue.objects.filter(not_epic_q(), project=project).values_list("name", flat=True)) == {
            "standard",
            "milestone",
            "approval",
            "untyped",
        }

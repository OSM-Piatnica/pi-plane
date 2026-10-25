# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the work item copy tests of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""Copying a project's work items into a duplicated project.

The interesting failures here are all silent ones. ``bulk_create`` bypasses ``Issue.save()``, so a
field nobody sets is simply wrong rather than missing; ``auto_now_add`` overwrites the dates a copy is
supposed to preserve without complaining; nothing enforces uniqueness on ``(project, sequence)``, so two
work items can end up numbered alike with no error anywhere; and a relation copied one-sidedly points
into another project and renders as a link its reader cannot open. Each of those has a test here.
"""

import uuid
from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework import status

from plane.bgtasks.project_copy_task import copy_project_work_items
from plane.db.models import (
    Cycle,
    CycleIssue,
    FileAsset,
    Issue,
    IssueAssignee,
    IssueLabel,
    IssueLink,
    IssuePropertyValue,
    IssueRelation,
    IssueSequence,
    IssueType,
    IssueTypeProperty,
    Label,
    Project,
    ProjectCopyJob,
    ProjectIssueType,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)
from plane.utils import project_copy_work_items as copy_service

ADMIN = 20
MEMBER = 15
ASSET_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def duplicate_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/duplicate/"


def status_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/copy-status/"


def retry_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/copy-retry/"


@pytest.fixture(autouse=True)
def isolate():
    """The endpoint is throttled per user and per workspace, and these tests share one slug; and the
    job is run by hand, so nothing may reach the broker."""
    cache.clear()
    with mock.patch.object(copy_project_work_items, "delay") as delay:
        yield delay


@pytest.fixture
def source(db, workspace, create_user):
    """A project with a small but awkward set of work items."""
    project = Project.objects.create(name="Source", identifier="SRC", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=ADMIN)

    backlog = State.objects.create(
        name="Backlog", color="#000", group="backlog", project=project, workspace=workspace, sequence=1000
    )
    label = Label.objects.create(name="Area", project=project, workspace=workspace, sort_order=1)
    cycle = Cycle.objects.create(name="Sprint 1", owned_by=create_user, project=project, workspace=workspace)

    parent = Issue.objects.create(
        name="Parent",
        project=project,
        workspace=workspace,
        state=backlog,
        created_by=create_user,
        start_date="2026-01-05",
        target_date="2026-01-09",
        duration=5,
    )
    child = Issue.objects.create(
        name="Child", project=project, workspace=workspace, state=backlog, parent=parent, created_by=create_user
    )
    Issue.objects.create(
        name="Grandchild", project=project, workspace=workspace, state=backlog, parent=child, created_by=create_user
    )

    IssueLabel.objects.create(issue=parent, label=label, project=project, workspace=workspace)
    IssueLink.objects.create(
        issue=parent, url="https://example.invalid/spec", title="Spec", project=project, workspace=workspace
    )
    CycleIssue.objects.create(issue=parent, cycle=cycle, project=project, workspace=workspace)

    project.default_state = backlog
    project.save()
    return project


def _duplicate(client, workspace, source, properties=None, **include):
    body = {"include": {"work_items": True, **include}}
    if properties is not None:
        body["work_item_properties"] = properties
    return client.post(duplicate_url(workspace.slug, source.id), body, format="json")


def _run_job(copy_id):
    job = ProjectCopyJob.objects.get(target_project_id=copy_id)
    copy_project_work_items(str(job.id))
    job.refresh_from_db()
    return job


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkItemCopy:
    def test_the_copy_is_created_before_any_work_item_is(self, session_client, workspace, source, isolate):
        """The project must be usable immediately; the items arrive after."""
        response = _duplicate(session_client, workspace, source)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        summary = response.data["copy_summary"]["work_items"]
        assert summary["status"] == "queued"
        assert summary["total"] == 3
        assert not Issue.objects.filter(project_id=response.data["id"]).exists()
        isolate.assert_called_once_with(summary["job_id"])

    def test_the_sub_item_tree_is_rebuilt_inside_the_copy(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        _run_job(copy_id)

        copied = {issue.name: issue for issue in Issue.objects.filter(project_id=copy_id)}
        assert copied["Parent"].parent_id is None
        assert copied["Child"].parent_id == copied["Parent"].id
        assert copied["Grandchild"].parent_id == copied["Child"].id

        # A parent pointing back into the source would be a cross-project foreign key
        source_ids = set(Issue.objects.filter(project=source).values_list("id", flat=True))
        assert not any(issue.parent_id in source_ids for issue in copied.values())

    def test_work_item_numbers_and_their_sequence_rows_travel(self, session_client, workspace, source):
        """`(project, sequence_id)` is the source-to-copy key, so it must be exact."""
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        _run_job(copy_id)

        source_numbers = sorted(Issue.objects.filter(project=source).values_list("sequence_id", flat=True))
        copy_numbers = sorted(Issue.objects.filter(project_id=copy_id).values_list("sequence_id", flat=True))
        assert copy_numbers == source_numbers

        for issue in Issue.objects.filter(project_id=copy_id):
            rows = IssueSequence.objects.filter(issue=issue)
            assert rows.count() == 1, "exactly one sequence row per work item"
            assert rows.first().sequence == issue.sequence_id

    def test_a_work_item_created_during_the_copy_cannot_take_a_reserved_number(self, session_client, workspace, source):
        """The silent collision the reservation row exists to prevent."""
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        copy = Project.objects.get(pk=copy_id)

        # Somebody adds an item to the copy while the job is still queued
        interloper = Issue.objects.create(
            name="Added by hand", project=copy, workspace=workspace, created_by=copy.created_by
        )
        assert interloper.sequence_id > 3, "must land above everything the copy still owes"

        _run_job(copy_id)

        numbers = list(Issue.objects.filter(project_id=copy_id).values_list("sequence_id", flat=True))
        assert len(numbers) == len(set(numbers)), "no two work items may share a number"

    def test_the_original_author_and_dates_are_preserved(self, session_client, workspace, source):
        """`auto_now_add` overwrites both on insert; only the second pass restores them."""
        author = User.objects.create(email="author@corp.example", username=uuid.uuid4().hex)
        original = Issue.objects.filter(project=source, name="Parent").first()
        Issue.objects.filter(pk=original.pk).update(created_by=author)

        copy_id = _duplicate(session_client, workspace, source).data["id"]
        _run_job(copy_id)

        original.refresh_from_db()
        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert copied.created_by_id == author.id, "the source's author, not whoever copied"
        assert copied.created_at == original.created_at
        assert copied.updated_at == original.updated_at

    def test_every_copied_work_item_belongs_to_the_new_workspace(self, session_client, workspace, source):
        """`bulk_create` bypasses the `save()` that normally derives `workspace`."""
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        _run_job(copy_id)

        for issue in Issue.objects.filter(project_id=copy_id):
            assert issue.workspace_id == workspace.id
            assert issue.project_id == uuid.UUID(str(copy_id))
            assert issue.description_stripped is not None or not issue.description_html

    def test_external_identifiers_are_cleared(self, session_client, workspace, source):
        for index, issue in enumerate(Issue.objects.filter(project=source)):
            Issue.objects.filter(pk=issue.pk).update(external_source="todoist_csv", external_id=f"task-{index}")

        copy_id = _duplicate(session_client, workspace, source).data["id"]
        _run_job(copy_id)

        assert not Issue.objects.filter(project_id=copy_id).exclude(external_source=None).exists()
        assert not Issue.objects.filter(project_id=copy_id).exclude(external_id=None).exists()

    def test_drafts_archived_and_intake_items_are_left_behind(self, session_client, workspace, source, create_user):
        triage = State.objects.create(
            name="Triage",
            color="#f00",
            group="triage",
            is_triage=True,
            project=source,
            workspace=workspace,
            sequence=9000,
        )
        Issue.objects.create(name="Draft", project=source, workspace=workspace, is_draft=True, created_by=create_user)
        Issue.objects.create(
            name="Archived", project=source, workspace=workspace, archived_at="2026-01-01", created_by=create_user
        )
        Issue.objects.create(name="Intake", project=source, workspace=workspace, state=triage, created_by=create_user)

        response = _duplicate(session_client, workspace, source)
        assert response.data["copy_summary"]["work_items"]["total"] == 3
        _run_job(response.data["id"])

        assert sorted(Issue.objects.filter(project_id=response.data["id"]).values_list("name", flat=True)) == [
            "Child",
            "Grandchild",
            "Parent",
        ]

    def test_comments_attachments_and_time_entries_are_reported_as_not_copied(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = _run_job(copy_id)

        for note in ("comments", "attachments", "history", "worklogs", "subscribers"):
            assert f"work_items:{note}-not-copied" in job.skipped

    def test_an_assignee_who_is_not_in_the_copy_is_dropped_and_counted(
        self, session_client, workspace, source, create_user
    ):
        outsider = User.objects.create(email="outsider@corp.example", username=uuid.uuid4().hex)
        WorkspaceMember.objects.create(workspace=workspace, member=outsider, role=MEMBER)
        ProjectMember.objects.create(project=source, member=outsider, workspace=workspace, role=MEMBER)
        parent = Issue.objects.get(project=source, name="Parent")
        IssueAssignee.objects.create(issue=parent, assignee=outsider, project=source, workspace=workspace)
        IssueAssignee.objects.create(issue=parent, assignee=create_user, project=source, workspace=workspace)

        # Members are not copied, so only the person doing the copy is in the target
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = _run_job(copy_id)

        copied_parent = Issue.objects.get(project_id=copy_id, name="Parent")
        assignees = set(IssueAssignee.objects.filter(issue=copied_parent).values_list("assignee_id", flat=True))
        assert assignees == {create_user.id}
        assert job.counts.get("assignees_dropped") == 1
        assert "work_items:assignees-not-in-copy" in job.skipped

    def test_cycle_membership_is_not_copied_unless_cycles_are(self, session_client, workspace, source):
        """Copying it anyway would carry other people's sprint planning across."""
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        _run_job(copy_id)

        assert not CycleIssue.objects.filter(project_id=copy_id).exists()

    def test_cycle_membership_travels_when_cycles_are_copied(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source, cycles=True).data["id"]
        _run_job(copy_id)

        membership = CycleIssue.objects.filter(project_id=copy_id)
        assert membership.count() == 1
        # The membership must point at the copy's cycle, not the source's
        assert membership.first().cycle.project_id == uuid.UUID(str(copy_id))

    def test_a_relation_with_one_end_outside_the_copy_is_dropped(self, session_client, workspace, source, create_user):
        """Both ends are plain FKs to Issue, so a one-sided copy leaks across projects."""
        other = Project.objects.create(name="Other", identifier="OTH", workspace=workspace, created_by=create_user)
        outside = Issue.objects.create(name="Elsewhere", project=other, workspace=workspace, created_by=create_user)

        parent = Issue.objects.get(project=source, name="Parent")
        child = Issue.objects.get(project=source, name="Child")
        IssueRelation.objects.create(
            issue=parent, related_issue=child, relation_type="blocked_by", project=source, workspace=workspace
        )
        IssueRelation.objects.create(
            issue=parent, related_issue=outside, relation_type="blocked_by", project=source, workspace=workspace
        )

        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = _run_job(copy_id)

        relations = IssueRelation.objects.filter(project_id=copy_id)
        assert relations.count() == 1
        assert relations.first().related_issue.project_id == uuid.UUID(str(copy_id))
        assert job.counts.get("relations_dropped") == 1

    def test_custom_property_values_travel_and_people_outside_the_copy_do_not(
        self, session_client, workspace, source, create_user
    ):
        outsider = User.objects.create(email="outsider2@corp.example", username=uuid.uuid4().hex)
        issue_type = IssueType.objects.create(workspace=workspace, name="Bug", created_by=create_user)
        ProjectIssueType.objects.create(project=source, workspace=workspace, issue_type=issue_type, level=0)
        text_prop = IssueTypeProperty.objects.create(
            workspace=workspace, issue_type=issue_type, title="Note", property_type="text"
        )
        people_prop = IssueTypeProperty.objects.create(
            workspace=workspace, issue_type=issue_type, title="Reviewers", property_type="member_picker"
        )
        parent = Issue.objects.get(project=source, name="Parent")
        Issue.objects.filter(pk=parent.pk).update(type=issue_type)
        IssuePropertyValue.objects.create(
            issue=parent, property=text_prop, value="hello", project=source, workspace=workspace
        )
        IssuePropertyValue.objects.create(
            issue=parent,
            property=people_prop,
            value=[str(create_user.id), str(outsider.id)],
            project=source,
            workspace=workspace,
        )

        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = _run_job(copy_id)

        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        values = {value.property_id: value.value for value in IssuePropertyValue.objects.filter(issue=copied)}
        assert values[text_prop.id] == "hello"
        assert values[people_prop.id] == [str(create_user.id)]
        assert job.counts.get("property_members_dropped") == 1

    def test_a_resumed_copy_adds_the_remainder_and_never_a_duplicate(
        self, session_client, workspace, source, create_user
    ):
        """Running the job twice must change nothing the second time, in any pass."""
        parent = Issue.objects.get(project=source, name="Parent")
        IssueAssignee.objects.create(issue=parent, assignee=create_user, project=source, workspace=workspace)

        copy_id = _duplicate(session_client, workspace, source, cycles=True).data["id"]
        _run_job(copy_id)

        def counts():
            return {
                "issues": Issue.objects.filter(project_id=copy_id).count(),
                "labels": IssueLabel.objects.filter(project_id=copy_id).count(),
                "assignees": IssueAssignee.objects.filter(project_id=copy_id).count(),
                "links": IssueLink.objects.filter(project_id=copy_id).count(),
                "cycle_membership": CycleIssue.objects.filter(project_id=copy_id).count(),
            }

        first = counts()
        assert first["assignees"] == 1 and first["labels"] == 1 and first["cycle_membership"] == 1

        job = ProjectCopyJob.objects.get(target_project_id=copy_id)
        job.status = ProjectCopyJob.Status.QUEUED
        job.completed_at = None
        job.save(update_fields=["status", "completed_at"])
        copy_project_work_items(str(job.id))

        assert counts() == first, "a rerun must add nothing, in any pass"
        job.refresh_from_db()
        assert job.status == ProjectCopyJob.Status.COMPLETED

    def test_a_partial_copy_is_completed_rather_than_duplicated(self, session_client, workspace, source):
        """Some work items already present, as a killed worker would leave."""
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        copy = Project.objects.get(pk=copy_id)
        job = ProjectCopyJob.objects.get(target_project_id=copy_id)

        one = list(copy_service.source_work_items(source.id)[:1])
        copy_service.copy_issue_batch(
            sources=one,
            target_project=copy,
            remap=copy_service.StoredRemap(job.remap),
            type_ids=copy_service._available_type_ids(copy),
            properties=set(copy_service.WORK_ITEM_PROPERTIES),
        )
        assert Issue.objects.filter(project_id=copy_id).count() == 1

        _run_job(copy_id)

        numbers = list(Issue.objects.filter(project_id=copy_id).values_list("sequence_id", flat=True))
        assert sorted(numbers) == [1, 2, 3]


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkItemProperties:
    def test_everything_is_copied_unless_the_choice_is_narrowed(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = _run_job(copy_id)

        assert job.plan["work_item_properties"] == list(copy_service.WORK_ITEM_PROPERTIES)
        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert IssueLabel.objects.filter(issue=copied).count() == 1
        assert IssueLink.objects.filter(issue=copied).count() == 1
        assert str(copied.start_date) == "2026-01-05"

    def test_a_property_left_out_is_not_copied_and_is_reported(self, session_client, workspace, source):
        choice = ["parents", "relations", "assignees", "cycles", "modules", "custom_properties", "description_images"]
        copy_id = _duplicate(session_client, workspace, source, properties=choice).data["id"]
        job = _run_job(copy_id)

        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert not IssueLabel.objects.filter(project_id=copy_id).exists()
        assert not IssueLink.objects.filter(project_id=copy_id).exists()
        assert copied.start_date is None and copied.target_date is None and copied.duration is None
        assert Issue.objects.get(project_id=copy_id, name="Child").parent_id == copied.id
        for note in ("labels", "links"):
            assert f"work_items:{note}-not-copied" in job.skipped

    def test_the_sub_item_tree_is_flat_without_parents(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source, properties=["labels"]).data["id"]
        _run_job(copy_id)

        assert not Issue.objects.filter(project_id=copy_id).exclude(parent=None).exists()

    def test_an_unknown_property_is_refused_by_name_and_nothing_is_created(self, session_client, workspace, source):
        before = Project.objects.count()

        response = _duplicate(session_client, workspace, source, properties=["labels", "bogus"])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "bogus" in str(response.data["work_item_properties"])
        assert Project.objects.count() == before
        assert not ProjectCopyJob.objects.exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestCopyJobEndpoints:
    def test_no_work_items_are_copied_unless_they_are_asked_for(self, session_client, workspace, source):
        response = session_client.post(duplicate_url(workspace.slug, source.id), {}, format="json")

        copy_id = response.data["id"]
        assert not Issue.objects.filter(project_id=copy_id).exists()
        assert not ProjectCopyJob.objects.filter(target_project_id=copy_id).exists()
        assert "work_items" not in response.data["copy_summary"]
        assert "work_items:not-copied" in response.data["copy_summary"]["skipped"]

    def test_a_second_copy_is_refused_while_one_is_running(self, session_client, workspace, source):
        """One work item copy per workspace: the defence against queueing ten."""
        _duplicate(session_client, workspace, source)

        second = _duplicate(session_client, workspace, source)

        assert second.status_code == status.HTTP_409_CONFLICT
        assert second.data["error"] == "PROJECT_COPY_ALREADY_RUNNING"

    def test_a_configuration_copy_is_not_held_up_by_a_running_work_item_copy(self, session_client, workspace, source):
        _duplicate(session_client, workspace, source)

        second = session_client.post(duplicate_url(workspace.slug, source.id), {}, format="json")

        assert second.status_code == status.HTTP_201_CREATED

    def test_progress_is_readable_from_the_project_the_client_is_looking_at(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]

        queued = session_client.get(status_url(workspace.slug, copy_id))
        assert queued.status_code == status.HTTP_200_OK
        assert queued.data["job"]["status"] == "queued"
        assert queued.data["job"]["total"] == 3

        _run_job(copy_id)

        done = session_client.get(status_url(workspace.slug, copy_id))
        assert done.data["job"]["status"] == "completed"
        assert done.data["job"]["copied"] == 3
        assert "lease_token" not in done.data["job"] and "remap" not in done.data["job"]

    def test_a_project_that_was_never_copied_reports_no_job(self, session_client, workspace, source):
        response = session_client.get(status_url(workspace.slug, source.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["job"] is None

    def test_a_failed_copy_can_be_retried_by_an_admin(self, session_client, workspace, source, isolate):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        isolate.reset_mock()
        ProjectCopyJob.objects.filter(target_project_id=copy_id).update(
            status="failed", reason="copy_failed", completed_at="2026-01-01T00:00:00Z"
        )

        response = session_client.post(retry_url(workspace.slug, copy_id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["job"]["status"] == "queued"
        isolate.assert_called_once()

    def test_only_a_failed_copy_can_be_retried(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]

        response = session_client.post(retry_url(workspace.slug, copy_id))

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "PROJECT_COPY_NOT_RETRYABLE"

    def test_a_member_cannot_retry(self, session_client, workspace, source, create_user):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        ProjectCopyJob.objects.filter(target_project_id=copy_id).update(
            status="failed", completed_at="2026-01-01T00:00:00Z"
        )
        ProjectMember.objects.filter(project_id=copy_id, member=create_user).update(role=MEMBER)

        response = session_client.post(retry_url(workspace.slug, copy_id))

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
@pytest.mark.django_db
class TestCopyJobLifecycle:
    def test_a_stalled_job_is_picked_up_by_the_sweeper(self, session_client, workspace, source, isolate):
        from plane.bgtasks.project_copy_task import reclaim_stalled_project_copies

        copy_id = _duplicate(session_client, workspace, source).data["id"]
        isolate.reset_mock()
        # Queued long ago and never delivered: a broker outage at dispatch
        ProjectCopyJob.objects.filter(target_project_id=copy_id).update(created_at="2026-01-01T00:00:00Z")

        with mock.patch.object(copy_project_work_items, "apply_async") as dispatch:
            assert reclaim_stalled_project_copies() == 1

        dispatch.assert_called_once()

    def test_a_fresh_job_is_left_to_its_own_dispatch(self, session_client, workspace, source):
        from plane.bgtasks.project_copy_task import reclaim_stalled_project_copies

        _duplicate(session_client, workspace, source)

        with mock.patch.object(copy_project_work_items, "apply_async") as dispatch:
            assert reclaim_stalled_project_copies() == 0

        dispatch.assert_not_called()

    def test_a_live_lease_keeps_a_second_worker_out(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = ProjectCopyJob.objects.get(target_project_id=copy_id)

        assert copy_service.claim(job, task_id="a") is not None
        assert copy_service.claim(job, task_id="b") is None

    def test_a_failing_copy_is_retried_then_given_up_on(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        job = ProjectCopyJob.objects.get(target_project_id=copy_id)

        with (
            mock.patch.object(copy_service, "copy_work_items", side_effect=RuntimeError("boom")),
            mock.patch.object(copy_project_work_items, "apply_async") as again,
        ):
            copy_project_work_items(str(job.id))
            job.refresh_from_db()
            assert job.status == ProjectCopyJob.Status.QUEUED and job.lease_token is None
            again.assert_called_once()

            for _ in range(5):
                copy_project_work_items(str(job.id))
        job.refresh_from_db()

        assert job.status == ProjectCopyJob.Status.FAILED
        assert job.reason == "copy_failed"
        assert job.lease_token is None and job.completed_at is not None

    def test_a_deleted_source_fails_the_copy(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]
        ProjectCopyJob.objects.filter(target_project_id=copy_id).update(source_project=None)

        job = _run_job(copy_id)

        assert job.status == ProjectCopyJob.Status.FAILED
        assert job.reason == "source_project_deleted"


def _storage_mock(copied=True):
    storage = mock.MagicMock()
    storage.copy_object.return_value = {"CopyObjectResult": {}} if copied else None
    return storage


@pytest.fixture
def source_with_image(db, workspace, source, create_user):
    """A source work item whose description embeds one uploaded image."""
    issue = Issue.objects.get(project=source, name="Parent")
    Issue.objects.filter(pk=issue.pk).update(
        description_html=f'<p>see</p><image-component src="{ASSET_ID}"></image-component>'
    )
    FileAsset.objects.create(
        id=ASSET_ID,
        attributes={"name": "diagram.png", "type": "image/png", "size": 100},
        asset="source/diagram.png",
        size=100,
        entity_type=FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
        issue=issue,
        project=source,
        workspace=workspace,
        created_by=create_user,
        is_uploaded=True,
    )
    return source


STORAGE = "plane.utils.project_copy_work_items.S3Storage"
SYNC = "plane.utils.project_copy_work_items.sync_with_external_service"


@pytest.mark.contract
@pytest.mark.django_db
class TestDescriptionImages:
    def test_a_copied_image_belongs_to_the_copy(self, session_client, workspace, source_with_image):
        """The upstream `copy_assets` filters by `project_id`, which across projects cannot be both."""
        copy_id = _duplicate(session_client, workspace, source_with_image).data["id"]

        with (
            mock.patch(STORAGE, return_value=_storage_mock()),
            mock.patch(SYNC, return_value={"description_json": {"ok": True}, "description_binary": "AAEC"}),
        ):
            _run_job(copy_id)

        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert str(ASSET_ID) not in copied.description_html, "must not still point at the source's asset"

        duplicated = FileAsset.objects.filter(project_id=copy_id, entity_type="ISSUE_DESCRIPTION")
        assert duplicated.count() == 1
        new_asset = duplicated.first()
        assert new_asset.issue_id == copied.id
        assert str(new_asset.id) in copied.description_html
        assert FileAsset.objects.get(pk=ASSET_ID).project_id == source_with_image.id, "copied, not moved"

    def test_copying_the_images_keeps_the_number_and_the_dates(self, session_client, workspace, source_with_image):
        copy_id = _duplicate(session_client, workspace, source_with_image).data["id"]
        original = Issue.objects.get(project=source_with_image, name="Parent")

        with mock.patch(STORAGE, return_value=_storage_mock()), mock.patch(SYNC, return_value={}):
            _run_job(copy_id)

        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert copied.sequence_id == original.sequence_id
        assert IssueSequence.objects.filter(issue=copied).count() == 1
        assert copied.updated_at == original.updated_at, "the description is written without touching updated_at"

    def test_an_image_that_cannot_be_copied_is_removed_rather_than_left_pointing_at_the_source(
        self, session_client, workspace, source_with_image
    ):
        FileAsset.objects.filter(pk=ASSET_ID).update(is_uploaded=False)

        copy_id = _duplicate(session_client, workspace, source_with_image).data["id"]
        with mock.patch(STORAGE, return_value=_storage_mock()), mock.patch(SYNC, return_value={}):
            job = _run_job(copy_id)

        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert str(ASSET_ID) not in copied.description_html
        assert "image-component" not in copied.description_html
        assert "see" in copied.description_html, "the rest of the description survives"
        assert "work_items:description-images-removed" in job.skipped

    def test_a_failed_storage_copy_removes_the_image_too(self, session_client, workspace, source_with_image):
        copy_id = _duplicate(session_client, workspace, source_with_image).data["id"]

        with mock.patch(STORAGE, return_value=_storage_mock(copied=False)), mock.patch(SYNC, return_value={}):
            job = _run_job(copy_id)

        copied = Issue.objects.get(project_id=copy_id, name="Parent")
        assert "image-component" not in copied.description_html
        assert not FileAsset.objects.filter(project_id=copy_id).exists()
        assert job.counts.get("description_images_removed") == 1

    def test_running_the_pass_twice_does_not_copy_the_image_twice(self, session_client, workspace, source_with_image):
        """Object storage copies cannot be rolled back, so the pass asks the result."""
        copy_id = _duplicate(session_client, workspace, source_with_image).data["id"]

        for _ in range(2):
            job = ProjectCopyJob.objects.get(target_project_id=copy_id)
            job.status = ProjectCopyJob.Status.QUEUED
            job.completed_at = None
            job.save(update_fields=["status", "completed_at"])
            with (
                mock.patch(STORAGE, return_value=_storage_mock()),
                mock.patch(SYNC, return_value={"description_json": {"a": 1}, "description_binary": "AAEC"}),
            ):
                copy_project_work_items(str(job.id))

        assert FileAsset.objects.filter(project_id=copy_id, entity_type="ISSUE_DESCRIPTION").count() == 1

    def test_an_unreachable_live_server_keeps_the_copy_rather_than_failing_it(
        self, session_client, workspace, source_with_image
    ):
        copy_id = _duplicate(session_client, workspace, source_with_image).data["id"]

        with mock.patch(STORAGE, return_value=_storage_mock()), mock.patch(SYNC, return_value={}):
            job = _run_job(copy_id)

        assert job.status == ProjectCopyJob.Status.COMPLETED
        assert "work_items:descriptions-not-reconverted" in job.skipped
        assert FileAsset.objects.filter(project_id=copy_id, entity_type="ISSUE_DESCRIPTION").count() == 1

    def test_an_item_without_images_costs_no_live_server_call(self, session_client, workspace, source):
        copy_id = _duplicate(session_client, workspace, source).data["id"]

        with mock.patch(STORAGE) as storage, mock.patch(SYNC) as sync:
            _run_job(copy_id)

        sync.assert_not_called()
        storage.return_value.copy_object.assert_not_called()

    def test_images_are_left_alone_when_not_asked_for(self, session_client, workspace, source_with_image):
        choice = [name for name in copy_service.WORK_ITEM_PROPERTIES if name != "description_images"]
        copy_id = _duplicate(session_client, workspace, source_with_image, properties=choice).data["id"]

        with mock.patch(STORAGE) as storage:
            job = _run_job(copy_id)

        storage.return_value.copy_object.assert_not_called()
        assert "work_items:description-images-not-copied" in job.skipped

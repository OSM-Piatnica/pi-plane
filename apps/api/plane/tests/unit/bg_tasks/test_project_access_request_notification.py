# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Admins and the lead of a Private project are told, in the inbox and by email, about a request to join it."""

from unittest.mock import patch

import pytest

from plane.bgtasks.project_access_request_notification_task import (
    ACCESS_REQUEST_ENTITY,
    access_request_recipients,
    notify_project_access_request,
)
from plane.db.models import Notification, Profile, Project, ProjectAccessRequest, ProjectMember, WorkspaceMember
from plane.db.models.project import ProjectNetwork
from plane.tests.factories import UserFactory, WorkspaceFactory

ADMIN, MEMBER = 20, 15
CONFIG = ("localhost", "", "", "25", "0", "0", "noreply@example.com")


def _user(workspace, language="en", **kwargs):
    user = UserFactory(**kwargs)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=MEMBER)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.language = language
    profile.save()
    return user


@pytest.fixture
def workspace(db):
    return WorkspaceFactory()


@pytest.fixture
def project(workspace):
    return Project.objects.create(
        name="Secret Plans", identifier="SP", workspace=workspace, network=ProjectNetwork.PRIVATE.value
    )


def _join(project, user, role):
    return ProjectMember.objects.create(workspace=project.workspace, project=project, member=user, role=role)


@pytest.mark.unit
@pytest.mark.django_db
class TestRecipients:
    def test_admins_and_the_lead_are_told_but_not_plain_members(self, workspace, project):
        admin, lead, plain = _user(workspace), _user(workspace), _user(workspace)
        requester = _user(workspace)
        _join(project, admin, ADMIN)
        _join(project, lead, MEMBER)
        _join(project, plain, MEMBER)
        project.project_lead = lead
        project.save()

        assert {user.id for user in access_request_recipients(project, requester.id)} == {admin.id, lead.id}

    def test_a_lead_who_left_the_project_is_not_told(self, workspace, project):
        admin, lead, requester = _user(workspace), _user(workspace), _user(workspace)
        _join(project, admin, ADMIN)
        project.project_lead = lead
        project.save()

        assert [user.id for user in access_request_recipients(project, requester.id)] == [admin.id]

    def test_the_requester_is_never_told_about_their_own_request(self, workspace, project):
        admin = _user(workspace)
        _join(project, admin, ADMIN)
        assert access_request_recipients(project, admin.id) == []

    def test_deactivated_members_and_bots_are_skipped(self, workspace, project):
        inactive, bot, requester = _user(workspace, is_active=False), _user(workspace, is_bot=True), _user(workspace)
        _join(project, inactive, ADMIN)
        _join(project, bot, ADMIN)
        assert access_request_recipients(project, requester.id) == []


@pytest.mark.unit
@pytest.mark.django_db
class TestNotifyProjectAccessRequest:
    @pytest.fixture
    def request_to_join(self, workspace, project):
        admin = _user(workspace, language="pl", first_name="Anna")
        requester = _user(workspace, first_name="Rob", last_name="Roy")
        _join(project, admin, ADMIN)
        access_request = ProjectAccessRequest.objects.create(project=project, requester=requester, message="Let me in")
        return access_request, admin, requester

    def _run(self, access_request):
        with patch(
            "plane.bgtasks.project_access_request_notification_task.get_email_configuration", return_value=CONFIG
        ):
            notify_project_access_request(str(access_request.id))

    def test_creates_the_inbox_entry_with_what_the_web_app_needs(self, request_to_join, project, mailoutbox):
        access_request, admin, requester = request_to_join
        self._run(access_request)

        notification = Notification.objects.get(receiver=admin, entity_name=ACCESS_REQUEST_ENTITY)
        assert notification.entity_identifier == access_request.id
        assert notification.triggered_by == requester
        assert notification.project == project
        assert notification.read_at is None
        assert notification.data["project"] == {
            "id": str(project.id),
            "name": "Secret Plans",
            "identifier": "SP",
            "workspace_slug": project.workspace.slug,
        }
        assert notification.data["access_request"] == {"id": str(access_request.id), "message": "Let me in"}

    def test_sends_an_email_in_the_language_of_the_receiver_with_a_link_to_the_member_settings(
        self, request_to_join, project, settings, mailoutbox
    ):
        settings.WEB_URL = "http://localhost:3000"
        access_request, admin, requester = request_to_join
        self._run(access_request)

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [admin.email]
        assert "prosi o dostęp do projektu Secret Plans" in mail.subject
        html = mail.alternatives[0][0]
        assert f"http://localhost:3000/{project.workspace.slug}/settings/projects/{project.id}/members/" in html
        assert "Let me in" in html and "Wiadomość:" in html

    def test_a_second_run_does_not_announce_the_same_request_twice(self, request_to_join, mailoutbox):
        access_request, admin, requester = request_to_join
        self._run(access_request)
        self._run(access_request)
        assert Notification.objects.filter(entity_name=ACCESS_REQUEST_ENTITY).count() == 1
        assert len(mailoutbox) == 1

    def test_a_request_that_has_been_decided_is_not_announced(self, request_to_join, mailoutbox):
        access_request, admin, requester = request_to_join
        access_request.status = ProjectAccessRequest.APPROVED
        access_request.save()
        self._run(access_request)
        assert not Notification.objects.filter(entity_name=ACCESS_REQUEST_ENTITY).exists()
        assert mailoutbox == []

    def test_a_failing_email_does_not_lose_the_inbox_entry(self, request_to_join):
        access_request, admin, requester = request_to_join
        with patch(
            "plane.bgtasks.project_access_request_notification_task.get_email_configuration",
            side_effect=RuntimeError("no smtp"),
        ):
            notify_project_access_request(str(access_request.id))
        assert Notification.objects.filter(receiver=admin, entity_name=ACCESS_REQUEST_ENTITY).exists()

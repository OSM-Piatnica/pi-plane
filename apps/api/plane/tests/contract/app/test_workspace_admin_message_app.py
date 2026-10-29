# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Writing to the admins of a workspace from the Help menu."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.bgtasks.workspace_admin_message_notification import ADMIN_MESSAGE_ENTITY, MESSAGE_LIMIT, MESSAGE_MAX_LENGTH
from plane.db.models import Notification, User, WorkspaceMember

ADMIN, MEMBER, GUEST = 20, 15, 5


def _url(workspace):
    return f"/api/workspaces/{workspace.slug}/admin-messages/"


def _person(workspace, role, email):
    user = User.objects.create(email=email, username=email)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture(autouse=True)
def mail_task():
    with patch("plane.app.views.workspace.admin_message.email_workspace_admin_message") as task:
        yield task


@pytest.mark.contract
@pytest.mark.django_db
class TestSending:
    @pytest.mark.parametrize("role", [ADMIN, MEMBER, GUEST])
    def test_everybody_in_the_workspace_can_write_to_the_admins(
        self, workspace, create_user, role, mail_task, django_capture_on_commit_callbacks
    ):
        # create_user is the admin of the workspace; the writer is somebody else
        writer = _person(workspace, role, f"writer{role}@example.com")

        with django_capture_on_commit_callbacks(execute=True):
            response = _client(writer).post(_url(workspace), {"message": "Please help"}, format="json")

        assert response.status_code == 201, response.data
        assert response.data["recipients"] == 1
        entry = Notification.objects.get(entity_name=ADMIN_MESSAGE_ENTITY)
        assert entry.receiver_id == create_user.id and entry.triggered_by_id == writer.id
        mail_task.delay.assert_called_once_with(str(workspace.id), response.data["id"])

    def test_somebody_outside_the_workspace_cannot(self, workspace):
        outsider = User.objects.create(email="out@example.com", username="out")

        response = _client(outsider).post(_url(workspace), {"message": "Hi"}, format="json")

        assert response.status_code == 403
        assert not Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).exists()

    def test_somebody_who_is_not_signed_in_cannot(self, workspace):
        response = APIClient().post(_url(workspace), {"message": "Hi"}, format="json")

        assert response.status_code in (401, 403)

    @pytest.mark.parametrize("message", ["", "   ", None])
    def test_an_empty_message_is_refused(self, workspace, message):
        writer = _person(workspace, MEMBER, "w@example.com")

        response = _client(writer).post(_url(workspace), {"message": message}, format="json")

        assert response.status_code == 400
        assert not Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).exists()

    def test_a_message_that_is_too_long_is_refused_and_the_longest_one_is_not(self, workspace):
        writer = _person(workspace, MEMBER, "w@example.com")

        too_long = _client(writer).post(_url(workspace), {"message": "x" * (MESSAGE_MAX_LENGTH + 1)}, format="json")
        longest = _client(writer).post(_url(workspace), {"message": "x" * MESSAGE_MAX_LENGTH}, format="json")

        assert too_long.status_code == 400 and longest.status_code == 201

    def test_the_only_admin_has_nobody_to_write_to(self, workspace, session_client):
        response = session_client.post(_url(workspace), {"message": "Hi"}, format="json")

        assert response.status_code == 400
        assert not Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).exists()

    def test_every_admin_is_told_but_not_other_members(self, workspace, create_user):
        second_admin = _person(workspace, ADMIN, "admin2@example.com")
        bystander = _person(workspace, MEMBER, "bystander@example.com")
        writer = _person(workspace, MEMBER, "w@example.com")

        response = _client(writer).post(_url(workspace), {"message": "Hello"}, format="json")

        assert response.data["recipients"] == 2
        receivers = set(
            Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).values_list("receiver_id", flat=True)
        )
        assert receivers == {create_user.id, second_admin.id}
        assert bystander.id not in receivers


@pytest.mark.contract
@pytest.mark.django_db
class TestLimit:
    def test_a_person_can_write_a_few_times_an_hour_to_one_workspace(self, workspace, create_user):
        _person(workspace, ADMIN, "admin2@example.com")
        writer = _person(workspace, MEMBER, "w@example.com")
        client = _client(writer)

        results = [client.post(_url(workspace), {"message": f"m{i}"}, format="json") for i in range(MESSAGE_LIMIT + 1)]

        assert [r.status_code for r in results] == [201] * MESSAGE_LIMIT + [429]
        assert results[-1].data["code"] == "RATE_LIMITED"
        # several admins make several entries but one message
        assert Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).count() == MESSAGE_LIMIT * 2

    def test_the_limit_is_per_person(self, workspace):
        first = _person(workspace, MEMBER, "a@example.com")
        second = _person(workspace, MEMBER, "b@example.com")
        for i in range(MESSAGE_LIMIT):
            assert _client(first).post(_url(workspace), {"message": f"m{i}"}, format="json").status_code == 201

        assert _client(first).post(_url(workspace), {"message": "more"}, format="json").status_code == 429
        assert _client(second).post(_url(workspace), {"message": "hi"}, format="json").status_code == 201

    def test_old_messages_do_not_count(self, workspace):
        writer = _person(workspace, MEMBER, "w@example.com")
        client = _client(writer)
        for i in range(MESSAGE_LIMIT):
            assert client.post(_url(workspace), {"message": f"m{i}"}, format="json").status_code == 201
        Notification.objects.filter(entity_name=ADMIN_MESSAGE_ENTITY).update(
            created_at=timezone.now() - timedelta(hours=2)
        )

        assert client.post(_url(workspace), {"message": "again"}, format="json").status_code == 201


@pytest.mark.contract
@pytest.mark.django_db
class TestInbox:
    def test_the_admin_sees_the_message_in_the_notifications_list(self, workspace, create_user, session_client):
        writer = _person(workspace, MEMBER, "w@example.com")
        _client(writer).post(_url(workspace), {"message": "Please help"}, format="json")

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/users/notifications/?per_page=20&cursor=20:0:0"
        )

        assert response.status_code == 200, getattr(response, "data", None)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert [row["entity_name"] for row in results] == [ADMIN_MESSAGE_ENTITY]
        assert results[0]["data"]["workspace_admin_message"]["message"] == "Please help"

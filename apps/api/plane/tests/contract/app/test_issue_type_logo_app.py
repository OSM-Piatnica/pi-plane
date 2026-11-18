# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the work item type tests of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""The logo of a work item type is shown next to the identifier of every work item of the type, so only the emoji or
icon shape the renderer understands is stored."""

import pytest
from rest_framework import status

from plane.db.models import IssueType

LIST_URL = "/api/workspaces/{slug}/issue-types/"
DETAIL_URL = "/api/workspaces/{slug}/issue-types/{pk}/"

DEFAULT_LOGO = {"in_use": "icon", "icon": {"name": "layers", "color": "#60646C", "background_color": "#F9F9FB"}}


@pytest.fixture
def issue_type(db, workspace):
    return IssueType.objects.create(workspace=workspace, name="Bug")


@pytest.mark.contract
class TestIssueTypeLogo:
    @pytest.mark.django_db
    def test_an_icon_and_an_emoji_are_stored(self, session_client, workspace, issue_type):
        url = DETAIL_URL.format(slug=workspace.slug, pk=issue_type.id)

        icon = session_client.patch(
            url, {"logo_props": {"in_use": "icon", "icon": {"name": "rocket", "color": "#6d28d9"}}}, format="json"
        )
        assert icon.status_code == status.HTTP_200_OK, icon.data
        issue_type.refresh_from_db()
        assert issue_type.logo_props == {"in_use": "icon", "icon": {"name": "rocket", "color": "#6d28d9"}}

        emoji = session_client.patch(
            url, {"logo_props": {"in_use": "emoji", "emoji": {"value": "128640"}}}, format="json"
        )
        assert emoji.status_code == status.HTTP_200_OK, emoji.data
        issue_type.refresh_from_db()
        assert issue_type.logo_props == {"in_use": "emoji", "emoji": {"value": "128640"}}

    @pytest.mark.django_db
    def test_what_the_settings_form_sends_is_accepted(self, session_client, workspace):
        response = session_client.post(
            LIST_URL.format(slug=workspace.slug), {"name": "Story", "logo_props": DEFAULT_LOGO}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert IssueType.objects.get(pk=response.data["id"]).logo_props == DEFAULT_LOGO

    @pytest.mark.django_db
    def test_an_empty_logo_clears_it(self, session_client, workspace, issue_type):
        IssueType.objects.filter(pk=issue_type.pk).update(logo_props=DEFAULT_LOGO)
        response = session_client.patch(
            DETAIL_URL.format(slug=workspace.slug, pk=issue_type.id), {"logo_props": {}}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        issue_type.refresh_from_db()
        assert issue_type.logo_props == {}

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "logo_props",
        [
            {"in_use": "svg", "svg": {"value": "<svg/>"}},
            {"in_use": "icon"},
            {"in_use": "icon", "icon": {"name": ""}},
            {"in_use": "icon", "icon": {"name": "rocket", "onload": "x"}},
            {"in_use": "icon", "icon": {"name": 5}},
            {"in_use": "emoji", "emoji": {"value": "x" * 65}},
            {"in_use": "emoji", "emoji": {"value": "1"}, "extra": True},
            ["emoji"],
            "emoji",
        ],
    )
    def test_a_malformed_logo_is_refused(self, session_client, workspace, issue_type, logo_props):
        response = session_client.patch(
            DETAIL_URL.format(slug=workspace.slug, pk=issue_type.id), {"logo_props": logo_props}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        issue_type.refresh_from_db()
        assert issue_type.logo_props == {}

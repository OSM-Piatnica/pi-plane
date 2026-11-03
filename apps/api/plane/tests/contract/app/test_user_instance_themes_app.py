# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The web app lists the instance themes at a path that is not an "instances" path: those only take the God Mode
session, so a signed-in person got 401 there."""

import pytest

from plane.license.models import InstanceTheme

URL = "/api/users/me/themes/"
THEME = {"name": "Piątnica Dark", "primary": "#4F8F7D", "background": "#404040", "dark_palette": True}


@pytest.mark.contract
@pytest.mark.django_db
class TestUserInstanceThemes:
    def test_a_signed_in_person_lists_the_themes(self, session_client):
        InstanceTheme.objects.create(**{**THEME, "source": "deployment"})
        response = session_client.get(URL)
        assert response.status_code == 200
        assert [t["name"] for t in response.data] == ["Piątnica Dark"]

    def test_anonymous_cannot_list(self, api_client):
        assert api_client.get(URL).status_code in (401, 403)

    def test_the_path_does_not_go_to_the_admin_session(self):
        # SessionMiddleware reads the admin cookie for every path with "instances" in it
        assert "instances" not in URL

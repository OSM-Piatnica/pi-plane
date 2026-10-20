# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Migration 0135 stores the solo workspace size as "1" instead of the English "Just myself"."""

from importlib import import_module

import pytest
from django.apps import apps as django_apps
from django.utils import timezone

from plane.db.models import Workspace

migration = import_module("plane.db.migrations.0135_organization_size_just_myself_to_1")


def _workspace(owner, slug, organization_size):
    return Workspace.objects.create(name=slug, owner=owner, slug=slug, organization_size=organization_size)


@pytest.mark.unit
class TestOrganizationSizeMigration:
    @pytest.mark.django_db
    def test_just_myself_becomes_one_and_other_sizes_are_kept(self, create_user):
        solo = _workspace(create_user, "solo", "Just myself")
        small = _workspace(create_user, "small", "2-10")
        unset = _workspace(create_user, "unset", None)

        migration.just_myself_to_one(django_apps, None)

        for workspace in (solo, small, unset):
            workspace.refresh_from_db()
        assert solo.organization_size == "1"
        assert small.organization_size == "2-10"
        assert unset.organization_size is None

    @pytest.mark.django_db
    def test_soft_deleted_workspaces_are_updated_too(self, create_user):
        deleted = _workspace(create_user, "deleted", "Just myself")
        Workspace.all_objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())

        migration.just_myself_to_one(django_apps, None)

        assert Workspace.all_objects.get(pk=deleted.pk).organization_size == "1"

    @pytest.mark.django_db
    def test_reverse_restores_just_myself(self, create_user):
        solo = _workspace(create_user, "solo-again", "1")

        migration.one_to_just_myself(django_apps, None)

        solo.refresh_from_db()
        assert solo.organization_size == "Just myself"

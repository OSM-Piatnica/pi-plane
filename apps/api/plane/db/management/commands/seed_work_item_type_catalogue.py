# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand, CommandError

from plane.db.models import Workspace
from plane.utils.issue_type_catalogue import CATALOGUE_KEYS, CATALOGUE_LANGUAGES, add_catalogue_types


class Command(BaseCommand):
    help = (
        "Add the catalogue of work item types (Task, Bug, Story, Change request, Milestone) to a workspace. "
        "Types the workspace already has are left as they are."
    )

    def add_arguments(self, parser):
        parser.add_argument("workspace_slug", type=str, help="Slug of the workspace")
        parser.add_argument(
            "--keys",
            nargs="+",
            choices=CATALOGUE_KEYS,
            help="Only these entries (default: all)",
        )
        parser.add_argument(
            "--language",
            choices=CATALOGUE_LANGUAGES,
            default="en",
            help="Language of the names, descriptions, templates and properties (default: en)",
        )

    def handle(self, *args, **options):
        workspace = Workspace.objects.filter(slug=options["workspace_slug"]).first()
        if workspace is None:
            raise CommandError("Workspace not found")
        results = add_catalogue_types(workspace.id, options.get("keys"), language=options["language"])
        for key, issue_type, status in results:
            self.stdout.write(f"{key}: {status} ({issue_type.name})")

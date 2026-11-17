# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.management import BaseCommand, CommandError

# Module imports
from plane.db.models import User
from plane.utils.auto_join_workspace import get_auto_join_settings, is_eligible, join_auto_join_workspace


class Command(BaseCommand):
    help = (
        "Add the people who already have an account to the workspace that is joined at sign-in "
        "(Workspaces in the admin app), as their next sign-in would"
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="only list who would join")

    def handle(self, *args, **options):
        settings = get_auto_join_settings()
        if settings is None:
            raise CommandError(
                "Joining at sign-in is not set up: choose the workspace and the email domains in the admin app "
                "(Workspaces) first"
            )
        workspace, role, domains = settings
        dry_run = options.get("dry_run", False)

        users = [
            user
            for user in User.objects.filter(is_active=True, is_bot=False).order_by("email")
            if is_eligible(user, workspace, domains)
        ]
        for user in users:
            if dry_run:
                self.stdout.write(f"Would join: {user.email}")
            elif join_auto_join_workspace(user, settings):
                self.stdout.write(f"Joined: {user.email}")

        verb = "would join" if dry_run else "joined"
        summary = f"{len(users)} account(s) {verb} workspace {workspace.slug} (role {role} unless invited)"
        self.stdout.write(self.style.SUCCESS(summary))

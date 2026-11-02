# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
import os
from pathlib import Path

# Django imports
from django.core.management.base import BaseCommand

# Module imports
from plane.license.models import InstanceTheme
from plane.license.utils.instance_theme import clean_theme_data


def _theme_from_file(path):
    """Reads a theme file: the config the app exports (`themeName`, `primary`, `background`, `darkPalette`,
    `overrides`), or the same with `name` / `dark_palette`. Returns (cleaned, errors)."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        return None, {"file": "Must contain a JSON object."}
    data = {
        "name": raw.get("themeName", raw.get("name", Path(path).stem)),
        "primary": raw.get("primary"),
        "background": raw.get("background"),
        "dark_palette": raw.get("darkPalette", raw.get("dark_palette", False)),
        "overrides": raw.get("overrides") or {},
    }
    return clean_theme_data(data)


class Command(BaseCommand):
    help = "Load the themes of the deployment (INSTANCE_THEMES_DIR) as read-only instance themes"

    def handle(self, *args, **options):
        directory = os.environ.get("INSTANCE_THEMES_DIR", "").strip()
        if not directory:
            self.stdout.write("INSTANCE_THEMES_DIR is not set, no deployment themes to load.")
            return
        if not os.path.isdir(directory):
            self.stdout.write(self.style.WARNING(f"INSTANCE_THEMES_DIR {directory} is not a directory, skipping."))
            return

        loaded = set()
        for path in sorted(Path(directory).glob("*.json")):
            try:
                cleaned, errors = _theme_from_file(path)
            except (OSError, ValueError) as error:
                self.stdout.write(self.style.WARNING(f"{path.name}: unreadable ({error}), skipped."))
                continue
            if errors:
                self.stdout.write(self.style.WARNING(f"{path.name}: {errors}, skipped."))
                continue

            # The deployment wins over a theme added in the admin GUI under the same name
            theme = InstanceTheme.objects.filter(name__iexact=cleaned["name"]).first()
            if theme is None:
                theme = InstanceTheme(name=cleaned["name"])
            for field, value in cleaned.items():
                setattr(theme, field, value)
            theme.source = InstanceTheme.Source.DEPLOYMENT
            theme.save()
            loaded.add(theme.pk)
            self.stdout.write(self.style.SUCCESS(f"{theme.name} loaded from {path.name}."))

        # Themes that were removed from the deployment go away with it (a real delete: the name is unique)
        removed, _ = (
            InstanceTheme.objects.filter(source=InstanceTheme.Source.DEPLOYMENT)
            .exclude(pk__in=loaded)
            .delete(soft=False)
        )
        if removed:
            self.stdout.write(f"Removed {removed} deployment theme(s) that are no longer in {directory}.")

# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.http import JsonResponse

from plane.utils.space import is_space_enabled

# What only the public sharing site uses: its read-only API and its sign-in
SPACE_PATH_PREFIXES = ("/api/public/", "/auth/spaces/")


class SpaceAvailabilityMiddleware:
    """Answers 404 for everything the public sharing site uses while Space is off (see plane.utils.space)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(SPACE_PATH_PREFIXES) and not is_space_enabled():
            return JsonResponse({"error": "Web sharing is turned off on this instance."}, status=404)
        return self.get_response(request)

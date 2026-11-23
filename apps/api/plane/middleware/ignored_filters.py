# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.utils.schedule_scope import IGNORED_FILTERS_HEADER


class IgnoredFiltersMiddleware:
    """Names the filters of a request that the server left out in the ``X-Ignored-Filters`` response header, so the
    web app can tell the person that a list is not filtered by them (see ``plane.utils.schedule_scope``)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ignored = getattr(request, "ignored_filters", None)
        if ignored:
            response[IGNORED_FILTERS_HEADER] = ",".join(ignored)
        return response

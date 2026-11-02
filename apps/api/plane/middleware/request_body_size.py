# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse


# Requests whose view has its own, configurable limit on the file they carry (the import limit of the admin app). The
# body is not read here: Django streams the upload to a temporary file and the view refuses it when it is too large.
OWN_SIZE_LIMIT_PATHS = ("/import-work-items/",)


class RequestBodySizeLimitMiddleware:
    """
    Middleware to catch RequestDataTooBig exceptions and return
    413 Request Entity Too Large instead of 400 Bad Request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.endswith(OWN_SIZE_LIMIT_PATHS):
            return self.get_response(request)
        try:
            _ = request.body
        except RequestDataTooBig:
            return JsonResponse(
                {
                    "error": "REQUEST_BODY_TOO_LARGE",
                    "detail": "The size of the request body exceeds the maximum allowed size.",
                },
                status=413,
            )

        # If body size is OK, continue with the request
        return self.get_response(request)

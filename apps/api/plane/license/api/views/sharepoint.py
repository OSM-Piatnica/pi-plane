# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The "Test connection" button of Integrations → SharePoint in the admin app.

It signs in to Microsoft with the saved credentials (always asking for a new token, so that a cached one does not
hide a secret that stopped working) and, when a site address comes with the request, looks the site up and lists its
document libraries. A failure is answered with HTTP 400, a message for the administrator and an ``error_code`` that
names the case.
"""

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.license.api.permissions import InstanceAdminPermission
from plane.utils.sharepoint.client import parse_site_url
from plane.utils.sharepoint.config import get_sharepoint_client
from plane.utils.sharepoint.errors import (
    SharePointAuthError,
    SharePointError,
    SharePointNotFoundError,
    SharePointPermissionError,
)

from .base import BaseAPIView

# What a failure means once the sign-in itself has worked and a site is being looked up. The general messages of the
# client cannot know that; here the administrator is told what to do about it.
SITE_ERRORS = {
    SharePointPermissionError: (
        "site_access_denied",
        "The credentials work, but the application has no access to this site. With the Sites.Selected permission "
        "a SharePoint administrator has to grant the application access to each site it may use.",
    ),
    SharePointNotFoundError: (
        "site_not_found",
        "The credentials work, but Microsoft Graph found no site at this address. Check the address of the site.",
    ),
    SharePointAuthError: (
        "token_rejected",
        "Microsoft issued a token, but Microsoft Graph did not accept it. Check that the application has the "
        "Sites.Selected application permission for Microsoft Graph and that an administrator consented to it.",
    ),
}


def _failure(error: SharePointError, *, code: str | None = None, message: str | None = None) -> Response:
    return Response(
        {"error": message or error.message, "error_code": code or error.code, "detail": error.detail},
        status=status.HTTP_400_BAD_REQUEST,
    )


class SharePointConnectionTestEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    def post(self, request):
        site_url = str(request.data.get("site_url") or "").strip()
        try:
            # Refuse an address that is not a SharePoint site before anything is sent anywhere
            if site_url:
                parse_site_url(site_url)
            client = get_sharepoint_client(require_enabled=False)
        except SharePointError as error:
            return _failure(error)

        with client:
            try:
                client.get_token(force_refresh=True)
            except SharePointError as error:
                return _failure(error)
            if not site_url:
                return Response({"site": None, "libraries": []}, status=status.HTTP_200_OK)
            try:
                site = client.get_site(site_url)
                libraries = client.list_drives(site.id)
            except SharePointError as error:
                code, message = SITE_ERRORS.get(type(error), (None, None))
                return _failure(error, code=code, message=message)

        return Response(
            {
                "site": {"id": site.id, "name": site.name, "web_url": site.web_url},
                "libraries": [
                    {"id": library.id, "name": library.name, "web_url": library.web_url} for library in libraries
                ],
            },
            status=status.HTTP_200_OK,
        )

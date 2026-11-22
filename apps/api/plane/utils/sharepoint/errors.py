# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
What can go wrong when Pi-Plane talks to SharePoint through Microsoft Graph.

Every error carries a ``code``: a short stable word that the API hands to its caller next to the message, so the
admin app (and later the document store) can tell the cases apart without reading English. The messages are written
by Pi-Plane. What Microsoft said is kept apart in ``detail``, shortened, and never holds the client secret or a
token.
"""


class SharePointError(Exception):
    """Base of every error raised by the SharePoint client."""

    code = "sharepoint_error"

    def __init__(self, message: str, *, code: str | None = None, detail: str = "", status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        # What Microsoft answered (its error code and a shortened description), for the logs and the administrator
        self.detail = detail
        # The HTTP status of the answer, when there was one
        self.status = status


class SharePointConfigurationError(SharePointError):
    """The instance has no (complete) SharePoint configuration, or a saved value is not usable."""

    code = "not_configured"


class SharePointInputError(SharePointError):
    """A value that would end up in a request (a site URL, a site or library ID) is not acceptable."""

    code = "invalid_input"


class SharePointAuthError(SharePointError):
    """
    Microsoft did not issue or accept a token. ``code`` says why, as far as Microsoft tells:
    ``invalid_credentials`` (wrong client secret), ``secret_expired``, ``application_not_found`` (wrong client ID, or
    the app lives in another tenant), ``tenant_not_found``, or ``authentication_failed`` for anything else.
    """

    code = "authentication_failed"


class SharePointPermissionError(SharePointError):
    """
    Graph refused the call (HTTP 403). With the ``Sites.Selected`` permission this is what a site answers that the
    app was not granted access to.
    """

    code = "permission_denied"


class SharePointNotFoundError(SharePointError):
    """Graph does not know the site, library or item (HTTP 404)."""

    code = "not_found"


class SharePointThrottledError(SharePointError):
    """Graph kept answering 429 or 503 after the retries. ``retry_after`` is what it last asked for, in seconds."""

    code = "throttled"

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class SharePointTransportError(SharePointError):
    """No usable answer arrived: no connection, a timeout, or a body that is not what Graph sends."""

    code = "transport_error"


class SharePointTimeoutError(SharePointTransportError):
    """The operation ran out of time: the client's deadline passed before Microsoft had answered everything."""

    code = "timeout"


class SharePointResponseError(SharePointError):
    """Graph answered with an error that is none of the above (for example 400 or 500)."""

    code = "unexpected_response"

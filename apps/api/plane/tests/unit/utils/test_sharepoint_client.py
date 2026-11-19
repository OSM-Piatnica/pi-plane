# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
The SharePoint (Microsoft Graph) client against a fake transport.

Nothing here reaches a network: ``httpx.MockTransport`` plays Microsoft, a small object plays the cache, and the
waits between retries are recorded instead of slept. The answers are written from Microsoft's documentation; none of
this has been run against a real tenant.
"""

import logging
from email.utils import format_datetime
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
import pytest

from plane.utils.sharepoint import client as client_module
from plane.utils.sharepoint.client import (
    GRAPH_ROOT,
    MAX_ATTEMPTS,
    SharePointClient,
    parse_site_url,
    validate_client_id,
    validate_tenant_id,
)
from plane.utils.sharepoint.errors import (
    SharePointAuthError,
    SharePointError,
    SharePointInputError,
    SharePointNotFoundError,
    SharePointPermissionError,
    SharePointResponseError,
    SharePointThrottledError,
    SharePointTransportError,
)

pytestmark = pytest.mark.unit

TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT_ID = "6731de76-14a6-49ae-97bc-6eba6914391e"
SECRET = "s3cr3t~Value.That-Must_Not.Leak"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
SITE_ID = "contoso.sharepoint.com,2c712604-1370-44e7-a1f5-426573fda7b9,2d2244c3-251a-49ea-93a8-39e1c3a060fe"
DRIVE_ID = "b!BCZxLHAT50Sh9UJlc_2nucNEIi0aJepJk6g54cOgYP4"


class FakeCache:
    """The parts of Django's cache the client uses, with a clock the test moves."""

    def __init__(self):
        self.now = 0.0
        self.entries = {}
        self.timeouts = []

    def get(self, key):
        value, expires_at = self.entries.get(key, (None, 0.0))
        return value if self.now < expires_at else None

    def set(self, key, value, timeout):
        self.timeouts.append(timeout)
        self.entries[key] = (value, self.now + timeout)

    def delete(self, key):
        self.entries.pop(key, None)


class FakeMicrosoft:
    """Plays the token endpoint and Graph. `graph` is a list of answers (or a function) for the Graph calls."""

    def __init__(self, graph=(), token=None):
        self.requests = []
        self.tokens_issued = 0
        self.token_answers = list(token or [])
        self.graph_answers = graph if callable(graph) else list(graph)

    @property
    def graph_requests(self):
        return [request for request in self.requests if request.url.host == "graph.microsoft.com"]

    def __call__(self, request):
        self.requests.append(request)
        if request.url.host == "login.microsoftonline.com":
            if self.token_answers:
                answer = self.token_answers.pop(0)
                if isinstance(answer, Exception):
                    raise answer
                return answer
            self.tokens_issued += 1
            return httpx.Response(
                200, json={"token_type": "Bearer", "expires_in": 3600, "access_token": f"token-{self.tokens_issued}"}
            )
        assert request.url.host == "graph.microsoft.com", f"unexpected host {request.url.host}"
        answer = self.graph_answers(request) if callable(self.graph_answers) else self.graph_answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def graph_error(status, code="generalException", message="Something went wrong", headers=None):
    return httpx.Response(status, json={"error": {"code": code, "message": message}}, headers=headers)


def token_error(status, error, number, description):
    return httpx.Response(
        status, json={"error": error, "error_description": f"AADSTS{number}: {description}", "error_codes": [number]}
    )


@pytest.fixture
def cache():
    return FakeCache()


@pytest.fixture
def make_client(cache):
    clients = []

    def build(microsoft, **options):
        waits = []
        client = SharePointClient(
            TENANT,
            CLIENT_ID,
            SECRET,
            transport=httpx.MockTransport(microsoft),
            cache=cache,
            sleep=waits.append,
            **options,
        )
        client.waits = waits
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.close()


SITE_JSON = {
    "id": SITE_ID,
    "displayName": "Projects",
    "name": "projects",
    "webUrl": "https://contoso.sharepoint.com/sites/Projects",
}


class TestToken:
    def test_the_token_request_is_a_client_credentials_post_to_the_tenant(self, make_client):
        microsoft = FakeMicrosoft()
        assert make_client(microsoft).get_token() == "token-1"
        (request,) = microsoft.requests
        assert request.method == "POST"
        assert str(request.url) == TOKEN_URL
        form = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        assert form == {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": SECRET,
            "scope": "https://graph.microsoft.com/.default",
        }

    def test_the_token_is_cached_until_shortly_before_it_expires(self, make_client, cache):
        microsoft = FakeMicrosoft()
        client = make_client(microsoft)
        assert client.get_token() == "token-1"
        assert cache.timeouts == [3600 - 300]
        cache.now = 3299
        assert client.get_token() == "token-1"
        assert microsoft.tokens_issued == 1
        # Five minutes before Microsoft's expiry the cached token is gone and a new one is asked for
        cache.now = 3300
        assert client.get_token() == "token-2"
        assert microsoft.tokens_issued == 2

    def test_another_client_with_the_same_credentials_shares_the_cached_token(self, make_client):
        microsoft = FakeMicrosoft()
        make_client(microsoft).get_token()
        assert make_client(microsoft).get_token() == "token-1"
        assert microsoft.tokens_issued == 1

    def test_a_changed_secret_does_not_use_the_token_of_the_old_one(self, make_client, cache):
        microsoft = FakeMicrosoft()
        make_client(microsoft).get_token()
        other = SharePointClient(
            TENANT, CLIENT_ID, "another-secret", transport=httpx.MockTransport(microsoft), cache=cache
        )
        with other:
            assert other.get_token() == "token-2"

    def test_force_refresh_asks_again(self, make_client):
        microsoft = FakeMicrosoft()
        client = make_client(microsoft)
        client.get_token()
        assert client.get_token(force_refresh=True) == "token-2"
        assert client.get_token() == "token-2"

    def test_a_token_that_expires_at_once_is_not_cached(self, make_client, cache):
        microsoft = FakeMicrosoft(token=[httpx.Response(200, json={"access_token": "short", "expires_in": 120})])
        assert make_client(microsoft).get_token() == "short"
        assert cache.entries == {}

    def test_the_cache_key_does_not_hold_the_secret(self, make_client, cache):
        make_client(FakeMicrosoft()).get_token()
        (key,) = cache.entries
        assert SECRET not in key and key.startswith("sharepoint:token:")

    @pytest.mark.parametrize(
        "answer, code",
        [
            (token_error(401, "invalid_client", 7000215, "Invalid client secret provided."), "invalid_credentials"),
            (
                token_error(401, "invalid_client", 7000222, "The provided client secret keys are expired."),
                "secret_expired",
            ),
            (
                token_error(400, "unauthorized_client", 700016, "Application was not found in the directory."),
                "application_not_found",
            ),
            (token_error(400, "invalid_request", 90002, "Tenant not found."), "tenant_not_found"),
            (
                token_error(400, "invalid_request", 900023, "Specified tenant identifier is not valid."),
                "tenant_not_found",
            ),
            (httpx.Response(401, json={"error": "invalid_client"}), "invalid_credentials"),
            (httpx.Response(400, json={"error": "invalid_scope"}), "authentication_failed"),
            (httpx.Response(400, content=b"<html>nope</html>"), "authentication_failed"),
        ],
    )
    def test_a_refused_sign_in_says_why(self, make_client, cache, answer, code):
        client = make_client(FakeMicrosoft(token=[answer]))
        with pytest.raises(SharePointAuthError) as raised:
            client.get_token()
        assert raised.value.code == code
        assert raised.value.status == answer.status_code
        assert cache.entries == {}

    def test_an_error_of_the_sign_in_service_is_not_an_authentication_failure(self, make_client):
        client = make_client(FakeMicrosoft(token=[httpx.Response(500, json={"error": "server_error"})]))
        with pytest.raises(SharePointResponseError):
            client.get_token()

    def test_an_answer_without_a_token_is_refused(self, make_client):
        client = make_client(FakeMicrosoft(token=[httpx.Response(200, json={"expires_in": 3600})]))
        with pytest.raises(SharePointTransportError):
            client.get_token()

    def test_the_token_request_is_not_repeated_when_no_answer_arrives(self, make_client):
        microsoft = FakeMicrosoft(token=[httpx.ConnectError("no route")])
        client = make_client(microsoft)
        with pytest.raises(SharePointTransportError):
            client.get_token()
        assert len(microsoft.requests) == 1


class TestGraphCalls:
    def test_a_site_is_resolved_from_its_address(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.Response(200, json=SITE_JSON)])
        site = make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")
        assert (site.id, site.name, site.web_url) == (
            SITE_ID,
            "Projects",
            "https://contoso.sharepoint.com/sites/Projects",
        )
        (request,) = microsoft.graph_requests
        assert request.method == "GET"
        assert request.url.raw_path.decode().split("?")[0] == "/v1.0/sites/contoso.sharepoint.com:/sites/Projects"
        assert request.headers["Authorization"] == "Bearer token-1"

    def test_the_parts_of_a_site_path_are_encoded(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.Response(200, json=SITE_JSON)])
        make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Dział%20IT/Pod%23strona")
        path = microsoft.graph_requests[0].url.raw_path.decode().split("?")[0]
        assert path == "/v1.0/sites/contoso.sharepoint.com:/sites/Dzia%C5%82%20IT/Pod%23strona"

    def test_the_root_site_has_no_path(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.Response(200, json=SITE_JSON)])
        make_client(microsoft).get_site("https://contoso.sharepoint.com/")
        assert microsoft.graph_requests[0].url.path == "/v1.0/sites/contoso.sharepoint.com"

    def test_a_site_answer_without_an_id_is_refused(self, make_client):
        client = make_client(FakeMicrosoft(graph=[httpx.Response(200, json={"displayName": "Projects"})]))
        with pytest.raises(SharePointTransportError):
            client.get_site("https://contoso.sharepoint.com/sites/Projects")

    def test_libraries_are_listed_across_pages(self, make_client):
        next_link = f"{GRAPH_ROOT}/sites/{SITE_ID}/drives?$skiptoken=abc"
        microsoft = FakeMicrosoft(
            graph=[
                httpx.Response(
                    200,
                    json={
                        "value": [
                            {
                                "id": "b!one",
                                "name": "Documents",
                                "webUrl": "https://x/1",
                                "driveType": "documentLibrary",
                            }
                        ],
                        "@odata.nextLink": next_link,
                    },
                ),
                httpx.Response(
                    200, json={"value": [{"id": "b!two", "name": "Artwork", "driveType": "documentLibrary"}, {}]}
                ),
            ]
        )
        drives = make_client(microsoft).list_drives(SITE_ID)
        assert [(drive.id, drive.name) for drive in drives] == [("b!one", "Documents"), ("b!two", "Artwork")]
        first, second = microsoft.graph_requests
        assert first.url.path == f"/v1.0/sites/{SITE_ID}/drives"
        assert str(second.url) == next_link

    def test_a_next_link_that_leaves_graph_is_not_followed(self, make_client):
        microsoft = FakeMicrosoft(
            graph=[
                httpx.Response(
                    200, json={"value": [], "@odata.nextLink": "https://graph.microsoft.com.evil.example/v1.0/x"}
                )
            ]
        )
        with pytest.raises(SharePointTransportError):
            make_client(microsoft).list_drives(SITE_ID)
        assert len(microsoft.graph_requests) == 1

    def test_a_list_that_never_ends_is_cut_off(self, make_client):
        page = {"value": [{"id": "b!one"}], "@odata.nextLink": f"{GRAPH_ROOT}/sites/{SITE_ID}/drives?$skiptoken=again"}
        microsoft = FakeMicrosoft(graph=lambda request: httpx.Response(200, json=page))
        with pytest.raises(SharePointTransportError):
            make_client(microsoft).list_drives(SITE_ID)
        assert len(microsoft.graph_requests) == client_module.MAX_PAGES

    def test_the_root_of_a_library(self, make_client):
        microsoft = FakeMicrosoft(
            graph=[
                httpx.Response(
                    200,
                    json={
                        "id": "01ROOT",
                        "name": "root",
                        "webUrl": "https://x/root",
                        "eTag": '"e1"',
                        "folder": {"childCount": 3},
                    },
                )
            ]
        )
        root = make_client(microsoft).get_drive_root(DRIVE_ID)
        assert (root.id, root.name, root.etag, root.is_folder) == ("01ROOT", "root", '"e1"', True)
        assert microsoft.graph_requests[0].url.path == f"/v1.0/drives/{DRIVE_ID}/root"

    @pytest.mark.parametrize("site_id", ["", "contoso.sharepoint.com", "a,b,c", f"{SITE_ID}/../../me", "../users"])
    def test_a_site_id_that_is_not_one_never_reaches_graph(self, make_client, site_id):
        microsoft = FakeMicrosoft()
        with pytest.raises(SharePointInputError):
            make_client(microsoft).list_drives(site_id)
        assert microsoft.requests == []

    @pytest.mark.parametrize("drive_id", ["", "b!abc/../../users", "b!abc?x=1", "b!a b", "b!abc#"])
    def test_a_drive_id_that_is_not_one_never_reaches_graph(self, make_client, drive_id):
        microsoft = FakeMicrosoft()
        with pytest.raises(SharePointInputError):
            make_client(microsoft).get_drive_root(drive_id)
        assert microsoft.requests == []

    def test_only_graph_is_ever_sent_the_token(self, make_client):
        microsoft = FakeMicrosoft()
        client = make_client(microsoft)
        for target in (
            "https://example.com/v1.0/sites",
            "//example.com/x",
            "http://graph.microsoft.com/v1.0/sites",
            "sites",
        ):
            with pytest.raises(SharePointTransportError):
                client.request("GET", target)
        assert microsoft.requests == []


class TestErrors:
    @pytest.mark.parametrize(
        "status, error_class, code",
        [
            (403, SharePointPermissionError, "permission_denied"),
            (404, SharePointNotFoundError, "not_found"),
            (400, SharePointResponseError, "unexpected_response"),
            (500, SharePointResponseError, "unexpected_response"),
        ],
    )
    def test_an_error_answer_becomes_a_typed_error(self, make_client, status, error_class, code):
        microsoft = FakeMicrosoft(graph=[graph_error(status, "accessDenied", "Access denied")])
        with pytest.raises(error_class) as raised:
            make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")
        assert type(raised.value) is error_class
        assert (raised.value.code, raised.value.status) == (code, status)
        assert raised.value.detail == "accessDenied: Access denied"
        assert len(microsoft.graph_requests) == 1

    def test_an_error_answer_that_is_not_json_still_maps(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.Response(403, content=b"Forbidden")])
        with pytest.raises(SharePointPermissionError) as raised:
            make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")
        assert raised.value.detail == ""

    def test_a_rejected_token_is_replaced_once(self, make_client, cache):
        microsoft = FakeMicrosoft(
            graph=[graph_error(401, "InvalidAuthenticationToken"), httpx.Response(200, json=SITE_JSON)]
        )
        client = make_client(microsoft)
        assert client.get_site("https://contoso.sharepoint.com/sites/Projects").id == SITE_ID
        first, second = microsoft.graph_requests
        assert first.headers["Authorization"] == "Bearer token-1"
        assert second.headers["Authorization"] == "Bearer token-2"
        assert client.get_token() == "token-2"

    def test_a_token_rejected_twice_is_an_authentication_error(self, make_client, cache):
        microsoft = FakeMicrosoft(
            graph=lambda request: graph_error(401, "InvalidAuthenticationToken", "Access token is empty.")
        )
        with pytest.raises(SharePointAuthError) as raised:
            make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")
        assert raised.value.code == "authentication_failed"
        assert len(microsoft.graph_requests) == 2
        # The token Graph did not want is not kept
        assert cache.entries == {}

    def test_an_answer_that_is_not_json_is_a_transport_error(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.Response(200, content=b"<html>")])
        with pytest.raises(SharePointTransportError):
            make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")

    def test_an_answer_that_is_too_large_is_refused(self, make_client, monkeypatch):
        microsoft = FakeMicrosoft(graph=[httpx.Response(200, json={"id": SITE_ID, "displayName": "x" * 200})])
        client = make_client(microsoft)
        client.get_token()
        monkeypatch.setattr(client_module, "MAX_RESPONSE_BYTES", 64)
        with pytest.raises(SharePointTransportError):
            client.get_site("https://contoso.sharepoint.com/sites/Projects")

    def test_a_time_out_is_a_transport_error(self, make_client):
        microsoft = FakeMicrosoft(graph=lambda request: httpx.ReadTimeout("timed out"))
        client = make_client(microsoft)
        with pytest.raises(SharePointTransportError) as raised:
            client.get_site("https://contoso.sharepoint.com/sites/Projects")
        assert raised.value.detail == "ReadTimeout"
        assert "in time" in raised.value.message
        # A GET is tried again when no answer arrives, with a growing wait in between
        assert len(microsoft.graph_requests) == MAX_ATTEMPTS
        assert client.waits == [1.0, 2.0, 4.0]

    def test_a_get_recovers_from_a_lost_connection(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.ConnectError("reset"), httpx.Response(200, json=SITE_JSON)])
        client = make_client(microsoft)
        assert client.get_site("https://contoso.sharepoint.com/sites/Projects").id == SITE_ID
        assert client.waits == [1.0]

    def test_a_call_that_changes_something_is_not_repeated_when_no_answer_arrives(self, make_client):
        microsoft = FakeMicrosoft(graph=[httpx.ConnectError("reset")])
        client = make_client(microsoft)
        with pytest.raises(SharePointTransportError):
            client.request("POST", "/drives/x/items/y/createUploadSession", json={})
        assert len(microsoft.graph_requests) == 1

    def test_every_error_is_a_sharepoint_error(self):
        for error_class in (
            SharePointAuthError,
            SharePointInputError,
            SharePointNotFoundError,
            SharePointPermissionError,
            SharePointResponseError,
            SharePointThrottledError,
            SharePointTransportError,
        ):
            assert issubclass(error_class, SharePointError)


class TestThrottling:
    @pytest.mark.parametrize("status", [429, 503])
    def test_a_throttled_call_waits_as_long_as_asked_and_tries_again(self, make_client, status):
        microsoft = FakeMicrosoft(
            graph=[
                graph_error(status, "TooManyRequests", headers={"Retry-After": "3"}),
                httpx.Response(200, json=SITE_JSON),
            ]
        )
        client = make_client(microsoft)
        assert client.get_site("https://contoso.sharepoint.com/sites/Projects").id == SITE_ID
        assert client.waits == [3.0]
        assert len(microsoft.graph_requests) == 2

    def test_retry_after_may_be_a_date(self, make_client):
        when = format_datetime(datetime.now(UTC) + timedelta(seconds=10), usegmt=True)
        microsoft = FakeMicrosoft(
            graph=[graph_error(429, headers={"Retry-After": when}), httpx.Response(200, json=SITE_JSON)]
        )
        client = make_client(microsoft)
        client.get_site("https://contoso.sharepoint.com/sites/Projects")
        (wait,) = client.waits
        assert 5 < wait <= 10

    def test_without_retry_after_the_wait_grows(self, make_client):
        microsoft = FakeMicrosoft(graph=[graph_error(503), graph_error(503), httpx.Response(200, json=SITE_JSON)])
        client = make_client(microsoft)
        client.get_site("https://contoso.sharepoint.com/sites/Projects")
        assert client.waits == [1.0, 2.0]

    def test_the_number_of_tries_is_bounded(self, make_client):
        microsoft = FakeMicrosoft(graph=lambda request: graph_error(429, headers={"Retry-After": "1"}))
        client = make_client(microsoft)
        with pytest.raises(SharePointThrottledError) as raised:
            client.get_site("https://contoso.sharepoint.com/sites/Projects")
        assert len(microsoft.graph_requests) == MAX_ATTEMPTS
        assert client.waits == [1.0] * (MAX_ATTEMPTS - 1)
        assert (raised.value.code, raised.value.retry_after, raised.value.status) == ("throttled", 1.0, 429)

    def test_a_long_retry_after_is_not_slept_through(self, make_client):
        microsoft = FakeMicrosoft(graph=lambda request: graph_error(429, headers={"Retry-After": "3600"}))
        client = make_client(microsoft)
        with pytest.raises(SharePointThrottledError) as raised:
            client.get_site("https://contoso.sharepoint.com/sites/Projects")
        assert client.waits == []
        assert raised.value.retry_after == 3600.0
        assert len(microsoft.graph_requests) == 1

    def test_the_waits_together_stay_within_the_budget(self, make_client):
        microsoft = FakeMicrosoft(graph=lambda request: graph_error(429, headers={"Retry-After": "4"}))
        client = make_client(microsoft, max_wait=10)
        with pytest.raises(SharePointThrottledError):
            client.get_site("https://contoso.sharepoint.com/sites/Projects")
        assert client.waits == [4.0, 4.0]

    def test_a_throttled_token_request_is_retried_too(self, make_client):
        microsoft = FakeMicrosoft(token=[httpx.Response(429, headers={"Retry-After": "2"})])
        client = make_client(microsoft)
        assert client.get_token() == "token-1"
        assert client.waits == [2.0]


class TestSiteUrl:
    @pytest.mark.parametrize(
        "url, hostname, path",
        [
            ("https://contoso.sharepoint.com/sites/Projects", "contoso.sharepoint.com", "sites/Projects"),
            ("  https://Contoso.SharePoint.com/sites/Projects/  ", "contoso.sharepoint.com", "sites/Projects"),
            ("https://contoso.sharepoint.com:443/teams/IT", "contoso.sharepoint.com", "teams/IT"),
            ("https://contoso.sharepoint.com", "contoso.sharepoint.com", ""),
            (
                "https://contoso.sharepoint.com/sites/Projects/Sub%20Site",
                "contoso.sharepoint.com",
                "sites/Projects/Sub Site",
            ),
            (
                "https://contoso.sharepoint.com/sites/Projects/Shared%20Documents/Forms/AllItems.aspx?viewid=1",
                "contoso.sharepoint.com",
                "sites/Projects",
            ),
            (
                "https://contoso.sharepoint.com/sites/Projects/SitePages/Home.aspx",
                "contoso.sharepoint.com",
                "sites/Projects",
            ),
            (
                "https://contoso.sharepoint.com/sites/Projects/_layouts/15/viewlsts.aspx",
                "contoso.sharepoint.com",
                "sites/Projects",
            ),
            ("https://contoso.sharepoint.com/sites/Projects#section", "contoso.sharepoint.com", "sites/Projects"),
            (
                "https://contoso-my.sharepoint.com/personal/jan_contoso_com",
                "contoso-my.sharepoint.com",
                "personal/jan_contoso_com",
            ),
        ],
    )
    def test_a_sharepoint_address_is_taken_apart(self, url, hostname, path):
        address = parse_site_url(url)
        assert (address.hostname, address.path) == (hostname, path)

    @pytest.mark.parametrize(
        "url",
        [
            "",
            None,
            "contoso.sharepoint.com/sites/Projects",
            "http://contoso.sharepoint.com/sites/Projects",
            "ftp://contoso.sharepoint.com/sites/Projects",
            "https://example.com/sites/Projects",
            "https://sharepoint.com/sites/Projects",
            "https://contoso.sharepoint.com.evil.example/sites/Projects",
            "https://evil.example/contoso.sharepoint.com/sites/Projects",
            "https://contoso.sharepoint.com@evil.example/sites/Projects",
            "https://user:password@contoso.sharepoint.com/sites/Projects",
            "https://contoso.sharepoint.com:8443/sites/Projects",
            "https://contoso.sharepoint.com:port/sites/Projects",
            "https://a.b.sharepoint.com/sites/Projects",
            "https://169.254.169.254/latest/meta-data",
            "https://localhost/sites/Projects",
            "https://[::1]/sites/Projects",
            "https://contoso.sharepoint.com/sites/../../v1.0/users",
            "https://contoso.sharepoint.com/sites/%2e%2e/users",
            "https://contoso.sharepoint.com/sites/a%2Fb",
            "https://contoso.sharepoint.com/sites/a%5Cb",
            "https://contoso.sharepoint.com/sites/a:b",
            "https://contoso.sharepoint.com/sites/a%0Ab",
            "https://contoso.sharepoint.com\\@evil.example/sites/Projects",
            "https://contoso.sharepoint.com/sites/Projects\nHost: evil.example",
            "https://contoso.sharepoint.com/" + "/".join(["a"] * 11),
            "https://contoso.sharepoint.com/sites/" + "a" * 2000,
        ],
    )
    def test_anything_else_is_refused(self, url):
        with pytest.raises(SharePointInputError) as raised:
            parse_site_url(url)
        assert raised.value.code == "invalid_site_url"

    def test_a_refused_address_sends_nothing(self, make_client):
        microsoft = FakeMicrosoft()
        with pytest.raises(SharePointInputError):
            make_client(microsoft).get_site("https://evil.example/sites/Projects")
        assert microsoft.requests == []


class TestCredentialsFormat:
    @pytest.mark.parametrize("tenant", [TENANT, TENANT.upper(), "contoso.onmicrosoft.com", " contoso.com "])
    def test_a_tenant_is_an_id_or_a_domain(self, tenant):
        assert validate_tenant_id(tenant) == tenant.strip().lower()

    @pytest.mark.parametrize(
        "tenant",
        [
            "",
            None,
            "common/../x",
            "contoso",
            "a b.com",
            "contoso.com/evil",
            "contoso.com?x=1",
            "contoso.com#",
            "-a.com",
            "x@y.com",
        ],
    )
    def test_anything_else_is_not_a_tenant(self, tenant):
        with pytest.raises(SharePointInputError) as raised:
            validate_tenant_id(tenant)
        assert raised.value.code == "invalid_tenant_id"

    @pytest.mark.parametrize("client_id", ["", None, "my-app", f"{CLIENT_ID}x", "contoso.com"])
    def test_a_client_id_is_a_guid(self, client_id):
        with pytest.raises(SharePointInputError):
            validate_client_id(client_id)
        assert validate_client_id(CLIENT_ID.upper()) == CLIENT_ID

    def test_a_client_is_not_built_from_values_that_cannot_work(self, cache):
        for arguments in (
            ("not a tenant", CLIENT_ID, SECRET),
            (TENANT, "not-a-guid", SECRET),
            (TENANT, CLIENT_ID, "  "),
        ):
            with pytest.raises(SharePointInputError):
                SharePointClient(*arguments, cache=cache)


class TestNothingLeaks:
    """The client secret and the tokens stay out of logs, error texts and the text form of the objects."""

    def _texts(self, error):
        return " | ".join([str(error), repr(error), error.message, error.detail, error.code, repr(error.args)])

    def test_an_error_that_quotes_the_secret_is_scrubbed(self, make_client, caplog):
        caplog.set_level(logging.DEBUG)
        answer = httpx.Response(
            401,
            json={
                "error": "invalid_client",
                "error_description": f"AADSTS7000215: Invalid client secret provided: '{SECRET}'.",
                "error_codes": [7000215],
            },
        )
        client = make_client(FakeMicrosoft(token=[answer]))
        with pytest.raises(SharePointAuthError) as raised:
            client.get_token()
        assert "AADSTS7000215" in raised.value.detail
        assert "***" in raised.value.detail
        assert SECRET not in self._texts(raised.value)
        assert SECRET not in caplog.text

    def test_a_graph_error_that_quotes_the_token_is_scrubbed(self, make_client, caplog):
        caplog.set_level(logging.DEBUG)
        microsoft = FakeMicrosoft(graph=[graph_error(403, "accessDenied", "Token token-1 has no roles")])
        with pytest.raises(SharePointPermissionError) as raised:
            make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")
        assert "token-1" not in self._texts(raised.value)
        assert "token-1" not in caplog.text

    def test_logs_of_a_whole_exchange_hold_no_secret_and_no_token(self, make_client, caplog):
        caplog.set_level(logging.DEBUG)
        microsoft = FakeMicrosoft(
            graph=[
                graph_error(429, headers={"Retry-After": "1"}),
                graph_error(401),
                httpx.Response(200, json=SITE_JSON),
                httpx.ConnectError(f"cannot connect with {SECRET}"),
                httpx.Response(200, json={"value": []}),
            ]
        )
        client = make_client(microsoft)
        site = client.get_site("https://contoso.sharepoint.com/sites/Projects?secret=" + SECRET)
        client.list_drives(site.id)
        assert "SharePoint:" in caplog.text
        for confidential in (SECRET, "token-1", "token-2"):
            assert confidential not in caplog.text

    def test_a_transport_error_does_not_carry_the_request(self, make_client):
        client = make_client(FakeMicrosoft(token=[httpx.ConnectError(f"body was client_secret={SECRET}")]))
        with pytest.raises(SharePointTransportError) as raised:
            client.get_token()
        assert SECRET not in self._texts(raised.value)
        assert raised.value.__cause__ is None and raised.value.__suppress_context__

    def test_the_text_form_of_the_client_holds_no_secret(self, make_client):
        client = make_client(FakeMicrosoft())
        client.get_token()
        assert SECRET not in repr(client) and SECRET not in str(client)
        assert "token-1" not in repr(client)

    def test_microsofts_text_is_shortened(self, make_client):
        microsoft = FakeMicrosoft(graph=[graph_error(403, "accessDenied", "x" * 5000)])
        with pytest.raises(SharePointPermissionError) as raised:
            make_client(microsoft).get_site("https://contoso.sharepoint.com/sites/Projects")
        assert len(raised.value.detail) <= 300

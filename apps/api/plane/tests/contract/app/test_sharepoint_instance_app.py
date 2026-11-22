# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
SharePoint in the instance settings: saving the configuration, the "Test connection" endpoint of the admin app and
the flag the apps read.

Microsoft is played by ``httpx.MockTransport``, put under the real client, so the saved (encrypted) configuration is
read and used as in production while nothing reaches a network. The answers are written from Microsoft's
documentation; none of this has been run against a real tenant.
"""

from urllib.parse import parse_qs
from uuid import uuid4

import httpx
import pytest
from django.conf import settings as django_settings
from django.contrib.auth import login
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from django.utils import timezone

from plane.db.models import User
from plane.db.models.session import SessionStore
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.license.utils.encryption import decrypt_data, encrypt_data
from plane.utils.instance_config_variables import instance_config_variables
from plane.utils.sharepoint import config as sharepoint_config
from plane.utils.sharepoint.client import SharePointClient
from plane.utils.sharepoint.config import (
    DEFAULT_MAX_FILE_SIZE,
    MAX_MAX_FILE_SIZE,
    MB,
    get_sharepoint_client,
    get_sharepoint_max_file_size,
    get_sharepoint_settings,
    is_sharepoint_enabled,
)
from plane.utils.sharepoint.errors import SharePointConfigurationError

CONFIGURATIONS = "/api/instances/configurations/"
INSTANCE = "/api/instances/"
TEST_CONNECTION = "/api/instances/sharepoint/test-connection/"

TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT_ID = "6731de76-14a6-49ae-97bc-6eba6914391e"
SECRET = "s3cr3t~Value.That-Must_Not.Leak"
SITE_URL = "https://contoso.sharepoint.com/sites/Projects"
SITE_ID = "contoso.sharepoint.com,2c712604-1370-44e7-a1f5-426573fda7b9,2d2244c3-251a-49ea-93a8-39e1c3a060fe"
KEYS = [
    "IS_SHAREPOINT_ENABLED",
    "SHAREPOINT_TENANT_ID",
    "SHAREPOINT_CLIENT_ID",
    "SHAREPOINT_CLIENT_SECRET",
    "SHAREPOINT_MAX_FILE_SIZE",
]


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="Test",
        instance_id=uuid4().hex,
        current_version="1.0.0",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def instance_admin(instance, create_user):
    return InstanceAdmin.objects.create(instance=instance, user=create_user, role=20)


@pytest.fixture
def rows(db):
    """The configuration rows as `configure_instance` seeds them: empty, the secret marked as encrypted."""
    for key in KEYS:
        InstanceConfiguration.objects.create(
            key=key,
            value="0" if key == "IS_SHAREPOINT_ENABLED" else "",
            category="SHAREPOINT",
            is_encrypted=key == "SHAREPOINT_CLIENT_SECRET",
        )


def store(**values):
    for key, value in values.items():
        row = InstanceConfiguration.objects.get(key=key)
        row.value = encrypt_data(value) if row.is_encrypted else value
        row.save()


@pytest.fixture
def credentials(rows):
    store(SHAREPOINT_TENANT_ID=TENANT, SHAREPOINT_CLIENT_ID=CLIENT_ID, SHAREPOINT_CLIENT_SECRET=SECRET)


class FakeMicrosoft:
    """The token endpoint and Graph. Each can be given an answer (or a function of the request) to return instead."""

    def __init__(self):
        self.requests = []
        self.token_answer = None
        self.site_answer = None
        self.drives_answer = None
        # Seconds the clients built on this fake may take; None keeps the client's own default
        self.deadline = None

    def hosts(self):
        return [request.url.host for request in self.requests]

    def __call__(self, request):
        self.requests.append(request)
        if request.url.host == "login.microsoftonline.com":
            answer = self.token_answer or httpx.Response(
                200, json={"token_type": "Bearer", "expires_in": 3600, "access_token": f"token-{len(self.requests)}"}
            )
        elif request.url.host == "graph.microsoft.com" and request.url.path.endswith("/drives"):
            answer = self.drives_answer or httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": "b!one",
                            "name": "Documents",
                            "webUrl": f"{SITE_URL}/Shared%20Documents",
                            "driveType": "documentLibrary",
                        },
                        {"id": "b!two", "name": "Artwork", "webUrl": f"{SITE_URL}/Artwork"},
                    ]
                },
            )
        elif request.url.host == "graph.microsoft.com":
            answer = self.site_answer or httpx.Response(
                200, json={"id": SITE_ID, "displayName": "Projects", "webUrl": SITE_URL}
            )
        else:
            raise AssertionError(f"unexpected host {request.url.host}")
        if callable(answer):
            answer = answer(request)
        if isinstance(answer, Exception):
            raise answer
        # A copy: the same answer may be given to several requests, and a response is read only once
        return httpx.Response(answer.status_code, headers=answer.headers, content=answer.content)


@pytest.fixture
def microsoft(monkeypatch):
    """Puts the fake under every client the configuration builds, and makes the waits between retries instant."""
    fake = FakeMicrosoft()

    def build(tenant_id, client_id, client_secret, **options):
        if fake.deadline is not None:
            options["deadline"] = fake.deadline
        return SharePointClient(
            tenant_id,
            client_id,
            client_secret,
            transport=httpx.MockTransport(fake),
            sleep=lambda seconds: None,
            **options,
        )

    monkeypatch.setattr(sharepoint_config, "SharePointClient", build)
    return fake


def graph_error(status, code="generalException", message="Something went wrong", headers=None):
    return httpx.Response(status, json={"error": {"code": code, "message": message}}, headers=headers)


def token_error(status, error, number, description):
    return httpx.Response(
        status, json={"error": error, "error_description": f"AADSTS{number}: {description}", "error_codes": [number]}
    )


def run_test(client, site_url=None):
    return client.post(TEST_CONNECTION, {} if site_url is None else {"site_url": site_url}, format="json")


@pytest.mark.contract
@pytest.mark.django_db
class TestWhoMayTestTheConnection:
    def test_anonymous_cannot(self, api_client, instance, credentials, microsoft):
        assert run_test(api_client).status_code in (401, 403)
        assert microsoft.requests == []

    def test_a_person_who_is_not_an_instance_admin_cannot(self, session_client, instance, credentials, microsoft):
        assert run_test(session_client).status_code == 403
        assert microsoft.requests == []

    def test_an_instance_admin_of_too_low_a_role_cannot(self, api_client, instance, credentials, microsoft):
        member = User.objects.create(email="member@plane.so", username=uuid4().hex)
        InstanceAdmin.objects.create(instance=instance, user=member, role=5)
        api_client.force_authenticate(user=member)
        assert run_test(api_client).status_code == 403
        assert microsoft.requests == []

    def test_the_path_goes_to_the_admin_session(self):
        # SessionMiddleware reads the God Mode cookie for every path with "instances" in it, and only for those
        assert "instances" in TEST_CONNECTION


def signed_in_session(user):
    """
    The key of a session in which `user` is signed in, made the way the sign-in endpoints make it (Django's
    ``login()`` on the project's session store), so a request carrying it goes through the real session middleware
    and session authentication instead of ``force_authenticate``.
    """
    request = RequestFactory().post("/api/instances/admins/sign-in/")
    request.session = SessionStore()
    login(request, user)
    request.session.save()
    return request.session.session_key


@pytest.mark.contract
@pytest.mark.django_db
class TestTheGodModeSession:
    """`/api/instances/*` is authenticated by the God Mode cookie (`admin-session-id`) only."""

    def test_the_god_mode_cookie_lets_an_instance_admin_test(self, api_client, instance_admin, credentials, microsoft):
        api_client.cookies[django_settings.ADMIN_SESSION_COOKIE_NAME] = signed_in_session(instance_admin.user)
        response = run_test(api_client)
        assert response.status_code == 200, response.data
        assert microsoft.hosts() == ["login.microsoftonline.com"]

    def test_the_web_app_cookie_is_not_enough(self, api_client, instance_admin, credentials, microsoft):
        # The same signed-in session, sent as the cookie of the web app: the instance paths do not read it
        api_client.cookies[django_settings.SESSION_COOKIE_NAME] = signed_in_session(instance_admin.user)
        assert run_test(api_client).status_code in (401, 403)
        assert microsoft.requests == []

    def test_a_god_mode_session_of_someone_who_is_not_an_admin_is_refused(
        self, api_client, instance, credentials, microsoft
    ):
        member = User.objects.create(email="member@plane.so", username=uuid4().hex)
        api_client.cookies[django_settings.ADMIN_SESSION_COOKIE_NAME] = signed_in_session(member)
        assert run_test(api_client).status_code == 403
        assert microsoft.requests == []

    def test_a_request_from_another_site_is_refused(self, api_client, instance_admin, credentials, microsoft):
        # Cookie-authenticated writes must come from Pi-Plane's own origins
        api_client.cookies[django_settings.ADMIN_SESSION_COOKIE_NAME] = signed_in_session(instance_admin.user)
        response = api_client.post(TEST_CONNECTION, {}, format="json", HTTP_ORIGIN="https://evil.example")
        assert response.status_code == 403
        assert microsoft.requests == []


@pytest.mark.contract
@pytest.mark.django_db
class TestTheConnectionTest:
    def test_without_a_site_only_the_sign_in_is_tried(self, session_client, instance_admin, credentials, microsoft):
        response = run_test(session_client)
        assert response.status_code == 200, response.data
        assert response.data == {"site": None, "libraries": []}
        (request,) = microsoft.requests
        assert str(request.url) == f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
        form = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        # The saved secret was decrypted and is what Microsoft is sent
        assert (form["client_id"], form["client_secret"], form["grant_type"]) == (
            CLIENT_ID,
            SECRET,
            "client_credentials",
        )

    def test_with_a_site_its_name_and_libraries_come_back(self, session_client, instance_admin, credentials, microsoft):
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 200, response.data
        assert response.data["site"] == {"id": SITE_ID, "name": "Projects", "web_url": SITE_URL}
        assert response.data["libraries"] == [
            {"id": "b!one", "name": "Documents", "web_url": f"{SITE_URL}/Shared%20Documents"},
            {"id": "b!two", "name": "Artwork", "web_url": f"{SITE_URL}/Artwork"},
        ]
        token, site, drives = microsoft.requests
        assert site.url.path == "/v1.0/sites/contoso.sharepoint.com:/sites/Projects"
        assert drives.url.path == f"/v1.0/sites/{SITE_ID}/drives"

    def test_it_works_while_the_integration_is_still_switched_off(
        self, session_client, instance_admin, credentials, microsoft
    ):
        assert InstanceConfiguration.objects.get(key="IS_SHAREPOINT_ENABLED").value == "0"
        assert run_test(session_client, SITE_URL).status_code == 200

    def test_every_test_signs_in_anew(self, session_client, instance_admin, credentials, microsoft):
        # A token in the cache must not hide a secret that has stopped working
        run_test(session_client)
        run_test(session_client)
        assert microsoft.hosts() == ["login.microsoftonline.com"] * 2

    def test_nothing_is_tried_before_the_credentials_are_saved(self, session_client, instance_admin, rows, microsoft):
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 400
        assert response.data["error_code"] == "not_configured"
        assert microsoft.requests == []

    def test_incomplete_credentials_are_not_configured(self, session_client, instance_admin, rows, microsoft):
        store(SHAREPOINT_TENANT_ID=TENANT, SHAREPOINT_CLIENT_ID=CLIENT_ID)
        assert run_test(session_client).data["error_code"] == "not_configured"
        assert microsoft.requests == []

    def test_the_rows_may_be_missing_altogether(self, session_client, instance_admin, microsoft):
        assert run_test(session_client).data["error_code"] == "not_configured"

    @pytest.mark.parametrize(
        "site_url",
        [
            "http://contoso.sharepoint.com/sites/Projects",
            "https://evil.example/sites/Projects",
            "https://contoso.sharepoint.com.evil.example/sites/Projects",
            "https://169.254.169.254/latest/meta-data",
            "https://contoso.sharepoint.com/sites/../../users",
            "not a url",
        ],
    )
    def test_an_address_that_is_not_a_sharepoint_site_sends_nothing(
        self, session_client, instance_admin, credentials, microsoft, site_url
    ):
        response = run_test(session_client, site_url)
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_site_url"
        assert microsoft.requests == []

    @pytest.mark.parametrize(
        "answer, code",
        [
            (token_error(401, "invalid_client", 7000215, "Invalid client secret provided."), "invalid_credentials"),
            (token_error(401, "invalid_client", 7000222, "The client secret keys are expired."), "secret_expired"),
            (token_error(400, "unauthorized_client", 700016, "Application not found."), "application_not_found"),
            (token_error(400, "invalid_request", 90002, "Tenant not found."), "tenant_not_found"),
            (httpx.Response(400, json={"error": "invalid_scope"}), "authentication_failed"),
            (httpx.Response(500, json={"error": "server_error"}), "unexpected_response"),
            (httpx.ConnectError("no route"), "transport_error"),
            (httpx.ReadTimeout("timed out"), "transport_error"),
            (httpx.Response(429, headers={"Retry-After": "3600"}), "throttled"),
        ],
    )
    def test_a_failed_sign_in_says_which_failure_it_is(
        self, session_client, instance_admin, credentials, microsoft, answer, code
    ):
        microsoft.token_answer = answer
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 400
        assert response.data["error_code"] == code
        assert response.data["error"]
        # The site is not asked for when the sign-in did not work
        assert "graph.microsoft.com" not in microsoft.hosts()

    def test_the_failures_read_differently(self, session_client, instance_admin, credentials, microsoft):
        messages = set()
        for answer in (
            token_error(401, "invalid_client", 7000215, "Invalid client secret provided."),
            token_error(400, "invalid_request", 90002, "Tenant not found."),
            token_error(400, "unauthorized_client", 700016, "Application not found."),
        ):
            microsoft.token_answer = answer
            messages.add(run_test(session_client).data["error"])
        assert len(messages) == 3

    def test_a_site_the_app_was_not_granted_is_named_as_such(
        self, session_client, instance_admin, credentials, microsoft
    ):
        # What Sites.Selected is expected to answer for a site the app has no grant for
        microsoft.site_answer = graph_error(403, "accessDenied", "Access denied")
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 400
        assert response.data["error_code"] == "site_access_denied"
        assert "Sites.Selected" in response.data["error"]
        assert response.data["detail"] == "accessDenied: Access denied"

    def test_access_refused_to_the_libraries_is_the_same_case(
        self, session_client, instance_admin, credentials, microsoft
    ):
        microsoft.drives_answer = graph_error(403, "accessDenied", "Access denied")
        assert run_test(session_client, SITE_URL).data["error_code"] == "site_access_denied"

    def test_a_site_that_is_not_there(self, session_client, instance_admin, credentials, microsoft):
        microsoft.site_answer = graph_error(404, "itemNotFound", "Requested site could not be found")
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 400
        assert response.data["error_code"] == "site_not_found"

    def test_a_token_graph_does_not_accept(self, session_client, instance_admin, credentials, microsoft):
        microsoft.site_answer = graph_error(401, "InvalidAuthenticationToken", "Access token validation failure.")
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 400
        assert response.data["error_code"] == "token_rejected"

    def test_graph_throttling(self, session_client, instance_admin, credentials, microsoft):
        microsoft.site_answer = graph_error(429, "TooManyRequests", headers={"Retry-After": "3600"})
        assert run_test(session_client, SITE_URL).data["error_code"] == "throttled"

    def test_graph_out_of_reach(self, session_client, instance_admin, credentials, microsoft):
        microsoft.site_answer = httpx.ConnectError("no route")
        assert run_test(session_client, SITE_URL).data["error_code"] == "transport_error"

    def test_running_out_of_time_says_so(self, session_client, instance_admin, credentials, microsoft):
        # The deadline is already used up: nothing is sent, and the answer names the time-out
        microsoft.deadline = 0
        response = run_test(session_client, SITE_URL)
        assert response.status_code == 400
        assert response.data["error_code"] == "timeout"
        assert "seconds" in response.data["error"]
        assert microsoft.requests == []

    def test_the_test_has_the_default_deadline(self, monkeypatch, instance_admin, credentials):
        built = {}

        def build(*args, **options):
            built.update(options)
            raise SharePointConfigurationError("stop here")

        monkeypatch.setattr(sharepoint_config, "SharePointClient", build)
        with pytest.raises(SharePointConfigurationError):
            get_sharepoint_client(require_enabled=False)
        # Nothing overrides the client's own deadline (DEFAULT_DEADLINE), which is well under proxy time-outs
        assert "deadline" not in built

    def test_another_graph_error(self, session_client, instance_admin, credentials, microsoft):
        microsoft.site_answer = graph_error(500)
        assert run_test(session_client, SITE_URL).data["error_code"] == "unexpected_response"

    def test_no_answer_holds_the_secret_or_a_token(self, session_client, instance_admin, credentials, microsoft):
        answers = [run_test(session_client, SITE_URL)]
        # Graph quoting back the very token it was sent, and the secret
        microsoft.site_answer = lambda request: graph_error(
            403, "accessDenied", f"{request.headers['Authorization']} {SECRET}"
        )
        answers.append(run_test(session_client, SITE_URL))
        microsoft.token_answer = token_error(401, "invalid_client", 7000215, f"Invalid client secret '{SECRET}'.")
        answers.append(run_test(session_client, SITE_URL))
        for answer in answers:
            text = str(answer.data)
            assert SECRET not in text
            assert "token-" not in text

    def test_a_saved_tenant_that_cannot_be_one_is_refused_without_a_request(
        self, session_client, instance_admin, credentials, microsoft
    ):
        # Not reachable through the admin app, which validates on saving; a row edited by hand must not be trusted
        store(SHAREPOINT_TENANT_ID="common/../../evil")
        response = run_test(session_client)
        assert response.status_code == 400
        assert response.data["error_code"] == "invalid_tenant_id"
        assert microsoft.requests == []


@pytest.mark.contract
@pytest.mark.django_db
class TestSavingTheConfiguration:
    def save(self, client, **values):
        return client.patch(CONFIGURATIONS, values, format="json")

    def test_the_credentials_are_saved_and_the_secret_is_stored_encrypted(self, session_client, instance_admin, rows):
        response = self.save(
            session_client,
            IS_SHAREPOINT_ENABLED="1",
            SHAREPOINT_TENANT_ID=f" {TENANT} ",
            SHAREPOINT_CLIENT_ID=CLIENT_ID,
            SHAREPOINT_CLIENT_SECRET=SECRET,
            SHAREPOINT_MAX_FILE_SIZE=str(200 * MB),
        )
        assert response.status_code == 200, response.data
        stored = dict(InstanceConfiguration.objects.filter(key__in=KEYS).values_list("key", "value"))
        assert stored["SHAREPOINT_TENANT_ID"] == TENANT
        assert stored["SHAREPOINT_CLIENT_SECRET"] != SECRET
        assert SECRET not in stored["SHAREPOINT_CLIENT_SECRET"]
        assert decrypt_data(stored["SHAREPOINT_CLIENT_SECRET"]) == SECRET
        settings = get_sharepoint_settings()
        assert (settings.enabled, settings.tenant_id, settings.client_id, settings.client_secret) == (
            True,
            TENANT,
            CLIENT_ID,
            SECRET,
        )
        assert settings.max_file_size == 200 * MB

    def test_a_tenant_domain_is_accepted(self, session_client, instance_admin, rows):
        assert self.save(session_client, SHAREPOINT_TENANT_ID="contoso.onmicrosoft.com").status_code == 200

    @pytest.mark.parametrize(
        "values",
        [
            {"SHAREPOINT_TENANT_ID": "common/../evil"},
            {"SHAREPOINT_TENANT_ID": "not a tenant"},
            {"SHAREPOINT_CLIENT_ID": "my-app"},
            {"SHAREPOINT_MAX_FILE_SIZE": "abc"},
            {"SHAREPOINT_MAX_FILE_SIZE": "1.5"},
            {"SHAREPOINT_MAX_FILE_SIZE": "-5"},
            {"SHAREPOINT_MAX_FILE_SIZE": str(MB - 1)},
            {"SHAREPOINT_MAX_FILE_SIZE": str(MAX_MAX_FILE_SIZE + 1)},
            {"IS_SHAREPOINT_ENABLED": "yes"},
        ],
    )
    def test_a_value_that_cannot_work_is_refused(self, session_client, instance_admin, rows, values):
        response = self.save(session_client, SHAREPOINT_CLIENT_SECRET=SECRET, **values)
        assert response.status_code == 400, response.data
        assert response.data["error"]
        # Nothing of the request is saved, the valid part neither
        assert InstanceConfiguration.objects.get(key="SHAREPOINT_CLIENT_SECRET").value == ""
        for key in values:
            assert InstanceConfiguration.objects.get(key=key).value in ("", "0")

    def test_empty_values_clear_the_settings(self, session_client, instance_admin, credentials):
        response = self.save(
            session_client,
            SHAREPOINT_TENANT_ID="",
            SHAREPOINT_CLIENT_ID="",
            SHAREPOINT_CLIENT_SECRET="",
            SHAREPOINT_MAX_FILE_SIZE="",
        )
        assert response.status_code == 200, response.data
        assert not get_sharepoint_settings().has_credentials
        assert get_sharepoint_max_file_size() == DEFAULT_MAX_FILE_SIZE

    def test_other_settings_are_saved_as_before(self, session_client, instance_admin, rows):
        InstanceConfiguration.objects.create(key="ENABLE_SIGNUP", value="1", category="AUTHENTICATION")
        assert self.save(session_client, ENABLE_SIGNUP="0").status_code == 200
        assert InstanceConfiguration.objects.get(key="ENABLE_SIGNUP").value == "0"

    def test_a_person_who_is_not_an_instance_admin_cannot_read_the_configuration(
        self, session_client, instance, credentials
    ):
        assert session_client.get(CONFIGURATIONS).status_code == 403


@pytest.mark.unit
@pytest.mark.django_db
class TestReadingTheSettings:
    def test_the_keys_are_seeded_in_a_category_of_their_own(self):
        seeded = {item["key"]: item for item in instance_config_variables if item["category"] == "SHAREPOINT"}
        assert sorted(seeded) == sorted(KEYS)
        assert [key for key, item in seeded.items() if item["is_encrypted"]] == ["SHAREPOINT_CLIENT_SECRET"]

    def test_nothing_saved_means_off_with_the_default_size(self, db):
        settings = get_sharepoint_settings()
        assert (settings.enabled, settings.has_credentials, settings.is_usable) == (False, False, False)
        assert settings.max_file_size == DEFAULT_MAX_FILE_SIZE == 500 * 1024 * 1024

    def test_garbage_as_the_size_means_the_default(self, rows):
        for value in ("lots", "12", str(MAX_MAX_FILE_SIZE * 2)):
            store(SHAREPOINT_MAX_FILE_SIZE=value)
            assert get_sharepoint_max_file_size() == DEFAULT_MAX_FILE_SIZE

    def test_switched_on_without_credentials_is_not_usable(self, rows):
        store(IS_SHAREPOINT_ENABLED="1", SHAREPOINT_TENANT_ID=TENANT, SHAREPOINT_CLIENT_ID=CLIENT_ID)
        assert get_sharepoint_settings().enabled
        assert not is_sharepoint_enabled()

    def test_a_client_is_only_built_when_switched_on(self, credentials):
        with pytest.raises(SharePointConfigurationError) as raised:
            get_sharepoint_client()
        assert raised.value.code == "disabled"
        store(IS_SHAREPOINT_ENABLED="1")
        get_sharepoint_client().close()

    def test_the_text_form_of_the_settings_holds_no_secret(self, credentials):
        settings = get_sharepoint_settings()
        assert settings.client_secret == SECRET
        assert SECRET not in repr(settings) and SECRET not in str(settings)

    @override_settings(SKIP_ENV_VAR=False)
    def test_the_environment_rules_when_the_database_is_skipped(self, credentials, monkeypatch):
        monkeypatch.setenv("SHAREPOINT_TENANT_ID", "contoso.onmicrosoft.com")
        monkeypatch.delenv("SHAREPOINT_CLIENT_SECRET", raising=False)
        settings = get_sharepoint_settings()
        assert settings.tenant_id == "contoso.onmicrosoft.com"
        assert settings.client_secret == ""


@pytest.mark.contract
@pytest.mark.django_db
class TestTheFlagTheAppsRead:
    def flag(self, client):
        return client.get(INSTANCE).data["config"]["is_sharepoint_enabled"]

    def test_off_until_it_is_switched_on_with_credentials(self, session_client, instance_admin, rows):
        assert self.flag(session_client) is False
        # Switched on, but there is nothing to sign in with yet
        assert session_client.patch(CONFIGURATIONS, {"IS_SHAREPOINT_ENABLED": "1"}, format="json").status_code == 200
        assert self.flag(session_client) is False
        response = session_client.patch(
            CONFIGURATIONS,
            {"SHAREPOINT_TENANT_ID": TENANT, "SHAREPOINT_CLIENT_ID": CLIENT_ID, "SHAREPOINT_CLIENT_SECRET": SECRET},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert self.flag(session_client) is True
        assert session_client.patch(CONFIGURATIONS, {"IS_SHAREPOINT_ENABLED": "0"}, format="json").status_code == 200
        assert self.flag(session_client) is False

    def test_the_instance_payload_holds_no_credentials(self, api_client, instance, credentials):
        store(IS_SHAREPOINT_ENABLED="1")
        text = str(api_client.get(INSTANCE).data)
        for confidential in (SECRET, TENANT, CLIENT_ID):
            assert confidential not in text

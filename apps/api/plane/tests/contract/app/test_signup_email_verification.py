# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""The email-and-password sign-up asks for a code sent to the address before the account is created."""

import json
import os
import uuid
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from plane.authentication.utils.signup_verification import KEY_PREFIX, MAX_CODES_PER_WINDOW, MAX_VERIFY_ATTEMPTS
from plane.db.models import User
from plane.license.models import Instance
from plane.settings.redis import redis_instance

EMAIL = "verify-me@plane.so"
PASSWORD = "Xk9#mQ2$vL7@pR4!"
SMTP_ON = {"EMAIL_HOST": "smtp.example.com"}


def _clear_redis(email=EMAIL):
    key = f"{KEY_PREFIX}{email}"
    redis_instance().delete(key, f"{key}:verify_attempts", f"{key}:issued")


@pytest.fixture(autouse=True)
def _clean_state():
    cache.delete_pattern("throttle_authentication_*")
    _clear_redis()
    yield
    cache.delete_pattern("throttle_authentication_*")
    _clear_redis()


@pytest.fixture
def setup_instance(db):
    instance = Instance.objects.first()
    if instance:
        instance.is_setup_done = True
        instance.save()
        return instance
    return Instance.objects.create(
        instance_name="Test Instance",
        instance_id=str(uuid.uuid4()),
        current_version="1.0.0",
        domain="http://localhost:8000",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def django_client():
    return Client(HTTP_USER_AGENT="Mozilla/5.0")


@pytest.fixture(autouse=True)
def _no_mail():
    with (
        patch("plane.authentication.views.signup_verification.send_one_time_code.delay") as send,
        patch("plane.authentication.adapter.base.user_activation_email"),
    ):
        yield send


def _issued_code(email=EMAIL):
    return json.loads(redis_instance().get(f"{KEY_PREFIX}{email}"))["code"]


def _request_code(api_client, email=EMAIL):
    return api_client.post(reverse("sign-up-verification-code"), {"email": email}, format="json")


@pytest.mark.contract
@patch.dict(os.environ, SMTP_ON)
class TestVerificationCodeEndpoint:
    def test_sends_a_code(self, api_client, setup_instance, _no_mail):
        response = _request_code(api_client)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"required": True}
        _no_mail.assert_called_once()
        assert _no_mail.call_args[0][0] == EMAIL
        assert _no_mail.call_args[0][2] == _issued_code()

    def test_rejects_an_invalid_email(self, api_client, setup_instance):
        response = _request_code(api_client, "not-an-email")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "INVALID_EMAIL_SIGN_UP"

    def test_rejects_an_existing_user(self, api_client, setup_instance, _no_mail):
        User.objects.create(email=EMAIL)

        response = _request_code(api_client)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "USER_ALREADY_EXIST"
        _no_mail.assert_not_called()

    def test_caps_the_codes_per_address(self, api_client, setup_instance):
        for _ in range(MAX_CODES_PER_WINDOW):
            assert _request_code(api_client).status_code == status.HTTP_200_OK

        response = _request_code(api_client)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_message"] == "SIGN_UP_VERIFICATION_CODE_ATTEMPT_EXHAUSTED"


@pytest.mark.contract
class TestVerificationNotRequired:
    @patch.dict(os.environ, {"EMAIL_HOST": ""})
    def test_without_smtp_no_code_is_asked_for(self, api_client, django_client, setup_instance, _no_mail):
        assert _request_code(api_client).data == {"required": False}
        _no_mail.assert_not_called()

        response = django_client.post(reverse("sign-up"), {"email": EMAIL, "password": PASSWORD})

        assert "error_code" not in response.url
        assert User.objects.filter(email=EMAIL).exists()

    @patch.dict(os.environ, {**SMTP_ON, "ENABLE_SIGNUP_EMAIL_VERIFICATION": "0"})
    def test_switched_off_no_code_is_asked_for(self, api_client, django_client, setup_instance):
        assert _request_code(api_client).data == {"required": False}

        response = django_client.post(reverse("sign-up"), {"email": EMAIL, "password": PASSWORD})

        assert "error_code" not in response.url
        assert User.objects.filter(email=EMAIL).exists()


@pytest.mark.contract
@patch.dict(os.environ, SMTP_ON)
@pytest.mark.parametrize("url_name", ["sign-up", "space-sign-up"])
class TestSignUpWithCode:
    def test_without_a_code_no_account_is_created(self, url_name, api_client, django_client, setup_instance):
        _request_code(api_client)

        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD})

        assert "SIGN_UP_VERIFICATION_CODE_REQUIRED" in response.url
        assert not User.objects.filter(email=EMAIL).exists()

    def test_without_a_requested_code_the_code_is_expired(self, url_name, django_client, setup_instance):
        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": "123456"})

        assert "EXPIRED_SIGN_UP_VERIFICATION_CODE" in response.url
        assert not User.objects.filter(email=EMAIL).exists()

    def test_a_wrong_code_creates_no_account(self, url_name, api_client, django_client, setup_instance):
        _request_code(api_client)
        wrong = "100000" if _issued_code() != "100000" else "100001"

        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": wrong})

        assert "INVALID_SIGN_UP_VERIFICATION_CODE" in response.url
        assert not User.objects.filter(email=EMAIL).exists()

    def test_the_right_code_creates_the_account(self, url_name, api_client, django_client, setup_instance):
        _request_code(api_client)

        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": _issued_code()})

        assert response.status_code == 302
        assert "error_code" not in response.url
        assert User.objects.get(email=EMAIL).check_password(PASSWORD)
        assert "_auth_user_id" in django_client.session
        # The code is used up
        assert not redis_instance().exists(f"{KEY_PREFIX}{EMAIL}")

    def test_the_code_stays_valid_after_a_weak_password(self, url_name, api_client, django_client, setup_instance):
        _request_code(api_client)
        code = _issued_code()

        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": "password", "code": code})
        assert "PASSWORD_TOO_WEAK" in response.url

        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": code})
        assert "error_code" not in response.url
        assert User.objects.filter(email=EMAIL).exists()

    def test_too_many_wrong_codes_drop_the_code(self, url_name, api_client, django_client, setup_instance):
        _request_code(api_client)
        code = _issued_code()
        wrong = "100000" if code != "100000" else "100001"

        for _ in range(MAX_VERIFY_ATTEMPTS - 1):
            response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": wrong})
            assert "INVALID_SIGN_UP_VERIFICATION_CODE" in response.url

        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": wrong})
        assert "SIGN_UP_VERIFICATION_CODE_ATTEMPT_EXHAUSTED" in response.url

        # Even the right code no longer works
        response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": code})
        assert "EXPIRED_SIGN_UP_VERIFICATION_CODE" in response.url
        assert not User.objects.filter(email=EMAIL).exists()

    def test_a_one_time_sign_in_code_is_not_accepted(self, url_name, api_client, django_client, setup_instance):
        """The codes of the passwordless sign-in live apart and cannot verify a password sign-up."""
        ri = redis_instance()
        ri.set(f"one_time_code_{EMAIL}", json.dumps({"current_attempt": 0, "email": EMAIL, "token": "654321"}), ex=600)
        try:
            response = django_client.post(reverse(url_name), {"email": EMAIL, "password": PASSWORD, "code": "654321"})
        finally:
            ri.delete(f"one_time_code_{EMAIL}")

        assert "EXPIRED_SIGN_UP_VERIFICATION_CODE" in response.url
        assert not User.objects.filter(email=EMAIL).exists()

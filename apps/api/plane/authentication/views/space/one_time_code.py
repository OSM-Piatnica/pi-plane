# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Django imports
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.views import View
from django.utils.http import url_has_allowed_host_and_scheme

# Third party imports
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Module imports
from plane.authentication.provider.credentials.one_time_code import OneTimeCodeProvider
from plane.authentication.utils.login import user_login
from plane.bgtasks.one_time_code_task import send_one_time_code
from plane.license.models import Instance
from plane.authentication.utils.host import base_host
from plane.db.models import User
from plane.authentication.adapter.error import (
    AuthenticationException,
    AUTHENTICATION_ERROR_CODES,
)
from plane.authentication.rate_limit import (
    AuthenticationThrottle,
    throttle_auth_redirect,
)
from plane.utils.path_validator import get_safe_redirect_url, validate_next_path, get_allowed_hosts


class OneTimeCodeGenerateSpaceEndpoint(APIView):
    permission_classes = [AllowAny]

    throttle_classes = [AuthenticationThrottle]

    def post(self, request):
        # Check if instance is configured
        instance = Instance.objects.first()
        if instance is None or not instance.is_setup_done:
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["INSTANCE_NOT_CONFIGURED"],
                error_message="INSTANCE_NOT_CONFIGURED",
            )
            return Response(exc.get_error_dict(), status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get("email", "").strip().lower()
        try:
            validate_email(email)
            adapter = OneTimeCodeProvider(request=request, key=email)
            key, token = adapter.initiate()
            # If the smtp is configured send through here
            send_one_time_code.delay(email, key, token, accept_language=request.headers.get("Accept-Language"))
            return Response({"key": str(key)}, status=status.HTTP_200_OK)
        except AuthenticationException as e:
            return Response(e.get_error_dict(), status=status.HTTP_400_BAD_REQUEST)


class OneTimeCodeSignInSpaceEndpoint(View):
    @throttle_auth_redirect(is_space=True)
    def post(self, request):
        # set the referer as session to redirect after login
        code = request.POST.get("code", "").strip()
        email = request.POST.get("email", "").strip().lower()
        next_path = request.POST.get("next_path")

        if code == "" or email == "":
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED"],
                error_message="MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED",
            )
            params = exc.get_error_dict()
            url = get_safe_redirect_url(
                base_url=base_host(request=request, is_space=True),
                next_path=next_path,
                params=params,
            )
            return HttpResponseRedirect(url)

        existing_user = User.objects.filter(email=email).first()

        if not existing_user:
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["USER_DOES_NOT_EXIST"],
                error_message="USER_DOES_NOT_EXIST",
            )
            params = exc.get_error_dict()
            url = get_safe_redirect_url(
                base_url=base_host(request=request, is_space=True),
                next_path=next_path,
                params=params,
            )
            return HttpResponseRedirect(url)

        # Active User
        try:
            provider = OneTimeCodeProvider(request=request, key=f"one_time_code_{email}", code=code)
            user = provider.authenticate()
            # Login the user and record his device info
            user_login(request=request, user=user, is_space=True)
            # redirect to referer path
            next_path = validate_next_path(next_path=next_path)
            url = f"{base_host(request=request, is_space=True).rstrip('/')}{next_path}"
            if url_has_allowed_host_and_scheme(url, allowed_hosts=get_allowed_hosts()):
                return HttpResponseRedirect(url)
            else:
                return HttpResponseRedirect(base_host(request=request, is_space=True))

        except AuthenticationException as e:
            params = e.get_error_dict()
            url = get_safe_redirect_url(
                base_url=base_host(request=request, is_space=True),
                next_path=next_path,
                params=params,
            )
            return HttpResponseRedirect(url)


class OneTimeCodeSignUpSpaceEndpoint(View):
    @throttle_auth_redirect(is_space=True)
    def post(self, request):
        # set the referer as session to redirect after login
        code = request.POST.get("code", "").strip()
        email = request.POST.get("email", "").strip().lower()
        next_path = request.POST.get("next_path")

        if code == "" or email == "":
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED"],
                error_message="MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED",
            )
            params = exc.get_error_dict()
            url = get_safe_redirect_url(
                base_url=base_host(request=request, is_space=True),
                next_path=next_path,
                params=params,
            )
            return HttpResponseRedirect(url)
        # Existing User
        existing_user = User.objects.filter(email=email).first()
        # Already existing
        if existing_user:
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["USER_ALREADY_EXIST"],
                error_message="USER_ALREADY_EXIST",
            )
            params = exc.get_error_dict()
            url = get_safe_redirect_url(
                base_url=base_host(request=request, is_space=True),
                next_path=next_path,
                params=params,
            )
            return HttpResponseRedirect(url)

        try:
            provider = OneTimeCodeProvider(request=request, key=f"one_time_code_{email}", code=code)
            user = provider.authenticate()
            # Login the user and record his device info
            user_login(request=request, user=user, is_space=True)
            # redirect to referer path
            next_path = validate_next_path(next_path=next_path)
            url = f"{base_host(request=request, is_space=True).rstrip('/')}{next_path}"
            if url_has_allowed_host_and_scheme(url, allowed_hosts=get_allowed_hosts()):
                return HttpResponseRedirect(url)
            else:
                return HttpResponseRedirect(base_host(request=request, is_space=True))

        except AuthenticationException as e:
            params = e.get_error_dict()
            url = get_safe_redirect_url(
                base_url=base_host(request=request, is_space=True),
                next_path=next_path,
                params=params,
            )
            return HttpResponseRedirect(url)

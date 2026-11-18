# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# Third party imports
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Module imports
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.rate_limit import AuthenticationThrottle
from plane.authentication.utils.signup_verification import (
    SignUpEmailVerification,
    is_signup_email_verification_required,
)
from plane.bgtasks.one_time_code_task import send_one_time_code
from plane.db.models import User
from plane.license.models import Instance


class SignUpVerificationCodeEndpoint(APIView):
    """Send the code that the email-and-password sign-up asks for (web app and Space use the same one).

    Answers ``{"required": false}`` when no code is asked for, so the sign-up form goes on without one.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthenticationThrottle]

    def post(self, request):
        try:
            instance = Instance.objects.first()
            if instance is None or not instance.is_setup_done:
                raise AuthenticationException(
                    error_code=AUTHENTICATION_ERROR_CODES["INSTANCE_NOT_CONFIGURED"],
                    error_message="INSTANCE_NOT_CONFIGURED",
                )

            if not is_signup_email_verification_required():
                return Response({"required": False}, status=status.HTTP_200_OK)

            email = str(request.data.get("email", "")).strip().lower()
            try:
                validate_email(email)
            except ValidationError:
                raise AuthenticationException(
                    error_code=AUTHENTICATION_ERROR_CODES["INVALID_EMAIL_SIGN_UP"],
                    error_message="INVALID_EMAIL_SIGN_UP",
                    payload={"email": email},
                )

            if User.objects.filter(email=email).exists():
                raise AuthenticationException(
                    error_code=AUTHENTICATION_ERROR_CODES["USER_ALREADY_EXIST"],
                    error_message="USER_ALREADY_EXIST",
                    payload={"email": email},
                )

            verification = SignUpEmailVerification(email)
            code = verification.issue()
            send_one_time_code.delay(
                email,
                verification.key,
                code,
                accept_language=request.headers.get("Accept-Language"),
                # the language picked on the sign-up form; the account and its profile do not exist yet
                language=request.data.get("language"),
                purpose="sign_up",
            )
            return Response({"required": True}, status=status.HTTP_200_OK)
        except AuthenticationException as e:
            return Response(e.get_error_dict(), status=status.HTTP_400_BAD_REQUEST)

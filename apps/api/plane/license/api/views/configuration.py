# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Python imports
import uuid
from smtplib import (
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
    SMTPServerDisconnected,
)

# Django imports
from django.core.mail import BadHeaderError, EmailMultiAlternatives, get_connection
from django.db.models import Q, Case, When, Value

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .base import BaseAPIView
from plane.db.models import Workspace
from plane.license.api.permissions import InstanceAdminPermission
from plane.license.models import InstanceConfiguration
from plane.license.api.serializers import InstanceConfigurationSerializer
from plane.license.utils.encryption import encrypt_data
from plane.utils.admin_message_limit import MAX_ADMIN_MESSAGE_LIMIT, MIN_ADMIN_MESSAGE_LIMIT
from plane.utils.cache import cache_response, invalidate_cache
from plane.utils.import_limits import (
    MAX_IMPORT_MAX_WORK_ITEMS,
    MIN_IMPORT_MAX_WORK_ITEMS,
    get_import_file_size_limit_max,
)
from plane.utils.file_size_limit import (
    MIN_FILE_SIZE_LIMIT,
    get_file_size_limit_max,
    parse_whole_number,
)
from plane.license.utils.instance_value import get_email_configuration


class InstanceConfigurationEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    @cache_response(60 * 60 * 2, user=False)
    def get(self, request):
        instance_configurations = InstanceConfiguration.objects.all()
        serializer = InstanceConfigurationSerializer(instance_configurations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @invalidate_cache(path="/api/instances/configurations/", user=False)
    @invalidate_cache(path="/api/instances/", user=False)
    def patch(self, request):
        if "INSTANCE_DEFAULT_WORKSPACE_ID" in request.data:
            default_workspace_id = str(request.data.get("INSTANCE_DEFAULT_WORKSPACE_ID") or "").strip()
            # Empty clears the choice; anything else has to name a workspace that exists.
            if default_workspace_id:
                try:
                    parsed_workspace_id = uuid.UUID(default_workspace_id)
                except ValueError:
                    return Response(
                        {"error": "The workspace selected for short links is not valid."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not Workspace.objects.filter(id=parsed_workspace_id).exists():
                    return Response(
                        {"error": "The workspace selected for short links does not exist."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Empty goes back to the default; anything else is a whole number in range
        size_ranges = {
            "FILE_SIZE_LIMIT": ("upload limit", MIN_FILE_SIZE_LIMIT, get_file_size_limit_max()),
            "IMPORT_FILE_SIZE_LIMIT": ("import file limit", MIN_FILE_SIZE_LIMIT, get_import_file_size_limit_max()),
        }
        for key, (name, minimum, maximum) in size_ranges.items():
            raw_limit = str(request.data.get(key) or "").strip() if key in request.data else ""
            if raw_limit:
                limit = parse_whole_number(raw_limit)
                if limit is None or limit < minimum or limit > maximum:
                    return Response(
                        {
                            "error": (
                                f"The {name} must be between {minimum // (1024 * 1024)} MB "
                                f"and {maximum // (1024 * 1024)} MB."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        if "IMPORT_MAX_WORK_ITEMS" in request.data:
            raw_count = str(request.data.get("IMPORT_MAX_WORK_ITEMS") or "").strip()
            if raw_count:
                count = parse_whole_number(raw_count)
                if count is None or count < MIN_IMPORT_MAX_WORK_ITEMS or count > MAX_IMPORT_MAX_WORK_ITEMS:
                    return Response(
                        {
                            "error": (
                                f"The number of work items per import must be between {MIN_IMPORT_MAX_WORK_ITEMS} "
                                f"and {MAX_IMPORT_MAX_WORK_ITEMS}."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        if "ADMIN_MESSAGE_LIMIT" in request.data:
            raw_limit = str(request.data.get("ADMIN_MESSAGE_LIMIT") or "").strip()
            if raw_limit:
                limit = parse_whole_number(raw_limit)
                if limit is None or limit < MIN_ADMIN_MESSAGE_LIMIT or limit > MAX_ADMIN_MESSAGE_LIMIT:
                    return Response(
                        {
                            "error": (
                                f"The number of messages to the admins per hour must be between "
                                f"{MIN_ADMIN_MESSAGE_LIMIT} and {MAX_ADMIN_MESSAGE_LIMIT}."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        configurations = InstanceConfiguration.objects.filter(key__in=request.data.keys())

        bulk_configurations = []
        for configuration in configurations:
            raw_value = request.data.get(configuration.key, configuration.value)
            value = "" if raw_value is None else str(raw_value).strip()
            if configuration.is_encrypted:
                configuration.value = encrypt_data(value)
            else:
                configuration.value = value
            bulk_configurations.append(configuration)

        InstanceConfiguration.objects.bulk_update(bulk_configurations, ["value"], batch_size=100)

        serializer = InstanceConfigurationSerializer(configurations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DisableEmailFeatureEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    @invalidate_cache(path="/api/instances/", user=False)
    def delete(self, request):
        try:
            InstanceConfiguration.objects.filter(
                Q(
                    key__in=[
                        "EMAIL_HOST",
                        "EMAIL_HOST_USER",
                        "EMAIL_HOST_PASSWORD",
                        "ENABLE_SMTP",
                        "EMAIL_PORT",
                        "EMAIL_FROM",
                    ]
                )
            ).update(value=Case(When(key="ENABLE_SMTP", then=Value("0")), default=Value("")))
            return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Failed to disable email configuration"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmailCredentialCheckEndpoint(BaseAPIView):
    def post(self, request):
        receiver_email = request.data.get("receiver_email", False)
        if not receiver_email:
            return Response(
                {"error": "Receiver email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        (
            EMAIL_HOST,
            EMAIL_HOST_USER,
            EMAIL_HOST_PASSWORD,
            EMAIL_PORT,
            EMAIL_USE_TLS,
            EMAIL_USE_SSL,
            EMAIL_FROM,
        ) = get_email_configuration()

        # Configure all the connections
        connection = get_connection(
            host=EMAIL_HOST,
            port=int(EMAIL_PORT),
            username=EMAIL_HOST_USER,
            password=EMAIL_HOST_PASSWORD,
            use_tls=EMAIL_USE_TLS == "1",
            use_ssl=EMAIL_USE_SSL == "1",
        )
        # Prepare email details
        subject = "Email Notification from Pi-Plane"
        message = "This is a sample email notification sent from Pi-Plane application."
        # Send the email
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=EMAIL_FROM,
                to=[receiver_email],
                connection=connection,
            )
            msg.send(fail_silently=False)
            return Response({"message": "Email successfully sent."}, status=status.HTTP_200_OK)
        except BadHeaderError:
            return Response({"error": "Invalid email header."}, status=status.HTTP_400_BAD_REQUEST)
        except SMTPAuthenticationError:
            return Response(
                {"error": "Invalid credentials provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPConnectError:
            return Response(
                {"error": "Could not connect with the SMTP server."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPSenderRefused:
            return Response(
                {"error": "From address is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPServerDisconnected:
            return Response(
                {"error": "SMTP server disconnected unexpectedly."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SMTPRecipientsRefused:
            return Response(
                {"error": "All recipient addresses were refused."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TimeoutError:
            return Response(
                {"error": "Timeout error while trying to connect to the SMTP server."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ConnectionError:
            return Response(
                {"error": "Network connection error. Please check your internet connection."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"error": "Could not send email. Please check your configuration"},
                status=status.HTTP_400_BAD_REQUEST,
            )

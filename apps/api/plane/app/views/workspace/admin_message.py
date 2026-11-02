# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.bgtasks.workspace_admin_message_notification import (
    ADMIN_MESSAGE_ENTITY,
    MESSAGE_LIMIT_WINDOW_SECONDS,
    MESSAGE_MAX_LENGTH,
    create_admin_message_notifications,
    email_workspace_admin_message,
)
from plane.db.models import Notification, Workspace
from plane.utils.admin_message_limit import get_admin_message_limit

from ..base import BaseAPIView


class WorkspaceAdminMessageEndpoint(BaseAPIView):
    """A person writes to the admins of their workspace (any member, guests too): inbox entry and email for each."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)

        message = str(request.data.get("message") or "").strip()
        if not message:
            return Response({"error": "Write a message first"}, status=status.HTTP_400_BAD_REQUEST)
        if len(message) > MESSAGE_MAX_LENGTH:
            return Response(
                {"error": f"The message can have at most {MESSAGE_MAX_LENGTH} characters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # One message makes one inbox entry per admin, all with the same entity id: those ids count the messages
        sent_recently = (
            Notification.objects.filter(
                workspace=workspace,
                entity_name=ADMIN_MESSAGE_ENTITY,
                triggered_by=request.user,
                created_at__gte=timezone.now() - timedelta(seconds=MESSAGE_LIMIT_WINDOW_SECONDS),
            )
            .order_by()
            .values("entity_identifier")
            .distinct()
            .count()
        )
        if sent_recently >= get_admin_message_limit():
            return Response(
                {"error": "You have sent several messages recently. Please try again later.", "code": "RATE_LIMITED"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        with transaction.atomic():
            message_id, recipients = create_admin_message_notifications(workspace, request.user, message)
        if message_id is None:
            return Response(
                {"error": "There is nobody else in this workspace to write to"}, status=status.HTTP_400_BAD_REQUEST
            )
        # only after the inbox entries are committed, so the task finds them
        transaction.on_commit(lambda: email_workspace_admin_message.delay(str(workspace.id), str(message_id)))
        return Response({"id": str(message_id), "recipients": len(recipients)}, status=status.HTTP_201_CREATED)

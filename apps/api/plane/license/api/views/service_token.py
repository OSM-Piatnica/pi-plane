# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bot tokens in God Mode: read-only API tokens of a workspace's service account, which sees every project."""

# Python imports
from datetime import datetime, time
from uuid import UUID

# Django imports
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import APIToken, BotTypeEnum, Workspace
from plane.license.api.permissions import InstanceAdminPermission
from plane.utils.service_account import (
    get_or_create_service_account,
    service_account_project_count,
    sync_service_account_projects,
)

from .base import BaseAPIView

LABEL_MAX_LENGTH = 255


def _service_tokens():
    return APIToken.objects.filter(user__is_bot=True, user__bot_type=BotTypeEnum.SERVICE_ACCOUNT).select_related(
        "workspace", "created_by", "user"
    )


def _parse_expiry(value):
    """An ISO date or date-time in the future, or None for a token that does not expire. Raises ValueError."""
    if value in (None, ""):
        return None
    moment = parse_datetime(str(value))
    if moment is None:
        day = parse_date(str(value))
        if day is None:
            raise ValueError("expired_at must be an ISO date or date-time")
        # a bare date means the token works through the whole of that day
        moment = datetime.combine(day, time.max)
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    if moment <= timezone.now():
        raise ValueError("expired_at must be in the future")
    return moment


def _serialize(token, project_counts):
    workspace = token.workspace
    creator = token.created_by
    return {
        "id": str(token.id),
        "label": token.label,
        "description": token.description,
        "workspace": str(workspace.id) if workspace else None,
        "workspace_detail": (
            {"id": str(workspace.id), "name": workspace.name, "slug": workspace.slug} if workspace else None
        ),
        # only the end of the token, to tell tokens apart; the whole token is shown once, when it is created
        "token_hint": token.token[-4:],
        "is_active": token.is_active,
        "is_expired": bool(token.expired_at and token.expired_at <= timezone.now()),
        "expired_at": token.expired_at,
        "last_used": token.last_used,
        "created_at": token.created_at,
        "created_by_detail": (
            {"id": str(creator.id), "display_name": creator.display_name, "email": creator.email} if creator else None
        ),
        "project_count": project_counts.get(token.user_id, 0),
    }


class InstanceServiceTokenEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        tokens = list(_service_tokens())
        counts = {token.user_id: service_account_project_count(token.user) for token in tokens}
        return Response([_serialize(token, counts) for token in tokens], status=status.HTTP_200_OK)

    def post(self, request):
        workspace_ref = request.data.get("workspace")
        label = str(request.data.get("label") or "").strip()
        description = str(request.data.get("description") or "").strip()

        if not workspace_ref:
            return Response({"error": "Choose a workspace"}, status=status.HTTP_400_BAD_REQUEST)
        workspace = (
            Workspace.objects.filter(id=workspace_ref).first()
            if _looks_like_uuid(workspace_ref)
            else Workspace.objects.filter(slug=workspace_ref).first()
        )
        if workspace is None:
            return Response({"error": "The workspace does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        if not label:
            return Response({"error": "Give the token a name"}, status=status.HTTP_400_BAD_REQUEST)
        if len(label) > LABEL_MAX_LENGTH:
            return Response(
                {"error": f"The name can be at most {LABEL_MAX_LENGTH} characters long"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            expired_at = _parse_expiry(request.data.get("expired_at"))
        except ValueError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            account = get_or_create_service_account(workspace)
            sync_service_account_projects(account, workspace.id)
            token = APIToken.objects.create(
                user=account,
                user_type=1,
                workspace=workspace,
                label=label,
                description=description,
                expired_at=expired_at,
            )

        data = _serialize(token, {account.id: service_account_project_count(account)})
        # the only time the token is shown: it cannot be read back later
        data["token"] = token.token
        return Response(data, status=status.HTTP_201_CREATED)


class InstanceServiceTokenDetailEndpoint(BaseAPIView):
    permission_classes = [InstanceAdminPermission]

    def delete(self, request, pk):
        token = _service_tokens().filter(pk=pk).first()
        if token is None:
            return Response({"error": "The token does not exist"}, status=status.HTTP_404_NOT_FOUND)
        token.is_active = False
        token.save(update_fields=["is_active", "updated_at"])
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _looks_like_uuid(value) -> bool:
    try:
        UUID(str(value))
    except ValueError:
        return False
    return True

# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import Notification, User, UserGroup
from plane.db.models.user_group import GroupRole
from plane.utils.exception_logger import log_exception

GROUP_MEMBERSHIP_ENTITY = "group_membership"

ADDED = "added"
ROLE_CHANGED = "role_changed"


def _display_name(user):
    return user.display_name or f"{user.first_name} {user.last_name}".strip() or user.email


@shared_task
def notify_group_membership(group_id, user_id, actor_id, event, role):
    """Tell a person, in the inbox, that they were added to a group or that their role in it changed.

    Only changes made by hand are announced: the ones the sign-in sync makes for a group managed outside are not.
    """
    try:
        if actor_id is not None and str(actor_id) == str(user_id):
            return
        group = UserGroup.objects.get(pk=group_id)
        receiver = User.objects.filter(pk=user_id, is_active=True, is_bot=False).first()
        if receiver is None:
            return
        actor = User.objects.filter(pk=actor_id).first() if actor_id is not None else None
        role_name = "admin" if int(role) == GroupRole.ADMIN else "member"

        actor_name = _display_name(actor) if actor else ""
        if event == ADDED:
            title = f"{actor_name} added you to the group {group.name}"
        else:
            title = f"{actor_name} changed your role in the group {group.name} to {role_name}"
        Notification.objects.create(
            workspace_id=group.workspace_id,
            receiver=receiver,
            triggered_by=actor,
            entity_name=GROUP_MEMBERSHIP_ENTITY,
            entity_identifier=group.id,
            sender=f"in_app:{GROUP_MEMBERSHIP_ENTITY}",
            title=title.strip(),
            data={
                "group_membership": {
                    "group": {"id": str(group.id), "name": group.name},
                    "event": event,
                    "role": role_name,
                }
            },
        )
    except Exception as e:
        log_exception(e)
        logging.getLogger("plane.worker").error("Group membership notification failed")

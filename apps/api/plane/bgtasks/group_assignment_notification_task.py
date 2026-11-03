# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import (
    Issue,
    Notification,
    ProjectMember,
    User,
    UserGroup,
    UserGroupMember,
    UserNotificationPreference,
)
from plane.db.models.user_group import GroupRole
from plane.utils.exception_logger import log_exception
from plane.utils.user_groups import member_user_ids

GROUP_ASSIGNMENT_ENTITY = "group_assignment"


def _display_name(user):
    return user.display_name or f"{user.first_name} {user.last_name}".strip() or user.email


def opted_in_user_ids(user_ids):
    """Who of the given people asked to hear about work assigned to their groups."""
    return set(
        UserNotificationPreference.objects.filter(
            user_id__in=user_ids, workspace__isnull=True, project__isnull=True, group_assignment=True
        ).values_list("user_id", flat=True)
    )


def group_assignment_recipients(groups, actor_id):
    """{user id: (group, "admin" | "member")} of the people to tell about work assigned to these groups.

    The admins of a group are always told. Its other members (the groups below it count) only when they opted in.
    Somebody in several of the groups is told once, as an admin if they administer any of them.
    """
    recipients = {}
    for group in groups:
        admin_ids = set(
            UserGroupMember.objects.filter(group=group, role=GroupRole.ADMIN).values_list("user_id", flat=True)
        )
        member_ids = member_user_ids(group.workspace_id, [group.id]) - admin_ids
        for user_id in admin_ids:
            recipients[user_id] = (group, "admin")
        for user_id in opted_in_user_ids(member_ids):
            recipients.setdefault(user_id, (group, "member"))
    recipients.pop(actor_id, None)
    return recipients


@shared_task
def notify_group_assignment(issue_id, group_ids, actor_id):
    """Tell the admins of the groups a work item was just assigned to, and the members who opted in, in the inbox."""
    try:
        issue = Issue.objects.select_related("project").get(pk=issue_id)
        groups = list(UserGroup.objects.filter(pk__in=group_ids).order_by("name"))
        actor = User.objects.filter(pk=actor_id).first()
        if not groups:
            return

        recipients = group_assignment_recipients(groups, actor.id if actor else None)
        # only people who are in the project (they are, through the group) can open the work item
        in_project = set(
            ProjectMember.objects.filter(
                project=issue.project, member_id__in=list(recipients), is_active=True
            ).values_list("member_id", flat=True)
        )
        receivers = User.objects.filter(pk__in=in_project, is_active=True, is_bot=False)

        actor_name = _display_name(actor) if actor else ""
        for receiver in receivers:
            group, role = recipients[receiver.id]
            Notification.objects.create(
                workspace_id=issue.workspace_id,
                project=issue.project,
                receiver=receiver,
                triggered_by=actor,
                entity_name=GROUP_ASSIGNMENT_ENTITY,
                entity_identifier=issue.id,
                sender=f"in_app:{GROUP_ASSIGNMENT_ENTITY}",
                title=f"{actor_name} assigned {group.name} to {issue.project.identifier}-{issue.sequence_id}".strip(),
                data={
                    "issue": {
                        "id": str(issue.id),
                        "name": str(issue.name),
                        "identifier": str(issue.project.identifier),
                        "sequence_id": issue.sequence_id,
                    },
                    "group_assignment": {"group": {"id": str(group.id), "name": group.name}, "role": role},
                },
            )
    except Exception as e:
        log_exception(e)
        logging.getLogger("plane.worker").error("Group assignment notification failed")


def queue_group_assignment_notifications(issue_id, previous_group_ids, new_group_ids, actor_id=None):
    """Tell about the groups that were added to the work item, not the ones it already had.

    The person making the change is the one signed in on this request, unless one is given.
    """
    if actor_id is None:
        from crum import get_current_user

        actor = get_current_user()
        actor_id = actor.id if actor and actor.is_authenticated else None
    added = [str(group_id) for group_id in set(new_group_ids or []) - set(previous_group_ids or [])]
    if added:
        notify_group_assignment.delay(str(issue_id), added, str(actor_id) if actor_id is not None else None)

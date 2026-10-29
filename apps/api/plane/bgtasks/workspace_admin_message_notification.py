# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
A message from a person to the admins of their workspace: an inbox entry for each admin, and an email to each.

The inbox entries are made by the request that carries the message (so that the limit on how many a person may send
counts them at once); the emails go out in the background, in the admin's language, with the sender's address as
Reply-To so that the admin answers the person directly.
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from plane.app.permissions import ROLE
from plane.db.models import Notification, User, UserNotificationPreference, Workspace, WorkspaceMember
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.email import generate_plain_text_from_html
from plane.utils.email_i18n import translate, user_language
from plane.utils.exception_logger import log_exception

ADMIN_MESSAGE_ENTITY = "workspace_admin_message"
TEMPLATE = "emails/notifications/workspace_admin_message.html"
# The longest message, and the window in which a person may send only so many (plane.utils.admin_message_limit)
MESSAGE_MAX_LENGTH = 2000
MESSAGE_LIMIT_WINDOW_SECONDS = 60 * 60


def display_name(user):
    return user.display_name or f"{user.first_name} {user.last_name}".strip() or user.email


def workspace_admin_recipients(workspace, sender_id):
    """The people who answer for a workspace: its active admins, other than the one writing."""
    admin_ids = (
        WorkspaceMember.objects.filter(workspace=workspace, role=ROLE.ADMIN.value, is_active=True)
        .exclude(member_id=sender_id)
        .values_list("member_id", flat=True)
    )
    return list(User.objects.filter(pk__in=admin_ids, is_active=True, is_bot=False))


def wants_admin_message_emails(user):
    """False when the admin turned off the emails about messages to the admins; the inbox entry is kept either way."""
    preference = UserNotificationPreference.objects.filter(
        user=user, workspace__isnull=True, project__isnull=True
    ).first()
    return preference is None or preference.workspace_admin_message


def create_admin_message_notifications(workspace, sender, message):
    """Put the message in the inbox of every admin. Returns (message id, the recipients), or (None, []) if none."""
    recipients = workspace_admin_recipients(workspace, sender.id)
    if not recipients:
        return None, []
    message_id = uuid.uuid4()
    sender_name = display_name(sender)
    Notification.objects.bulk_create(
        [
            Notification(
                workspace=workspace,
                receiver=receiver,
                entity_name=ADMIN_MESSAGE_ENTITY,
                entity_identifier=message_id,
                triggered_by=sender,
                sender=f"in_app:{ADMIN_MESSAGE_ENTITY}",
                title=f"{sender_name} wrote to the admins of {workspace.name}",
                message_stripped=message,
                data={
                    "workspace_admin_message": {
                        "id": str(message_id),
                        "message": message,
                        "sender_email": sender.email,
                    }
                },
            )
            for receiver in recipients
        ]
    )
    return message_id, recipients


def _send_email(receiver, context, subject, reply_to):
    html_content = render_to_string(TEMPLATE, context)
    text_content = generate_plain_text_from_html(html_content)
    (
        EMAIL_HOST,
        EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD,
        EMAIL_PORT,
        EMAIL_USE_TLS,
        EMAIL_USE_SSL,
        EMAIL_FROM,
    ) = get_email_configuration()
    connection = get_connection(
        host=EMAIL_HOST,
        port=int(EMAIL_PORT),
        username=EMAIL_HOST_USER,
        password=EMAIL_HOST_PASSWORD,
        use_tls=EMAIL_USE_TLS == "1",
        use_ssl=EMAIL_USE_SSL == "1",
    )
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=EMAIL_FROM,
        to=[receiver.email],
        reply_to=[reply_to],
        connection=connection,
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@shared_task
def email_workspace_admin_message(workspace_id, message_id):
    """Email a message to the admins it was sent to; the inbox entries of ``message_id`` say who they are."""
    try:
        workspace = Workspace.objects.get(pk=workspace_id)
    except Workspace.DoesNotExist:
        return
    notifications = Notification.objects.filter(
        workspace=workspace, entity_name=ADMIN_MESSAGE_ENTITY, entity_identifier=message_id
    ).select_related("receiver", "triggered_by")

    for notification in notifications:
        receiver, sender = notification.receiver, notification.triggered_by
        if sender is None or not receiver.is_active or not receiver.email:
            continue
        if not wants_admin_message_emails(receiver):
            continue
        sender_name = display_name(sender)
        language = user_language(receiver)
        context = {
            "email_language": language,
            "sender_name": sender_name,
            "sender_email": sender.email,
            "workspace_name": workspace.name,
            "request_message": notification.message_stripped,
            "email": receiver.email,
            "web_url": settings.WEB_URL or settings.APP_BASE_URL,
        }
        try:
            _send_email(
                receiver,
                context,
                translate(language, "workspace_admin_message.subject", sender=sender_name, workspace=workspace.name),
                reply_to=sender.email,
            )
            logging.getLogger("plane.worker").info("Workspace admin message email sent")
        except Exception as e:
            log_exception(e)

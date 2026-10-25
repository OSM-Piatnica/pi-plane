# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging

# Third party imports
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

# Module imports
from plane.app.permissions import ROLE
from plane.db.models import Notification, ProjectAccessRequest, ProjectMember, User
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.email import generate_plain_text_from_html
from plane.utils.email_i18n import translate, user_language
from plane.utils.exception_logger import log_exception

ACCESS_REQUEST_ENTITY = "project_access_request"


def access_request_recipients(project, requester_id):
    """Who has to decide on a request to join a project: its admins and its lead (if they still are members)."""
    receiver_ids = set(
        ProjectMember.objects.filter(project=project, role=ROLE.ADMIN.value, is_active=True).values_list(
            "member_id", flat=True
        )
    )
    if (
        project.project_lead_id
        and ProjectMember.objects.filter(project=project, member_id=project.project_lead_id, is_active=True).exists()
    ):
        receiver_ids.add(project.project_lead_id)
    receiver_ids.discard(requester_id)
    return list(User.objects.filter(pk__in=receiver_ids, is_active=True, is_bot=False))


def _display_name(user):
    return user.display_name or f"{user.first_name} {user.last_name}".strip() or user.email


def _send_email(receiver, context, subject, template="emails/notifications/project_access_request.html"):
    html_content = render_to_string(template, context)
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
        subject=subject, body=text_content, from_email=EMAIL_FROM, to=[receiver.email], connection=connection
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@shared_task
def notify_project_access_request(access_request_id):
    """Tell the people who can approve it, in the inbox and by email, that someone asked to join a Private project."""
    try:
        access_request = ProjectAccessRequest.objects.select_related("project", "project__workspace", "requester").get(
            pk=access_request_id, status=ProjectAccessRequest.PENDING
        )
    except ProjectAccessRequest.DoesNotExist:
        return

    project = access_request.project
    workspace = project.workspace
    requester = access_request.requester
    requester_name = _display_name(requester)
    web_url = settings.WEB_URL or settings.APP_BASE_URL
    review_url = f"{web_url}/{workspace.slug}/settings/projects/{project.id}/members/"

    for receiver in access_request_recipients(project, requester.id):
        # a request is announced once per receiver
        notification, created = Notification.objects.get_or_create(
            workspace=workspace,
            receiver=receiver,
            entity_name=ACCESS_REQUEST_ENTITY,
            entity_identifier=access_request.id,
            defaults={
                "project": project,
                "triggered_by": requester,
                "sender": f"in_app:{ACCESS_REQUEST_ENTITY}",
                "title": f"{requester_name} requested access to {project.name}",
                "message_stripped": access_request.message or None,
                "data": {
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "identifier": project.identifier,
                        "workspace_slug": workspace.slug,
                    },
                    "access_request": {"id": str(access_request.id), "message": access_request.message},
                },
            },
        )
        if not created:
            continue

        language = user_language(receiver)
        context = {
            "email_language": language,
            "requester_name": requester_name,
            "project_name": project.name,
            "workspace_name": workspace.name,
            "request_message": access_request.message,
            "email": receiver.email,
            "review_url": review_url,
        }
        try:
            _send_email(
                receiver,
                context,
                translate(language, "access_request.subject", requester=requester_name, project=project.name),
            )
            logging.getLogger("plane.worker").info("Access request email sent")
        except Exception as e:
            log_exception(e)


DECISION_TEMPLATE = "emails/notifications/project_access_request_decision.html"


@shared_task
def notify_project_access_request_decision(access_request_id):
    """Tell the person who asked to join a Private project, in the inbox and by email, how it was decided."""
    try:
        access_request = ProjectAccessRequest.objects.select_related(
            "project", "project__workspace", "requester", "decided_by"
        ).get(pk=access_request_id, status__in=[ProjectAccessRequest.APPROVED, ProjectAccessRequest.REJECTED])
    except ProjectAccessRequest.DoesNotExist:
        return

    requester = access_request.requester
    if not requester.is_active or requester.is_bot:
        return

    project = access_request.project
    workspace = project.workspace
    decider = access_request.decided_by
    decider_name = _display_name(decider) if decider else ""
    approved = access_request.status == ProjectAccessRequest.APPROVED
    outcome = "approved" if approved else "rejected"
    web_url = settings.WEB_URL or settings.APP_BASE_URL
    project_url = f"{web_url}/{workspace.slug}/projects/{project.id}/issues/"

    # a decision is announced once
    notification, created = Notification.objects.get_or_create(
        workspace=workspace,
        receiver=requester,
        entity_name=ACCESS_REQUEST_ENTITY,
        entity_identifier=access_request.id,
        defaults={
            "project": project,
            "triggered_by": decider,
            "sender": f"in_app:{ACCESS_REQUEST_ENTITY}",
            "title": (
                f"{decider_name} approved your request to join {project.name}"
                if approved
                else f"{decider_name} rejected your request to join {project.name}"
            ).strip(),
            "data": {
                "project": {
                    "id": str(project.id),
                    "name": project.name,
                    "identifier": project.identifier,
                    "workspace_slug": workspace.slug,
                },
                "access_request": {"id": str(access_request.id), "status": access_request.status},
            },
        },
    )
    if not created:
        return

    language = user_language(requester)
    context = {
        "email_language": language,
        "approved": approved,
        "decider_name": decider_name,
        "project_name": project.name,
        "workspace_name": workspace.name,
        "email": requester.email,
        "project_url": project_url,
    }
    try:
        _send_email(
            requester,
            context,
            translate(language, f"access_request_decision.subject_{outcome}", project=project.name),
            DECISION_TEMPLATE,
        )
        logging.getLogger("plane.worker").info("Access request decision email sent")
    except Exception as e:
        log_exception(e)

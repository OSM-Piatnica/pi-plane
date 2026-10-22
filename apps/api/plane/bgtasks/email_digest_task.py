# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging
from collections import Counter

# Third party imports
import pytz
from celery import shared_task

# Django imports
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

# Module imports
from plane.db.models import EmailNotificationLog, User, UserNotificationPreference
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.email import generate_plain_text_from_html
from plane.utils.exception_logger import log_exception


def digest_now():
    """Current time in the timezone the daily digest hour is expressed in."""
    return timezone.now().astimezone(pytz.timezone(settings.EMAIL_DIGEST_TIMEZONE))


def update_count_label(count):
    if count == 1:
        return "1 aktualizacja"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return f"{count} aktualizacje"
    return f"{count} aktualizacji"


@shared_task
def stack_email_digests(force_daily=False):
    """Hand every digest receiver's pending email logs over to send_email_digest.

    Runs every hour. Hourly digests go out on every tick, daily digests only at
    EMAIL_DIGEST_DAILY_HOUR (or when force_daily is set).
    """
    frequencies = ["hourly"]
    if force_daily or digest_now().hour == settings.EMAIL_DIGEST_DAILY_HOUR:
        frequencies.append("daily")

    receiver_ids = UserNotificationPreference.objects.filter(email_frequency__in=frequencies).values_list(
        "user_id", flat=True
    )
    pending = EmailNotificationLog.objects.filter(processed_at__isnull=True, receiver_id__in=list(receiver_ids))

    log_ids_by_receiver = {}
    for log_id, receiver_id in pending.values_list("id", "receiver_id"):
        log_ids_by_receiver.setdefault(str(receiver_id), []).append(log_id)

    for receiver_id, log_ids in log_ids_by_receiver.items():
        send_email_digest.delay(receiver_id=receiver_id, email_notification_ids=log_ids)
        EmailNotificationLog.objects.filter(pk__in=log_ids).update(processed_at=timezone.now())


def build_issue_rows(logs, web_url, actor_names):
    """One row per issue, in order of the first pending activity."""
    rows = {}
    for log in logs:
        data = log.data or {}
        issue = data.get("issue") or {}
        activity = data.get("issue_activity") or {}
        row = rows.setdefault(
            log.entity_identifier,
            {
                "identifier": f"{issue.get('identifier', '')}-{issue.get('sequence_id', '')}",
                "name": issue.get("name", ""),
                "url": f"{web_url}/{issue.get('workspace_slug', '')}/projects/{issue.get('project_id', '')}"
                f"/issues/{issue.get('id', '')}",
                "workspace_slug": issue.get("workspace_slug", ""),
                "count": 0,
                "comments": 0,
                "actors": Counter(),
            },
        )
        row["count"] += 1
        if activity.get("field") == "comment":
            row["comments"] += 1
        row["actors"][str(log.triggered_by_id)] += 1

    for row in rows.values():
        row["actors"] = ", ".join(
            actor_names.get(actor_id, "") for actor_id, _ in row["actors"].most_common() if actor_names.get(actor_id)
        )
        row["count_label"] = update_count_label(row["count"])
    return list(rows.values())


@shared_task
def send_email_digest(receiver_id, email_notification_ids):
    """Send one email summarising all the receiver's pending activity, one row per issue."""
    try:
        receiver = User.objects.get(pk=receiver_id)
        logs = list(EmailNotificationLog.objects.filter(pk__in=email_notification_ids).order_by("created_at"))
        if not logs:
            return

        web_url = settings.WEB_URL or settings.APP_BASE_URL
        actor_names = {
            str(user.id): user.display_name
            for user in User.objects.filter(id__in={log.triggered_by_id for log in logs})
        }
        issues = build_issue_rows(logs, web_url, actor_names)
        total = sum(issue["count"] for issue in issues)

        context = {
            "receiver_first_name": receiver.first_name,
            "summary_text": f"{update_count_label(total)} w {len(issues)} zadaniach, które obserwujesz.",
            "issues": issues,
            "preferences_url": f"{web_url}/{issues[0]['workspace_slug']}/settings/account/notifications/",
        }
        html_content = render_to_string("emails/notifications/issue-digest.html", context)
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
            subject=f"Podsumowanie: {update_count_label(total)} w {len(issues)} zadaniach",
            body=text_content,
            from_email=EMAIL_FROM,
            to=[receiver.email],
            connection=connection,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        EmailNotificationLog.objects.filter(pk__in=email_notification_ids).update(sent_at=timezone.now())
        logging.getLogger("plane.worker").info("Email digest sent successfully")
    except User.DoesNotExist:
        return
    except Exception as e:
        log_exception(e)
        return

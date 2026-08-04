from plane.db.models import Issue, IssueRelation
from plane.utils.issue_relation_constraints import (
    date_violation_message,
    is_status_transition_allowed,
    is_timeline_relation_satisfied,
    status_violation_message,
)
from plane.utils.issue_relation_mapper import get_inverse_relation


def issue_display_ref(issue) -> str:
    project = getattr(issue, "project", None)
    identifier = getattr(project, "identifier", None) if project is not None else None
    if identifier and issue.sequence_id is not None:
        return f"{identifier}-{issue.sequence_id}"
    return str(issue.id)


def _iter_timeline_constraints(issue):
    """
    Yield (relation_type_from_issue_perspective, related_issue) for SS/FF relations.
    DB stores only start_before / finish_before; reverse is inferred.
    """
    forward = (
        IssueRelation.objects.filter(
            issue_id=issue.id,
            relation_type__in=["start_before", "finish_before"],
        )
        .select_related("related_issue", "related_issue__state", "related_issue__project")
        .iterator()
    )
    for relation in forward:
        yield relation.relation_type, relation.related_issue

    reverse = (
        IssueRelation.objects.filter(
            related_issue_id=issue.id,
            relation_type__in=["start_before", "finish_before"],
        )
        .select_related("issue", "issue__state", "issue__project")
        .iterator()
    )
    for relation in reverse:
        yield get_inverse_relation(relation.relation_type), relation.issue


def validate_issue_timeline_relations(
    issue,
    *,
    start_date=None,
    target_date=None,
    state_group=None,
    check_dates=True,
    check_status=True,
):
    """
    Validate proposed dates / state group against timeline relations.
    Returns an error message string, or None when valid.
    """
    if issue is None or issue.id is None:
        return None

    issue_dates = {
        "start_date": start_date if start_date is not None else issue.start_date,
        "target_date": target_date if target_date is not None else issue.target_date,
    }
    if state_group is None:
        state_group = getattr(getattr(issue, "state", None), "group", None)

    issue_ref = issue_display_ref(issue)

    for relation_type, related in _iter_timeline_constraints(issue):
        related_ref = issue_display_ref(related)
        related_dates = {
            "start_date": related.start_date,
            "target_date": related.target_date,
        }
        related_group = getattr(getattr(related, "state", None), "group", None)

        if check_dates and not is_timeline_relation_satisfied(relation_type, issue_dates, related_dates):
            return date_violation_message(relation_type, issue_ref, related_ref)

        if check_status and state_group is not None:
            if not is_status_transition_allowed(relation_type, state_group, related_group):
                return status_violation_message(relation_type, issue_ref, related_ref)

    return None


def validate_issue_update_payload(issue, attrs):
    """
    Validate serializer attrs (partial update aware) against timeline relations.
    Only runs checks relevant to fields present in attrs.
    """
    if issue is None:
        return None

    check_dates = "start_date" in attrs or "target_date" in attrs
    check_status = "state" in attrs

    if not check_dates and not check_status:
        return None

    start_date = attrs["start_date"] if "start_date" in attrs else issue.start_date
    target_date = attrs["target_date"] if "target_date" in attrs else issue.target_date

    state_group = None
    if check_status:
        state = attrs.get("state")
        state_group = getattr(state, "group", None)

    return validate_issue_timeline_relations(
        issue,
        start_date=start_date,
        target_date=target_date,
        state_group=state_group if check_status else None,
        check_dates=check_dates,
        check_status=check_status,
    )


def validate_new_timeline_relation(issue, related_issue, relation_type):
    """
    Validate creating a timeline relation between two existing issues.
    `relation_type` is from the API perspective (may be reverse like start_after).
    """
    if relation_type not in {
        "start_before",
        "start_after",
        "finish_before",
        "finish_after",
    }:
        return None

    issue_dates = {"start_date": issue.start_date, "target_date": issue.target_date}
    related_dates = {
        "start_date": related_issue.start_date,
        "target_date": related_issue.target_date,
    }
    issue_group = getattr(getattr(issue, "state", None), "group", None)
    related_group = getattr(getattr(related_issue, "state", None), "group", None)
    issue_ref = issue_display_ref(issue)
    related_ref = issue_display_ref(related_issue)

    if not is_timeline_relation_satisfied(relation_type, issue_dates, related_dates):
        return date_violation_message(relation_type, issue_ref, related_ref)

    if not is_status_transition_allowed(relation_type, issue_group, related_group):
        return status_violation_message(relation_type, issue_ref, related_ref)

    return None


def get_issue_with_timeline_prefetch(issue_id):
    return (
        Issue.objects.select_related("state", "project")
        .filter(pk=issue_id)
        .first()
    )

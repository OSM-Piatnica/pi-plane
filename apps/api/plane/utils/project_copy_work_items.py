# Copyright (c) 2026-present Maciej Szymczak and contributors
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from the work item copy of Hangar (szymczag/hangar, AGPL-3.0-only).
# See the LICENSE file for details.

"""Copy a project's work items into a project that was just duplicated.

Configuration is copied synchronously by :mod:`plane.utils.project_duplicate`, inside one transaction
that holds a lock on the workspace row. Work items are unbounded, so they are copied here instead --
after that transaction has committed, by a background job, with the lock long gone.

What is copied is the work items that are plainly part of the project: drafts, archived items and
intake (triage) items are left behind. Comments, attachments, activity, time entries and subscribers
are never copied.

Four things about this are load-bearing and quiet if broken:

* ``bulk_create`` bypasses ``save()``. Every field ``Issue.save()`` would have derived --
  ``workspace``, ``sequence_id``, ``sort_order``, ``description_stripped`` -- is set explicitly here,
  and ``created_at`` needs a second pass because ``auto_now_add`` overwrites whatever insert supplies.
* A copy keeps the source's ``sequence_id``. That is what makes ``(project, sequence_id)`` a durable
  source-to-copy key, so a resumed job can rebuild its translation from two queries and skip what it
  already wrote. It is also why the synchronous path reserves the range first: nothing enforces
  uniqueness on ``(project, sequence)``, so an item somebody creates in the copy while this runs would
  otherwise silently take a number the copy still owes.
* Parents are linked in a second pass. Sub-items nest arbitrarily deep, and a flat remap after the
  fact needs no traversal and no ordering guarantee.
* Every pass is idempotent by skipping what the target already has. A job that dies mid-batch and is
  redispatched must add what is missing, never a second copy of what is not.
"""

from __future__ import annotations

import base64
import logging
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from bs4 import BeautifulSoup
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.html import strip_tags

from plane.bgtasks.copy_s3_object import extract_asset_ids, replace_asset_ids, sync_with_external_service
from plane.db.models import (
    CycleIssue,
    FileAsset,
    Issue,
    IssueAssignee,
    IssueLabel,
    IssueLink,
    IssuePropertyValue,
    IssueRelation,
    IssueSequence,
    ModuleIssue,
    ProjectIssueType,
    ProjectMember,
)
from plane.settings.storage import S3Storage
from plane.utils.path_validator import sanitize_filename

log = logging.getLogger(__name__)

# Big enough that the per-batch overhead is amortised, small enough that a killed worker loses little
# and a transaction stays short.
BATCH_SIZE = 500

# What a copy of the work items can carry, in groups for the interface. Everything is on unless the
# caller narrows it. Comments, attachments, activity, time entries and subscribers are not on offer:
# they are other people's words, files and hours.
WORK_ITEM_PROPERTY_GROUPS = {
    "content": ("dates", "custom_properties", "description_images"),
    "people": ("assignees",),
    "organization": ("labels", "cycles", "modules"),
    "hierarchy": ("parents", "relations", "links"),
}
WORK_ITEM_PROPERTIES = tuple(name for group in WORK_ITEM_PROPERTY_GROUPS.values() for name in group)


class InvalidWorkItemProperties(ValueError):
    """The requested properties are not a valid choice; ``unknown`` names the entries that are not options."""

    def __init__(self, message, unknown=()):
        super().__init__(message)
        self.unknown = list(unknown)


def resolve_work_item_properties(selected) -> list[str]:
    """The properties a copy carries: everything when no choice was made, else the ones named."""
    if selected is None:
        return list(WORK_ITEM_PROPERTIES)
    if not isinstance(selected, (list, tuple)) or not all(isinstance(name, str) for name in selected):
        raise InvalidWorkItemProperties("work_item_properties must be a list of names")

    unknown = sorted({name for name in selected if name not in WORK_ITEM_PROPERTIES})
    if unknown:
        raise InvalidWorkItemProperties(f"Unknown work item properties: {', '.join(unknown)}", unknown)

    chosen = set(selected)
    return [name for name in WORK_ITEM_PROPERTIES if name in chosen]


class StoredRemap:
    """The configuration translation, read back from the job row.

    The remap of the synchronous service lives only in memory inside the transaction that builds it.
    The job runs long after that, so the mapping is persisted as ``{namespace: {old_id: new_id}}`` and
    read back through this, which keeps the same call shape.
    """

    def __init__(self, entries: dict | None):
        self._entries = entries or {}

    def get(self, label: str, old_id):
        if old_id is None:
            return None
        return self._entries.get(label, {}).get(str(old_id))


@dataclass
class CopyTally:
    """What the job created, and what it deliberately did not."""

    counts: dict = field(default_factory=dict)
    skipped: list = field(default_factory=list)

    def add(self, label: str, count: int) -> None:
        if count:
            self.counts[label] = self.counts.get(label, 0) + count

    def note(self, reason: str) -> None:
        if reason not in self.skipped:
            self.skipped.append(reason)


def source_work_items(source_project_id):
    """The work items a copy carries, in a stable order.

    ``Issue.issue_objects`` already leaves out drafts, archived items and intake (triage) items:
    a draft is one author's unsaved composition, and the other two are not part of the live project.

    Ordering by ``sequence_id`` is what makes the cursor meaningful, and it is the same key the copy is
    written under.
    """
    return Issue.issue_objects.filter(project_id=source_project_id).order_by("sequence_id")


def existing_sequence_ids(target_project_id) -> set:
    """Work item numbers already present in the copy: whatever is here was written by an earlier attempt."""
    return set(Issue.objects.filter(project_id=target_project_id).values_list("sequence_id", flat=True))


def translation(source_project_id, target_project_id) -> dict:
    """Source work item id -> copied work item id.

    Derived rather than stored, because the copy shares the source's numbering: two queries and a dict
    join replace a map that would otherwise have to be persisted and kept in step with the rows.
    """
    source = dict(source_work_items(source_project_id).values_list("sequence_id", "id"))
    target = dict(Issue.objects.filter(project_id=target_project_id).values_list("sequence_id", "id"))
    return {source_id: target[sequence_id] for sequence_id, source_id in source.items() if sequence_id in target}


def count_source_work_items(source_project_id) -> int:
    return source_work_items(source_project_id).count()


def reserve_sequence_range(target_project, source_project_id) -> int:
    """Push the target's next work item number past the whole copied range.

    One row, ``issue=NULL`` and ``deleted=True`` -- which is what ``IssueSequence.issue`` being nullable
    is for. ``Issue.save()`` derives the next number from ``Max(sequence)``, so this makes an item
    created in the copy while the job runs land above everything the copy still owes. Without it the
    collision is silent: two items numbered alike, and no constraint to raise.
    """
    highest = (
        IssueSequence.objects.filter(project_id=source_project_id).aggregate(largest=Max("sequence"))["largest"] or 0
    )
    if highest:
        IssueSequence.objects.create(
            issue=None,
            sequence=highest,
            deleted=True,
            project=target_project,
            workspace_id=target_project.workspace_id,
        )
    return highest


def copy_issue_batch(*, sources, target_project, remap, type_ids, properties) -> list:
    """Insert one batch of work items and everything ``save()`` would have set.

    Returns the created rows. ``ignore_conflicts`` is deliberately not used: on PostgreSQL it makes the
    returned primary keys unreliable, and they are load-bearing here.
    """
    keep_dates = "dates" in properties
    rows = []
    for source in sources:
        # A type that is not available in the copy would be a dangling reference
        type_id = source.type_id if source.type_id in type_ids["available"] else type_ids["default"]
        rows.append(
            Issue(
                project=target_project,
                workspace_id=target_project.workspace_id,
                # Verbatim: this is the source-to-copy key.
                sequence_id=source.sequence_id,
                # Verbatim: somebody's manual ordering is content, not an index.
                sort_order=source.sort_order,
                name=source.name,
                description_html=source.description_html,
                description_json=source.description_json,
                description_binary=source.description_binary,
                # `save()` would have derived this; `bulk_create` will not.
                description_stripped=(None if not source.description_html else strip_tags(source.description_html)),
                priority=source.priority,
                point=source.point,
                start_date=source.start_date if keep_dates else None,
                target_date=source.target_date if keep_dates else None,
                duration=source.duration if keep_dates else None,
                completed_at=source.completed_at,
                is_draft=False,
                state_id=remap.get("state", source.state_id),
                estimate_point_id=remap.get("estimate_point", source.estimate_point_id),
                type_id=type_id,
                # Linked in a second pass once every row exists.
                parent=None,
                # Cleared, or a later import believes it already created rows it did not
                external_source=None,
                external_id=None,
                created_by_id=source.created_by_id,
            )
        )

    created = Issue.objects.bulk_create(rows, batch_size=BATCH_SIZE)

    IssueSequence.objects.bulk_create(
        [
            IssueSequence(
                issue=row,
                sequence=row.sequence_id,
                project=target_project,
                workspace_id=target_project.workspace_id,
            )
            for row in created
        ],
        batch_size=BATCH_SIZE,
    )

    # `created_at` is auto_now_add and `updated_at` is auto_now, so both were overwritten on insert.
    # `bulk_update` calls pre_save(add=False), under which neither re-applies -- this pass is the only
    # thing that makes "preserve the original dates" true.
    for source, row in zip(sources, created):
        row.created_at = source.created_at
        row.updated_at = source.updated_at
    Issue.objects.bulk_update(created, ["created_at", "updated_at"], batch_size=BATCH_SIZE)

    return created


@transaction.atomic
def link_parents(*, source_project_id, target_project, tally: CopyTally) -> None:
    """Second pass: rebuild the sub-item tree.

    Every work item was inserted with no parent, so this is a flat remap rather than a traversal.
    A parent that was not copied (an archived one, say) leaves the child at the top level, which is the
    only honest answer: the alternative is a foreign key pointing into the source project.
    """
    ids = translation(source_project_id, target_project.id)
    if not ids:
        return

    parented = source_work_items(source_project_id).exclude(parent_id=None).values_list("id", "parent_id")

    rows, dropped = [], 0
    for source_id, source_parent_id in parented:
        target_id = ids.get(source_id)
        if target_id is None:
            continue
        target_parent_id = ids.get(source_parent_id)
        if target_parent_id is None:
            dropped += 1
            continue
        rows.append(Issue(id=target_id, parent_id=target_parent_id))

    if rows:
        Issue.objects.bulk_update(rows, ["parent"], batch_size=BATCH_SIZE)
    tally.add("sub_items", len(rows))
    if dropped:
        tally.add("parents_dropped", dropped)
        tally.note("work_items:parent-dropped")


def _already_written(model, target_ids, field="issue_id") -> set:
    """Target work items this pass has already written rows for.

    Per issue rather than per row, and that is exact rather than approximate because each pass is
    atomic: an issue either has all of its rows for a model or none of them, so one row is proof the
    issue is done. This is what makes a resumed job add the remainder instead of a second copy.
    """
    return set(model.objects.filter(**{f"{field}__in": target_ids}).values_list(field, flat=True))


@transaction.atomic
def copy_satellites(*, source_project_id, target_project, ids, remap, properties, tally: CopyTally) -> None:
    """Labels, assignees, links, and cycle and module membership.

    Each is skipped, with a note, when it was not asked for or the thing it points at was not itself
    copied. Forcing cycles on because work items were asked for would copy other people's sprint
    planning without anybody requesting it.
    """
    source_ids = list(ids)
    if not source_ids:
        return

    stamp = {"project": target_project, "workspace_id": target_project.workspace_id}
    target_ids = list(ids.values())

    if "labels" in properties:
        done = _already_written(IssueLabel, target_ids)
        rows, seen = [], set()
        for issue_id, label_id in IssueLabel.objects.filter(issue_id__in=source_ids).values_list(
            "issue_id", "label_id"
        ):
            new_label_id = remap.get("label", label_id)
            key = (ids[issue_id], new_label_id)
            # IssueLabel has no unique constraint at all, so the source can hold duplicates
            if new_label_id is None or key in seen or ids[issue_id] in done:
                continue
            seen.add(key)
            rows.append(IssueLabel(issue_id=ids[issue_id], label_id=new_label_id, **stamp))
        IssueLabel.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        tally.add("labels", len(rows))
    else:
        tally.note("work_items:labels-not-copied")

    if "assignees" in properties:
        members = set(
            ProjectMember.objects.filter(project=target_project, is_active=True).values_list("member_id", flat=True)
        )
        done = _already_written(IssueAssignee, target_ids)
        rows, dropped = [], 0
        for issue_id, assignee_id in IssueAssignee.objects.filter(issue_id__in=source_ids).values_list(
            "issue_id", "assignee_id"
        ):
            if assignee_id not in members:
                dropped += 1
                continue
            if ids[issue_id] in done:
                continue
            rows.append(IssueAssignee(issue_id=ids[issue_id], assignee_id=assignee_id, **stamp))
        IssueAssignee.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        tally.add("assignees", len(rows))
        if dropped:
            tally.add("assignees_dropped", dropped)
            tally.note("work_items:assignees-not-in-copy")
    else:
        tally.note("work_items:assignees-not-copied")

    if "links" in properties:
        done = _already_written(IssueLink, target_ids)
        rows, seen = [], set()
        for link in IssueLink.objects.filter(issue_id__in=source_ids):
            if ids[link.issue_id] in done:
                continue
            key = (ids[link.issue_id], link.url)
            # Uniqueness of (url, issue) is a serializer rule, not a constraint
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                IssueLink(issue_id=ids[link.issue_id], title=link.title, url=link.url, metadata=link.metadata, **stamp)
            )
        IssueLink.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        tally.add("links", len(rows))
    else:
        tally.note("work_items:links-not-copied")

    # Cycle and module membership, only where the cycle or module came across
    for name, model, field_name, namespace in (
        ("cycles", CycleIssue, "cycle_id", "cycle"),
        ("modules", ModuleIssue, "module_id", "module"),
    ):
        if name not in properties:
            tally.note(f"work_items:{name}-not-copied")
            continue
        done = _already_written(model, target_ids)
        rows = []
        for issue_id, old_id in model.objects.filter(issue_id__in=source_ids).values_list("issue_id", field_name):
            new_id = remap.get(namespace, old_id)
            if new_id is None or ids[issue_id] in done:
                continue
            rows.append(model(issue_id=ids[issue_id], **{field_name: new_id}, **stamp))
        model.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        tally.add(f"{name}_membership", len(rows))


@transaction.atomic
def copy_property_values(*, source_project_id, target_project, ids, tally: CopyTally) -> None:
    """Custom work item property values.

    ``property_id`` is kept verbatim, which is correct and not an oversight: an ``IssueTypeProperty``
    hangs off ``IssueType``, which is workspace level, so a copy inside the same workspace needs no
    property rows of its own.
    """
    source_ids = list(ids)
    if not source_ids:
        return

    # A value whose property does not belong to the item's type is already hidden in the source; the
    # copy should not inherit it.
    types = dict(Issue.objects.filter(id__in=source_ids).values_list("id", "type_id"))
    members = {
        str(member_id)
        for member_id in ProjectMember.objects.filter(project=target_project, is_active=True).values_list(
            "member_id", flat=True
        )
    }

    done = _already_written(IssuePropertyValue, list(ids.values()))
    rows, stale, dropped_members = [], 0, 0
    for item in IssuePropertyValue.objects.filter(issue_id__in=source_ids).select_related("property"):
        if ids[item.issue_id] in done:
            continue
        if item.property.issue_type_id != types.get(item.issue_id):
            stale += 1
            continue
        value = item.value
        if item.property.property_type == "member_picker":
            # People who are not in the copy would be unreachable references
            people = value if isinstance(value, list) else ([value] if value else [])
            kept = [person for person in people if str(person) in members]
            if len(kept) != len(people):
                dropped_members += len(people) - len(kept)
            if people and not kept:
                continue
            value = kept if isinstance(value, list) else (kept[0] if kept else value)
        rows.append(
            IssuePropertyValue(
                issue_id=ids[item.issue_id],
                property_id=item.property_id,
                project=target_project,
                workspace_id=target_project.workspace_id,
                value=value,
            )
        )

    IssuePropertyValue.objects.bulk_create(rows, batch_size=BATCH_SIZE)
    tally.add("property_values", len(rows))
    if stale:
        tally.add("property_values_stale", stale)
    if dropped_members:
        tally.add("property_members_dropped", dropped_members)
        tally.note("work_items:property-members-not-in-copy")


@transaction.atomic
def copy_relations(*, source_project_id, target_project, ids, tally: CopyTally) -> None:
    """Relations, but only where both ends were copied.

    Both foreign keys point at ``Issue`` with nothing scoping them to a project, so copying a one-sided
    relation would attach the copy's items to the source's. A member of the copy would then see a
    "blocked by" they cannot open, and the source's items would start showing relations into a project
    their members have never heard of.
    """
    source_ids = set(ids)
    if not source_ids:
        return

    done = _already_written(IssueRelation, list(ids.values()))
    rows, dropped = [], 0
    for relation in IssueRelation.objects.filter(issue_id__in=source_ids):
        if relation.related_issue_id not in source_ids:
            dropped += 1
            continue
        if ids[relation.issue_id] in done:
            continue
        rows.append(
            IssueRelation(
                issue_id=ids[relation.issue_id],
                related_issue_id=ids[relation.related_issue_id],
                relation_type=relation.relation_type,
                project=target_project,
                workspace_id=target_project.workspace_id,
            )
        )

    IssueRelation.objects.bulk_create(rows, batch_size=BATCH_SIZE, ignore_conflicts=True)
    tally.add("relations", len(rows))
    if dropped:
        tally.add("relations_dropped", dropped)
        tally.note("work_items:relations-outside-copy")


def _remove_images(html: str, asset_ids: set[str]) -> str:
    """Take the named uploaded images out of a description, leaving the rest of it."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("image-component"):
        if tag.get("src") in asset_ids:
            tag.decompose()
    return str(soup)


def copy_description_images(*, source_project_id, target_project, ids, tally: CopyTally) -> None:
    """Give each copied work item its own copy of the images in its description.

    Left alone, the copy would point at the source's files, and deleting either project would take the
    other's images with it. An image that cannot be copied is removed from the copy's description
    instead of left pointing at the source: a broken image reads as a faulty copy, a missing one as a
    gap, and people in the copy may not be allowed to open the source's files at all.

    Deliberately outside a transaction: it copies objects in storage, which cannot be rolled back with
    the database. It is resumable instead -- an item is done once no image in its description still
    belongs to the source project. The description is written with a queryset update, not ``save()``,
    so the copy keeps its original ``updated_at``.
    """
    if not ids:
        return

    storage = S3Storage()
    copied = removed = 0
    for target_issue in Issue.objects.filter(id__in=list(ids.values()), description_html__contains="image-component"):
        asset_ids = extract_asset_ids(target_issue.description_html, "image-component")
        sources = {
            str(asset.id): asset
            for asset in FileAsset.objects.filter(
                id__in=asset_ids, workspace_id=target_project.workspace_id, project_id=source_project_id
            )
        }
        if not sources:
            continue

        duplicated, unreadable = [], set()
        for asset_id, original in sources.items():
            if not original.is_uploaded:
                unreadable.add(asset_id)
                continue
            try:
                name = (original.attributes or {}).get("name")
                key = f"{target_project.workspace_id}/{uuid.uuid4().hex}-{sanitize_filename(name) or 'unnamed'}"
                if storage.copy_object(original.asset.name, key) is None:
                    unreadable.add(asset_id)
                    continue
                new_asset = FileAsset.objects.create(
                    attributes={
                        "name": name,
                        "type": (original.attributes or {}).get("type"),
                        "size": (original.attributes or {}).get("size"),
                    },
                    asset=key,
                    size=original.size,
                    workspace_id=target_project.workspace_id,
                    created_by_id=original.created_by_id,
                    entity_type=original.entity_type,
                    project_id=target_project.id,
                    issue_id=target_issue.id,
                    storage_metadata=original.storage_metadata,
                    is_uploaded=True,
                )
            except Exception:
                log.warning("Could not copy a description image of work item %s", target_issue.id, exc_info=True)
                unreadable.add(asset_id)
                continue
            duplicated.append({"new_asset_id": str(new_asset.id), "old_asset_id": asset_id})

        html = replace_asset_ids(target_issue.description_html, "image-component", duplicated)
        if unreadable:
            html = _remove_images(html, unreadable)

        changes = {"description_html": html, "description_stripped": strip_tags(html)}
        # The editor opens the binary document, not the html, so it has to follow the new image ids
        external = sync_with_external_service("ISSUE", html)
        if external and external.get("description_json") and external.get("description_binary"):
            changes["description_json"] = external["description_json"]
            changes["description_binary"] = base64.b64decode(external["description_binary"])
        else:
            tally.note("work_items:descriptions-not-reconverted")
        Issue.objects.filter(pk=target_issue.pk).update(**changes)
        copied += len(duplicated)
        removed += len(unreadable)

    tally.add("description_images", copied)
    if removed:
        tally.add("description_images_removed", removed)
        tally.note("work_items:description-images-removed")


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------

LEASE_SECONDS = 300


def claim(job, task_id: str):
    """Take the lease, or return None because somebody else holds it.

    Re-read under a row lock so two workers handed the same job by a redelivered message cannot both
    decide they own it.
    """
    from plane.db.models import ProjectCopyJob

    with transaction.atomic():
        current = ProjectCopyJob.objects.select_for_update().get(pk=job.pk)
        now = timezone.now()
        held = current.lease_token is not None and current.lease_expires_at and current.lease_expires_at > now
        if current.is_terminal or held:
            return None

        current.status = ProjectCopyJob.Status.PROCESSING
        current.lease_token = uuid.uuid4()
        current.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        current.heartbeat_at = now
        current.started_at = current.started_at or now
        current.celery_task_id = task_id or ""
        current.attempt_count = current.attempt_count + 1
        current.save(
            update_fields=[
                "status",
                "lease_token",
                "lease_expires_at",
                "heartbeat_at",
                "started_at",
                "celery_task_id",
                "attempt_count",
                "updated_at",
            ]
        )
        return current


def still_ours(job) -> bool:
    """Whether this worker still holds the lease it claimed."""
    from plane.db.models import ProjectCopyJob

    return ProjectCopyJob.objects.filter(pk=job.pk, lease_token=job.lease_token).exists()


def copy_work_items(job) -> CopyTally:
    """Copy every work item the job's plan asks for, resuming if need be.

    Each batch commits its rows, the counter and the cursor together, so a worker killed between them
    is impossible: either all three landed or none did. Anything already present in the target is
    skipped, which is what makes a redispatched job add the remainder rather than a second copy.
    """
    from plane.db.models import ProjectCopyJob

    plan = job.plan or {}
    properties = set(plan.get("work_item_properties") or WORK_ITEM_PROPERTIES)
    remap = StoredRemap(job.remap)
    tally = CopyTally()
    target = job.target_project

    type_ids = _available_type_ids(target)
    already = existing_sequence_ids(target.id)

    pending = source_work_items(job.source_project_id).exclude(sequence_id__in=already)
    batch = []
    for source in pending.iterator(chunk_size=BATCH_SIZE):
        batch.append(source)
        if len(batch) < BATCH_SIZE:
            continue
        _commit_batch(job, batch, target, remap, type_ids, properties)
        batch = []
        if not still_ours(job):
            return tally
    if batch:
        _commit_batch(job, batch, target, remap, type_ids, properties)

    ids = translation(job.source_project_id, target.id)

    if "parents" in properties:
        _enter_stage(job, ProjectCopyJob.Stage.PARENTS)
        link_parents(source_project_id=job.source_project_id, target_project=target, tally=tally)
    else:
        tally.note("work_items:parents-not-copied")

    _enter_stage(job, ProjectCopyJob.Stage.SATELLITES)
    copy_satellites(
        source_project_id=job.source_project_id,
        target_project=target,
        ids=ids,
        remap=remap,
        properties=properties,
        tally=tally,
    )

    if "custom_properties" in properties:
        _enter_stage(job, ProjectCopyJob.Stage.PROPERTIES)
        copy_property_values(source_project_id=job.source_project_id, target_project=target, ids=ids, tally=tally)
    else:
        tally.note("work_items:custom-properties-not-copied")

    if "relations" in properties:
        _enter_stage(job, ProjectCopyJob.Stage.RELATIONS)
        copy_relations(source_project_id=job.source_project_id, target_project=target, ids=ids, tally=tally)
    else:
        tally.note("work_items:relations-not-copied")

    if "description_images" in properties:
        _enter_stage(job, ProjectCopyJob.Stage.ASSETS)
        copy_description_images(source_project_id=job.source_project_id, target_project=target, ids=ids, tally=tally)
    else:
        tally.note("work_items:description-images-not-copied")

    for note in ("comments", "attachments", "history", "worklogs", "subscribers"):
        tally.note(f"work_items:{note}-not-copied")

    return tally


def _enter_stage(job, stage) -> None:
    job.stage = stage
    job.save(update_fields=["stage", "updated_at"])


def _commit_batch(job, sources, target, remap, type_ids, properties) -> None:
    """One batch: the rows, the progress and the cursor, in one transaction."""
    with transaction.atomic():
        created = copy_issue_batch(
            sources=sources, target_project=target, remap=remap, type_ids=type_ids, properties=properties
        )
        job.copied = job.copied + len(created)
        job.cursor = sources[-1].sequence_id
        job.heartbeat_at = timezone.now()
        job.lease_expires_at = job.heartbeat_at + timedelta(seconds=LEASE_SECONDS)
        job.save(update_fields=["copied", "cursor", "heartbeat_at", "lease_expires_at", "updated_at"])


def _available_type_ids(target) -> dict:
    """Work item types the copy can actually use, and its default."""
    available = set()
    default_id = None
    for row in ProjectIssueType.objects.filter(project=target).select_related("issue_type"):
        available.add(row.issue_type_id)
        if row.is_default or row.issue_type.is_default:
            default_id = default_id or row.issue_type_id
    return {"available": available, "default": default_id}

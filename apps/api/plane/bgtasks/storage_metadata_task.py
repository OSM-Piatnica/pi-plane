# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
# See the LICENSE file for details.

# Django imports
from django.conf import settings

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import FileAsset
from plane.settings.storage import get_storage
from plane.utils.exception_logger import log_exception


def _exceeds_announced_size(asset):
    stored = (asset.storage_metadata or {}).get("ContentLength")
    return bool(asset.size) and isinstance(stored, (int, float)) and stored > asset.size


@shared_task
def get_asset_object_metadata(asset_id):
    try:
        # Get the asset
        asset = FileAsset.objects.get(pk=asset_id)
        # Create an instance of the S3 storage
        storage = get_storage()
        # Get the storage
        asset.storage_metadata = storage.get_object_metadata(object_name=asset.asset.name)
        # Azure cannot cap an upload when it is signed, so a file over the announced size is removed here
        if settings.STORAGE_PROVIDER == "azure" and _exceeds_announced_size(asset):
            storage.delete_files([asset.asset.name])
            asset.is_uploaded = False
            asset.is_deleted = True
            asset.save(update_fields=["storage_metadata", "is_uploaded", "is_deleted"])
            return
        # Save the asset
        asset.save(update_fields=["storage_metadata"])
        return
    except FileAsset.DoesNotExist:
        return
    except Exception as e:
        log_exception(e)
        return

/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueAttachment } from "@plane/types";
import { getFileURL } from "@plane/utils";
import { isPreviewable } from "@/components/document-viewer/helpers";
import type { TDocumentUrlSource } from "@/components/document-viewer/types";

/**
 * A work item attachment as a viewer source. Its URL is the API's attachment endpoint, which checks
 * access and redirects to the stored file; the same URL serves "Download".
 */
export const attachmentToDocumentSource = (attachment: TIssueAttachment): TDocumentUrlSource | undefined => {
  const url = getFileURL(attachment.asset_url ?? "");
  if (!url) return undefined;
  return {
    id: attachment.id,
    name: attachment.attributes.name,
    mimeType: attachment.attributes.type,
    url,
  };
};

export const isAttachmentPreviewable = (attachment: TIssueAttachment): boolean =>
  isPreviewable(attachment.attributes.type, attachment.attributes.name);

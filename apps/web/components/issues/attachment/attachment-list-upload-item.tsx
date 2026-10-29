/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// ui
import { CircularProgress } from "@makeplane/propel/components/circular-progress";
import { Tooltip } from "@makeplane/propel/components/tooltip";
// components
import { getFileExtension } from "@plane/utils";
import { getFileIcon } from "@/components/icons";
// helpers
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
// types
import type { TAttachmentUploadStatus } from "@/store/issue/issue-details/attachment.store";
import { useTranslation } from "@plane/i18n";

type Props = {
  uploadStatus: TAttachmentUploadStatus;
};

export const IssueAttachmentsUploadItem = observer(function IssueAttachmentsUploadItem(props: Props) {
  const { t } = useTranslation();
  // props
  const { uploadStatus } = props;
  // derived values
  const fileName = uploadStatus.name;
  const fileExtension = getFileExtension(uploadStatus.name ?? "");
  const fileIcon = getFileIcon(fileExtension, 18);
  // hooks
  const { isMobile } = usePlatformOS();

  return (
    <div className="pointer-events-none flex h-11 items-center justify-between gap-3 bg-surface-2 pr-2 pl-9">
      <div className="flex items-center gap-3 truncate text-13">
        <div className="flex-shrink-0">{fileIcon}</div>
        <Tooltip label={fileName} layout="stacked" disabled={isMobile}>
          <p className="truncate font-medium text-secondary">{fileName}</p>
        </Tooltip>
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        <span className="flex-shrink-0">
          <CircularProgress
            value={uploadStatus.progress}
            size="md"
            variant="brand"
            aria-label={t("app_text.attachments.upload_progress")}
          />
        </span>
        <div className="flex-shrink-0 text-13 font-medium">{uploadStatus.progress}% done</div>
      </div>
    </div>
  );
});

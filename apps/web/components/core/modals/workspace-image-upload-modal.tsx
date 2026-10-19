/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useDropzone } from "react-dropzone";
// plane imports
import { ACCEPTED_AVATAR_IMAGE_MIME_TYPES_FOR_REACT_DROPZONE, MAX_FILE_SIZE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogInfo,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { UserOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { EFileAssetType } from "@plane/types";
import { getAssetIdFromUrl, getFileURL, checkURLValidity } from "@plane/utils";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
// services
import { FileService } from "@/services/file.service";

type Props = {
  handleRemove: () => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (url: string) => void;
  value: string | null;
};

// services
const fileService = new FileService();

export const WorkspaceImageUploadModal = observer(function WorkspaceImageUploadModal(props: Props) {
  const { handleRemove, isOpen, onClose, onSuccess, value } = props;
  // states
  const [image, setImageState] = useState<File | null>(null);
  // object URL for the picked file, revoked when the file changes or the component unmounts
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const imagePreviewUrlRef = useRef<string | null>(null);
  const setImage = (file: File | null | undefined) => {
    if (imagePreviewUrlRef.current) URL.revokeObjectURL(imagePreviewUrlRef.current);
    // react-doctor-disable-next-line no-create-object-url-without-revoke -- the URL is kept in a ref and revoked on the next change and on unmount
    imagePreviewUrlRef.current = file ? URL.createObjectURL(file) : null;
    setImagePreviewUrl(imagePreviewUrlRef.current);
    setImageState(file ?? null);
  };
  useEffect(
    () => () => {
      if (imagePreviewUrlRef.current) URL.revokeObjectURL(imagePreviewUrlRef.current);
    },
    []
  );
  const [isRemoving, setIsRemoving] = useState(false);
  const [isImageUploading, setIsImageUploading] = useState(false);
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { currentWorkspace, updateWorkspaceLogo } = useWorkspace();
  const { t } = useTranslation();

  const onDrop = (acceptedFiles: File[]) => setImage(acceptedFiles[0]);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ACCEPTED_AVATAR_IMAGE_MIME_TYPES_FOR_REACT_DROPZONE,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
  });

  const handleClose = () => {
    setIsImageUploading(false);
    onClose();
    setTimeout(() => {
      setImage(null);
    }, 300);
  };

  const handleSubmit = async () => {
    if (!image || !workspaceSlug || !currentWorkspace) return;
    setIsImageUploading(true);

    try {
      const { asset_url } = await fileService.uploadWorkspaceAsset(
        workspaceSlug.toString(),
        {
          entity_identifier: currentWorkspace.id,
          entity_type: EFileAssetType.WORKSPACE_LOGO,
        },
        image
      );
      updateWorkspaceLogo(workspaceSlug.toString(), asset_url);
      onSuccess(asset_url);
    } catch (error: any) {
      console.log("error", error);
      setToast({
        type: "error",
        title: t("toast.error"),
        message: error.error || t("common.something_went_wrong"),
      });
    } finally {
      setIsImageUploading(false);
    }
  };

  const handleImageRemove = async () => {
    if (!workspaceSlug || !value) return;
    setIsRemoving(true);
    try {
      if (checkURLValidity(value)) {
        await fileService.deleteOldWorkspaceAsset(currentWorkspace?.id ?? "", value);
      } else {
        const assetId = getAssetIdFromUrl(value);
        await fileService.deleteWorkspaceAsset(workspaceSlug.toString(), assetId);
      }
      await handleRemove();
      handleClose();
    } catch (error) {
      console.log("Error in removing workspace asset:", error);
    } finally {
      setIsRemoving(false);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogContent size="sm">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>{t("onboarding.profile.upload_image")}</DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody tabIndex={0}>
            <div className="space-y-5">
              <div className="space-y-3">
                <div className="flex items-center justify-center gap-3">
                  <div
                    {...getRootProps()}
                    className={`relative grid h-80 w-80 cursor-pointer place-items-center rounded-lg p-12 text-center focus:ring-2 focus:ring-accent-strong focus:ring-offset-2 focus:outline-none ${
                      (image === null && isDragActive) || !value
                        ? "border-2 border-dashed border-subtle hover:bg-surface-2"
                        : ""
                    }`}
                  >
                    {image !== null || (value && value !== "") ? (
                      <>
                        <button
                          type="button"
                          className="absolute top-0 right-0 z-40 translate-x-1/2 -translate-y-1/2 rounded-sm bg-surface-2 px-2 py-0.5 text-11 font-medium text-secondary"
                        >
                          {t("common.edit")}
                        </button>
                        <img
                          src={imagePreviewUrl ?? (value ? getFileURL(value) : "")}
                          alt="Workspace logo preview"
                          className="absolute top-0 left-0 h-full w-full rounded-md object-cover"
                        />
                      </>
                    ) : (
                      <div>
                        <UserOutline className="mx-auto h-16 w-16 text-secondary" />
                        <span className="mt-2 block text-13 font-medium text-secondary">
                          {isDragActive
                            ? t("app_text.image_upload.drop_to_upload")
                            : t("app_text.image_upload.drag_and_drop")}
                        </span>
                      </div>
                    )}

                    <input {...getInputProps()} />
                  </div>
                </div>
                {fileRejections.length > 0 && (
                  <p className="text-13 text-danger-primary">
                    {fileRejections[0].errors[0].code === "file-too-large"
                      ? t("app_text.image_upload.size_exceeded")
                      : t("app_text.image_upload.invalid_format")}
                  </p>
                )}
              </div>
              <p className="text-13 text-secondary">{t("app_text.image_upload.formats_supported")}</p>
            </div>
          </DialogBody>
        </DialogMain>
        <DialogActions>
          <DialogInfo>
            <Button
              variant="danger"
              size="md"
              stretch="auto"
              label={isRemoving ? t("removing") : t("common.remove")}
              onClick={handleImageRemove}
              disabled={!value}
              loading={isRemoving}
            />
          </DialogInfo>
          <Button variant="secondary" size="md" stretch="auto" label={t("common.cancel")} onClick={handleClose} />
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            label={isImageUploading ? t("app_text.image_upload.uploading") : t("app_text.image_upload.upload_and_save")}
            onClick={handleSubmit}
            disabled={!image}
            loading={isImageUploading}
          />
        </DialogActions>
      </DialogContent>
    </Dialog>
  );
});

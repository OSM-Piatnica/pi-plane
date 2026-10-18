/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type React from "react";
import { useEffect, useEffectEvent, useState, useRef } from "react";
import { Controller, useForm } from "react-hook-form"; // services
import { WarningCircleOutline } from "@makeplane/propel/icons";
// plane imports
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Popover, PopoverBody, PopoverContent, PopoverTrigger } from "@makeplane/propel/components/popover";
import type { EditorRefApi } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { setToast } from "@plane/blocks/toast";
import { toSideAndAlign } from "@plane/blocks/common";
import type { TPopoverMenuPlacement } from "@plane/blocks/common";
import { cn } from "@plane/utils";

// components
import { RichTextEditor } from "@/components/editor/rich-text";
// services
import { AIService } from "@/services/ai.service";
const aiService = new AIService();

type Props = {
  isOpen: boolean;
  handleClose: () => void;
  onResponse: (response: any) => void;
  onError?: (error: any) => void;
  placement?: TPopoverMenuPlacement;
  prompt?: string;
  button: React.ReactNode;
  className?: string;
  workspaceId: string;
  workspaceSlug: string;
  projectId: string;
};

type FormData = {
  prompt: string;
  task: string;
};

export function GptAssistantPopover(props: Props) {
  const {
    isOpen,
    handleClose,
    onResponse,
    onError,
    placement,
    prompt,
    button,
    className = "",
    workspaceId,
    workspaceSlug,
    projectId,
  } = props;
  // states
  const [response, setResponse] = useState("");
  const [invalidResponse, setInvalidResponse] = useState(false);
  const { t } = useTranslation();
  // refs
  const editorRef = useRef<EditorRefApi>(null);
  const responseRef = useRef<EditorRefApi>(null);
  // derived values
  const { side, align } = toSideAndAlign(placement ?? "auto");
  // form
  const {
    handleSubmit,
    control,
    reset,
    setFocus,
    formState: { isSubmitting },
  } = useForm<FormData>({
    defaultValues: {
      prompt: prompt || "",
      task: "",
    },
  });

  const onClose = () => {
    handleClose();
    setResponse("");
    setInvalidResponse(false);
    reset();
  };

  const handleServiceError = (err: any) => {
    const error = err?.data?.error;
    const errorMessage =
      err?.status === 429 ? error || t("app_text.ai_assistant.rate_limit") : error || t("common.error.message");

    setToast({
      type: "error",
      title: t("toast.error"),
      message: errorMessage,
    });

    if (onError) onError(err);
  };

  const callAIService = async (formData: FormData) => {
    try {
      const res = await aiService.createGptTask(workspaceSlug.toString(), {
        prompt: prompt || "",
        task: formData.task,
      });

      setResponse(res.response_html);
      setFocus("task");

      setInvalidResponse(res.response === "");
    } catch (err) {
      handleServiceError(err);
    }
  };

  const handleInvalidTask = () => {
    setToast({
      type: "error",
      title: t("toast.error"),
      message: t("core_ui.gpt_enter_task"),
    });
  };

  const handleAIResponse = async (formData: FormData) => {
    if (!workspaceSlug) return;

    if (formData.task === "") {
      handleInvalidTask();
      return;
    }

    await callAIService(formData);
  };

  useEffect(() => {
    if (isOpen) setFocus("task");
  }, [isOpen, setFocus]);

  useEffect(() => {
    editorRef.current?.setEditorValue(prompt || "");
  }, [editorRef, prompt]);

  useEffect(() => {
    responseRef.current?.setEditorValue(`<p>${response}</p>`);
  }, [response, responseRef]);

  // Read the latest submit handler (it closes over `prompt` and the workspace props) without
  // re-subscribing the Enter listener on every render.
  const onEnterKey = useEffectEvent(() => void handleSubmit(handleAIResponse)());

  useEffect(() => {
    const handleEnterKeyPress = (event: KeyboardEvent) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        onEnterKey();
      }
    };

    // Escape is Base UI's now: it closes the popover, which runs `onClose` through `onOpenChange`.
    if (isOpen) window.addEventListener("keydown", handleEnterKeyPress);

    return () => {
      window.removeEventListener("keydown", handleEnterKeyPress);
    };
  }, [isOpen]);

  const responseActionButton = response !== "" && (
    <Button
      variant="primary"
      size="sm"
      stretch="auto"
      label={t("app_text.ai_assistant.use_response")}
      onClick={() => {
        onResponse(response);
        onClose();
      }}
    />
  );

  const generateResponseButtonText = isSubmitting
    ? t("app_text.ai_assistant.generating_response")
    : response === ""
      ? t("app_text.ai_assistant.generate_response")
      : t("app_text.ai_assistant.generate_again");

  return (
    <div className="relative w-min text-left">
      <Popover
        open={isOpen}
        onOpenChange={(nextOpen) => {
          // The caller's own button owns opening (`openOnClick={false}` below), so the only
          // transitions Base UI drives here are dismissals: Escape and outside press.
          if (!nextOpen) onClose();
        }}
      >
        {/* The trigger only anchors the panel: the `button` node the caller hands us already toggles
            `isOpen`, so a second toggle here would cancel it out. It stays out of the tab order,
            as the `<button tabIndex={-1}>` it replaces did. */}
        <PopoverTrigger
          nativeButton={false}
          openOnClick={false}
          tabIndex={-1}
          render={<span className="flex items-center" />}
        >
          {button}
        </PopoverTrigger>
        {/* The popover owns the portal, positioning, enter/leave and the panel surface, so
            the old popper positioning, enter/leave transition and hand-rolled chrome all go. */}
        <PopoverContent variant="rich" side={side} align={align}>
          <div className={cn("flex min-h-0 w-200 max-w-full flex-1 flex-col space-y-4 overflow-hidden", className)}>
            <PopoverBody tabIndex={0}>
              <div className="vertical-scroll-enable max-h-72 space-y-4 overflow-y-auto">
                {prompt && (
                  <div className="text-13">
                    {t("app_text.ai_assistant.content_label")}
                    <RichTextEditor
                      editable={false}
                      id="ai-assistant-content"
                      initialValue={prompt}
                      containerClassName="-m-3"
                      ref={editorRef}
                      workspaceId={workspaceId}
                      workspaceSlug={workspaceSlug}
                      projectId={projectId}
                    />
                  </div>
                )}
                {response !== "" && (
                  <div className="page-block-section max-h-[8rem] text-13">
                    {t("app_text.ai_assistant.response_label")}
                    <RichTextEditor
                      editable={false}
                      id="ai-assistant-response"
                      initialValue={`<p>${response}</p>`}
                      ref={responseRef}
                      workspaceId={workspaceId}
                      workspaceSlug={workspaceSlug}
                      projectId={projectId}
                    />
                  </div>
                )}
                {invalidResponse && (
                  <div className="text-13 text-danger-primary">{t("app_text.ai_assistant.no_response")}</div>
                )}
              </div>
            </PopoverBody>
            <Controller
              control={control}
              name="task"
              render={({ field: { value, onChange, ref } }) => (
                <InputGroup size="2xl">
                  <Input
                    size="2xl"
                    id="task"
                    name="task"
                    type="text"
                    value={value}
                    onChange={onChange}
                    ref={ref}
                    placeholder={`${
                      prompt && prompt !== ""
                        ? t("app_text.ai_assistant.placeholder_with_content")
                        : t("app_text.ai_assistant.placeholder_empty")
                    }`}
                    // oxlint-disable-next-line jsx-a11y/no-autofocus -- existing behaviour; lint cleanup only
                    autoFocus
                  />
                </InputGroup>
              )}
            />
            <div className="flex justify-between gap-2">
              {responseActionButton ? (
                <>{responseActionButton}</>
              ) : (
                <>
                  <div className="flex items-start justify-center gap-2 text-13 text-accent-primary">
                    <WarningCircleOutline className="h-4 w-4" />
                    <p>{t("app_text.ai_assistant.consent")} </p>
                  </div>
                </>
              )}
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" stretch="auto" label={t("close")} onClick={onClose} />
                <Button
                  variant="primary"
                  size="sm"
                  stretch="auto"
                  label={generateResponseButtonText}
                  onClick={handleSubmit(handleAIResponse)}
                  loading={isSubmitting}
                />
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

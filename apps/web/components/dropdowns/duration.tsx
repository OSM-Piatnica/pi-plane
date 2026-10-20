/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { Timer } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { SelectTriggerChrome } from "@plane/blocks/select";
import type { SelectVariant } from "@plane/blocks/select";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Input, InputGroup } from "@makeplane/propel/components/input";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { CloseOutline } from "@makeplane/propel/icons";
import { cn, normalizeWorkItemDuration } from "@plane/utils";

type Props = {
  /** Trigger chrome, the same `SelectVariant` scale the property selects use. */
  variant: SelectVariant;
  className?: string;
  disabled?: boolean;
  /** Hides the leading icon. */
  hideIcon?: boolean;
  icon?: ReactNode;
  isClearable?: boolean;
  onChange: (val: number | null) => void;
  onClose?: () => void;
  placeholder?: string;
  /** Opt-in hover tooltip on the trigger: heading + the current value. */
  showTooltip?: boolean;
  tabIndex?: number;
  value: number | null | undefined;
};

export const DurationDropdown = observer(function DurationDropdown(props: Props) {
  const {
    variant,
    className,
    disabled = false,
    hideIcon = false,
    icon = <Timer />,
    isClearable = true,
    onChange,
    onClose,
    placeholder = "Duration",
    showTooltip = false,
    tabIndex,
    value,
  } = props;
  // states
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState("");
  // refs
  const inputRef = useRef<HTMLInputElement | null>(null);
  // hooks
  const { t } = useTranslation();

  const hasValue = value !== null && value !== undefined;
  const label = hasValue ? t("duration_days", { count: value }) : placeholder;

  useEffect(() => {
    if (isEditing) inputRef.current?.focus();
  }, [isEditing]);

  const startEditing = () => {
    if (disabled) return;
    setDraft(hasValue ? String(value) : "");
    setIsEditing(true);
  };

  const stopEditing = () => {
    setIsEditing(false);
    onClose?.();
  };

  const commit = () => {
    const trimmed = draft.trim();
    const nextValue = trimmed === "" ? null : normalizeWorkItemDuration(Number(trimmed));
    if (nextValue !== (value ?? null)) onChange(nextValue);
    stopEditing();
  };

  if (isEditing) {
    return (
      <div className={cn("h-full", className)}>
        <InputGroup size="md">
          <Input
            ref={inputRef}
            size="md"
            type="number"
            min={1}
            step={1}
            value={draft}
            placeholder={placeholder}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              // A duration is a whole number of days, so the exponent, sign and decimal keys that
              // a number input would otherwise accept have no meaning here.
              if (["e", "E", "+", "-", "."].includes(e.key)) {
                e.preventDefault();
                return;
              }
              if (e.key === "Enter") commit();
              if (e.key === "Escape") stopEditing();
            }}
          />
        </InputGroup>
      </div>
    );
  }

  const trigger = (
    <SelectTriggerChrome
      variant={variant}
      isActive={false}
      className={cn("clickable", { "cursor-not-allowed text-secondary": disabled })}
      prependIcon={hideIcon ? undefined : (icon as React.ReactElement<{ className?: string }>)}
      label={label}
      isEmpty={!hasValue}
      tabIndex={tabIndex}
      disabled={disabled}
      onClick={startEditing}
    >
      <span className="min-w-0 grow truncate text-left">{label}</span>
    </SelectTriggerChrome>
  );

  return (
    <div className={cn("flex h-full max-w-full items-center gap-1", className)}>
      {showTooltip ? (
        <Tooltip label={`${placeholder}: ${hasValue ? label : "None"}`} layout="stacked">
          <span className="flex h-full max-w-full min-w-0 items-center">{trigger}</span>
        </Tooltip>
      ) : (
        trigger
      )}
      {isClearable && !disabled && hasValue && (
        <IconButton
          variant="ghost"
          size="xs"
          aria-label={t("common.clear")}
          icon={<Icon icon={CloseOutline} />}
          onClick={() => onChange(null)}
        />
      )}
    </div>
  );
});

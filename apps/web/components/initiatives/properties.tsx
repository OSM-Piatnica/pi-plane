/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import {
  FlagOutline,
  InitiativeCancelled,
  InitiativeCompleted,
  InitiativeDraft,
  InitiativeInProgress,
  InitiativePlanned,
} from "@makeplane/propel/icons";
import { LinearProgress } from "@makeplane/propel/components/linear-progress";
import { Select } from "@plane/blocks/select";
import type { SelectVariant } from "@plane/blocks/select";
import { INITIATIVE_HEALTHS, INITIATIVE_STATUSES } from "@plane/constants";
import type { TInitiativeHealthOption, TInitiativeStatusOption } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TInitiativeHealth, TInitiativeKind, TInitiativeProgress, TInitiativeStatus } from "@plane/types";
import { cn } from "@plane/utils";
import { getInitiativeProgressPercentage } from "@/helpers/initiatives";

const STATUS_ICONS = {
  planned: InitiativePlanned,
  active: InitiativeInProgress,
  paused: InitiativeDraft,
  completed: InitiativeCompleted,
  cancelled: InitiativeCancelled,
} as const;

/** A goal shows a flag; an initiative shows its status */
export function InitiativeIcon(props: { kind: TInitiativeKind; status: TInitiativeStatus; className?: string }) {
  const { kind, status, className } = props;
  if (kind === "goal") {
    const color = INITIATIVE_STATUSES.find((option) => option.key === status)?.color;
    return <FlagOutline className={cn("size-4 shrink-0", className)} style={{ color }} />;
  }
  // the status icons carry their own colours
  const StatusIcon = STATUS_ICONS[status] ?? InitiativePlanned;
  return <StatusIcon className={cn("size-4 shrink-0", className)} />;
}

function ColorDot({ color }: { color: string }) {
  return <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: color }} aria-hidden="true" />;
}

export function InitiativeStatusSelect(props: {
  value: TInitiativeStatus;
  onChange: (value: TInitiativeStatus) => void;
  disabled?: boolean;
  variant?: SelectVariant;
}) {
  const { value, onChange, disabled = false, variant = "pill-md" } = props;
  const { t } = useTranslation();
  const selected = INITIATIVE_STATUSES.find((option) => option.key === value) ?? null;
  return (
    <Select<TInitiativeStatusOption>
      getValues={() => [...INITIATIVE_STATUSES]}
      value={selected}
      onChange={(key) => key && onChange(key as TInitiativeStatus)}
      getOptionValue={(option) => option.key}
      getOptionLabel={(option) => t(option.i18n_label)}
      getOptionIcon={(option) => <ColorDot color={option.color} />}
      disabled={disabled}
      showSearch={false}
      pinSelected={false}
    >
      <Select.Trigger<TInitiativeStatusOption>
        variant={variant}
        disabled={disabled}
        prependIcon={(options) => (options[0] ? <ColorDot color={options[0].color} /> : undefined)}
        label={(options) => (options[0] ? t(options[0].i18n_label) : "")}
      >
        {(options) => <span className="truncate">{options[0] ? t(options[0].i18n_label) : ""}</span>}
      </Select.Trigger>
    </Select>
  );
}

export function InitiativeHealthBadge(props: { health: TInitiativeHealth | null; className?: string }) {
  const { health, className } = props;
  const { t } = useTranslation();
  const option = INITIATIVE_HEALTHS.find((item) => item.key === health);
  if (!option) return <span className={cn("text-11 text-placeholder", className)}>{t("initiatives.health.none")}</span>;
  return (
    <span
      className={cn("inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-11 font-medium", className)}
      style={{ color: option.color, backgroundColor: `${option.color}20` }}
    >
      <ColorDot color={option.color} />
      {t(option.i18n_label)}
    </span>
  );
}

export function InitiativeHealthSelect(props: {
  value: TInitiativeHealth | null;
  onChange: (value: TInitiativeHealth) => void;
  disabled?: boolean;
}) {
  const { value, onChange, disabled = false } = props;
  const { t } = useTranslation();
  const selected = INITIATIVE_HEALTHS.find((option) => option.key === value) ?? null;
  return (
    <Select<TInitiativeHealthOption>
      getValues={() => [...INITIATIVE_HEALTHS]}
      value={selected}
      onChange={(key) => key && onChange(key as TInitiativeHealth)}
      getOptionValue={(option) => option.key}
      getOptionLabel={(option) => t(option.i18n_label)}
      getOptionIcon={(option) => <ColorDot color={option.color} />}
      disabled={disabled}
      showSearch={false}
      pinSelected={false}
      placeholder={t("initiatives.health.pick")}
    >
      <Select.Trigger<TInitiativeHealthOption>
        variant="pill-md"
        disabled={disabled}
        prependIcon={(options) => (options[0] ? <ColorDot color={options[0].color} /> : undefined)}
        label={(options) => (options[0] ? t(options[0].i18n_label) : t("initiatives.health.pick"))}
      >
        {(options) => (
          <span className="truncate">{options[0] ? t(options[0].i18n_label) : t("initiatives.health.pick")}</span>
        )}
      </Select.Trigger>
    </Select>
  );
}

/** A progress bar with the share of done work items and the count, and a note when some are hidden */
export function InitiativeProgress(props: {
  label: string;
  progress: TInitiativeProgress | undefined;
  isPartial: boolean;
  partialNote?: string;
  emptyNote?: string;
}) {
  const { label, progress, isPartial, partialNote, emptyNote } = props;
  const { t } = useTranslation();
  const percentage = getInitiativeProgressPercentage(progress);
  const total = progress?.total_issues ?? 0;
  const done = (progress?.completed ?? 0) + (progress?.cancelled ?? 0);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2 text-13">
        <span className="font-medium text-primary">{label}</span>
        <span className="text-tertiary">{t("initiatives.progress.done_of_total", { done, total })}</span>
      </div>
      <LinearProgress
        value={percentage}
        size="md"
        variant={percentage === 100 ? "success" : "brand"}
        aria-label={label}
      />
      {total === 0 && emptyNote && <span className="text-12 text-tertiary">{emptyNote}</span>}
      {isPartial && partialNote && <span className="text-12 text-tertiary">{partialNote}</span>}
    </div>
  );
}

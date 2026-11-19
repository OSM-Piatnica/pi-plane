/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId } from "react";
import { Switch } from "@makeplane/propel/components/switch";
import { useTranslation } from "@plane/i18n";
import type { TAvailableWorkspaceFeature, TWorkspaceFeatureFlags, TWorkspaceFeatureKey } from "@plane/types";

type Props = {
  /** The features that have a switch: only available ones */
  features: readonly TAvailableWorkspaceFeature[];
  flags: TWorkspaceFeatureFlags;
  onToggle: (key: TWorkspaceFeatureKey, isEnabled: boolean) => void;
};

/** The switches of the workspace Features settings page: a name, one line of description, a switch */
export function WorkspaceFeaturesList({ features, flags, onToggle }: Props) {
  const { t } = useTranslation();
  const idPrefix = useId();

  return (
    <ul className="mt-4 divide-y divide-subtle rounded-md border border-subtle">
      {features.map((feature) => {
        const titleId = `${idPrefix}-${feature.key}-title`;
        const descriptionId = `${idPrefix}-${feature.key}-description`;
        return (
          <li key={feature.key} className="flex items-center justify-between gap-4 px-4 py-3">
            <div className="flex min-w-0 flex-col gap-0.5">
              <span id={titleId} className="text-body-sm-medium text-primary">
                {t(feature.i18n_title)}
              </span>
              <span id={descriptionId} className="text-body-xs-regular text-tertiary">
                {t(feature.i18n_description)}
              </span>
            </div>
            <Switch
              size="sm"
              checked={flags[feature.key]}
              onCheckedChange={(checked) => onToggle(feature.key, checked)}
              aria-labelledby={titleId}
              aria-describedby={descriptionId}
            />
          </li>
        );
      })}
    </ul>
  );
}

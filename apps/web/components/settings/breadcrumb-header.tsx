/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { LucideIcon } from "lucide-react";
// plane imports
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import type { ISvgIcons } from "@plane/blocks/icons";
import { useTranslation } from "@plane/i18n";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { SettingsPageHeader } from "@/components/settings/page-header";

type Props = {
  /** Entry from `WORKSPACE_SETTINGS` or `PROJECT_SETTINGS`. */
  item: { i18n_label: string };
  /** Matching entry from `WORKSPACE_SETTINGS_ICONS` or `PROJECT_SETTINGS_ICONS`. */
  Icon: LucideIcon | React.FC<ISvgIcons>;
};

/** Header of a settings page: a single breadcrumb with the page's icon and translated name. */
export function SettingsBreadcrumbHeader({ item, Icon }: Props) {
  const { t } = useTranslation();

  return (
    <SettingsPageHeader
      leftItem={
        <div className="flex items-center gap-2">
          <Breadcrumbs>
            <Breadcrumbs.Item
              component={<BreadcrumbLink label={t(item.i18n_label)} icon={<Icon className="size-4 text-tertiary" />} />}
            />
          </Breadcrumbs>
        </div>
      }
    />
  );
}

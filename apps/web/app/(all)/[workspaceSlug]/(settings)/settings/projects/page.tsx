/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useTranslation } from "@plane/i18n";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { Button as ButtonElement } from "@makeplane/propel/elements/button";
// assets
import ProjectDarkEmptyState from "@/app/assets/empty-state/project-settings/no-projects-dark.png?url";
import ProjectLightEmptyState from "@/app/assets/empty-state/project-settings/no-projects-light.png?url";
// hooks
import { useCommandPalette } from "@/hooks/store/use-command-palette";

function ProjectSettingsPage() {
  // store hooks
  const { resolvedTheme } = useTheme();
  const { toggleCreateProjectModal } = useCommandPalette();
  const { t } = useTranslation();
  // derived values
  const resolvedPath = resolvedTheme === "dark" ? ProjectDarkEmptyState : ProjectLightEmptyState;
  return (
    <div className="mx-auto flex h-full max-w-[480px] flex-col items-center justify-center gap-4">
      <img src={resolvedPath} alt={t("app_text.project_settings_empty.title")} />
      <div className="text-16 font-semibold text-tertiary">{t("app_text.project_settings_empty.title")}</div>
      <div className="text-center text-13 text-tertiary">{t("app_text.project_settings_empty.description")}</div>
      <div className="flex gap-2">
        <ButtonElement
          variant="secondary"
          size="sm"
          stretch="auto"
          render={<Link href="https://plane.so/" target="_blank" />}
        >
          {t("app_text.project_settings_empty.learn_more")}
        </ButtonElement>
        <Button
          variant="primary"
          size="sm"
          stretch="auto"
          label={t("workspace_projects.empty_state.general.primary_button.text")}
          onClick={() => toggleCreateProjectModal(true)}
        />
      </div>
    </div>
  );
}

export default observer(ProjectSettingsPage);

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";

export function AuthFooter() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center">
      <span className="text-13 whitespace-nowrap text-tertiary">{t("app_text.auth_screens.join_teams")}</span>
    </div>
  );
}

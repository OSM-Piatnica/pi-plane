/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
// images
import Image404 from "@/app/assets/404.svg?url";

export function PageNotFound() {
  const { t } = useTranslation();

  return (
    <div className={`h-screen w-full overflow-hidden bg-surface-1`}>
      <div className="grid h-full place-items-center p-4">
        <div className="space-y-8 text-center">
          <div className="relative mx-auto h-60 w-60 lg:h-80 lg:w-80">
            <img src={Image404} alt={t("app_text.not_found.image_alt")} className="h-full w-full object-contain" />
          </div>
          <div className="space-y-2">
            <h3 className="text-16 font-semibold">{t("app_text.not_found.title")}</h3>
            <p className="text-13 text-secondary">{t("app_text.not_found.description")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

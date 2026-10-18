/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
// assets
import SomethingWentWrongImage from "@/app/assets/something-went-wrong.svg?url";

export function SomethingWentWrongError() {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-screen w-full place-items-center bg-surface-1 p-6">
      <div className="text-center">
        <div className="mx-auto grid h-52 w-52 place-items-center rounded-full">
          <div className="grid h-32 w-32 place-items-center">
            <img
              src={SomethingWentWrongImage}
              alt={t("app_text.not_found.title")}
              className="h-full w-full object-contain"
            />
          </div>
        </div>
        <h1 className="mt-12 text-24 font-semibold">{t("app_text.not_found.title")}</h1>
        <p className="mt-4 text-tertiary">{t("space_text.issues.public_board_not_found")}</p>
      </div>
    </div>
  );
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { useTranslation } from "@plane/i18n";
// ui
import { Button } from "@makeplane/propel/components/button";
// images
import Image404 from "@/app/assets/404.svg?url";
// types
import type { Route } from "./+types/not-found";

export const meta: Route.MetaFunction = () => [
  { title: "404 - Page Not Found" },
  { name: "robots", content: "noindex, nofollow" },
];

function PageNotFound() {
  const { t } = useTranslation();
  return (
    <div className={`h-screen w-full overflow-hidden bg-surface-1`}>
      <div className="grid h-full place-items-center p-4">
        <div className="space-y-8 text-center">
          <div className="relative mx-auto h-60 w-60 lg:h-80 lg:w-80">
            <img src={Image404} className="h-full w-full object-contain" alt={t("app_text.not_found.image_alt")} />
          </div>
          <div className="space-y-2">
            <h3 className="text-16 font-semibold">{t("app_text.not_found.title")}</h3>
            <p className="text-13 text-secondary">{t("app_text.not_found.description")}</p>
          </div>
          <div className="flex justify-center">
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              label={t("app_text.not_found.go_to_home")}
              nativeButton={false}
              render={<Link href="/" />}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default PageNotFound;

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { EmptyStateDetailed } from "@plane/blocks/empty-state";
import { PI_PLANE_RELEASES_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";

type TProductUpdatesFallbackProps = {
  description: string;
  variant: "cloud" | "self-managed";
};

export function ProductUpdatesFallback(props: TProductUpdatesFallbackProps) {
  const { description } = props;
  const { t } = useTranslation();
  // Pi-Plane's releases are on GitHub; the changelog of plane.so describes the upstream product
  const changelogUrl = PI_PLANE_RELEASES_URL;

  return (
    <div className="py-8">
      <EmptyStateDetailed
        assetKey="changelog"
        description={description}
        align="center"
        actions={[
          {
            label: t("app_text.product_updates.go_to_changelog"),
            variant: "primary",
            onClick: () => window.open(changelogUrl, "_blank"),
          },
        ]}
      />
    </div>
  );
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { EmptyStateDetailed } from "@plane/blocks/empty-state";
import { useTranslation } from "@plane/i18n";

type TProductUpdatesFallbackProps = {
  description: string;
  variant: "cloud" | "self-managed";
};

export function ProductUpdatesFallback(props: TProductUpdatesFallbackProps) {
  const { description, variant } = props;
  const { t } = useTranslation();
  // derived values
  const changelogUrl =
    variant === "cloud"
      ? "https://plane.so/changelog?category=cloud"
      : "https://plane.so/changelog?category=self-hosted";

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

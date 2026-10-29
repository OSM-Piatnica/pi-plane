/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import type { TSticky } from "@plane/types";
import { STICKY_COLORS_LIST } from "./sticky-colors";

type TProps = {
  handleUpdate: (data: Partial<TSticky>) => Promise<void>;
};

export function ColorPalette(props: TProps) {
  const { handleUpdate } = props;
  const { t } = useTranslation();
  return (
    <div className="shadow absolute bottom-5 left-0 z-10 mb-2 w-56 rounded-md bg-surface-1 p-2">
      <div className="mb-2 text-13 font-semibold text-placeholder">{t("page_ui.editor.background_colors")}</div>
      <div className="flex flex-wrap gap-2">
        {STICKY_COLORS_LIST.map((color) => (
          <button
            key={color.key}
            type="button"
            aria-label={t(color.label)}
            onClick={() => {
              handleUpdate({
                background_color: color.key,
              });
            }}
            className="h-6 w-6 rounded-md transition-all hover:ring-2 hover:ring-accent-strong focus:ring-2 focus:ring-accent-strong focus:outline-none"
            style={{
              backgroundColor: color.backgroundColor,
            }}
          />
        ))}
      </div>
    </div>
  );
}

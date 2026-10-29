/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import type { TThemeOverrides } from "@plane/utils";
import { applyThemeOverrides, isColorDark, THEME_OVERRIDE_GROUPS, toOverrideHex, validateHexColor } from "@plane/utils";
// local imports
import { InputColorPicker } from "./input-color-picker";

type Props = {
  value: TThemeOverrides | undefined;
  onChange: (value: TThemeOverrides) => void;
};

const withHash = (value: string) => (value && value[0] !== "#" ? `#${value}` : value);

export const CustomThemeAdvancedSettings = observer(function CustomThemeAdvancedSettings(props: Props) {
  const { value, onChange } = props;
  // translation
  const { t } = useTranslation();
  // state
  const [isOpen, setIsOpen] = useState(() => Object.keys(value ?? {}).length > 0);
  // derived values
  const overrides = value ?? {};
  const overrideCount = Object.keys(overrides).length;

  const update = (next: TThemeOverrides) => {
    onChange(next);
    // preview what is valid so far; it is saved with "Set theme"
    const valid: TThemeOverrides = {};
    Object.entries(next).forEach(([token, color]) => {
      if (validateHexColor(color)) valid[token] = toOverrideHex(color);
    });
    applyThemeOverrides(valid);
  };

  const handleTokenChange = (token: string, color: string) => {
    if (!color) {
      const { [token]: _removed, ...rest } = overrides;
      update(rest);
      return;
    }
    update({ ...overrides, [token]: withHash(color) });
  };

  return (
    <div className="flex flex-col gap-3 border-t border-subtle pt-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-body-sm-medium">{t("core_ui.theme.advanced.title")}</h3>
          <p className="text-caption-md-regular text-tertiary">{t("core_ui.theme.advanced.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          {overrideCount > 0 && (
            <Button
              variant="secondary"
              size="md"
              stretch="auto"
              type="button"
              label={t("core_ui.theme.advanced.reset_all")}
              onClick={() => update({})}
            />
          )}
          <Button
            variant="secondary"
            size="md"
            stretch="auto"
            type="button"
            aria-expanded={isOpen}
            label={
              isOpen ? t("core_ui.theme.advanced.hide") : t("core_ui.theme.advanced.show", { count: overrideCount })
            }
            onClick={() => setIsOpen((open) => !open)}
          />
        </div>
      </div>
      {isOpen && (
        <div className="flex flex-col gap-5">
          {THEME_OVERRIDE_GROUPS.map((group) => (
            <section key={group.key} className="flex flex-col gap-3">
              <h4 className="text-body-xs-medium text-secondary">{t(`core_ui.theme.advanced.groups.${group.key}`)}</h4>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {group.tokens.map(({ token, labelKey }) => {
                  const color = overrides[token];
                  const isValid = !color || validateHexColor(color);
                  return (
                    <div key={token} className="flex flex-col gap-1">
                      <label htmlFor={`theme-override-${token}`} className="text-caption-md-regular text-tertiary">
                        {t(`core_ui.theme.advanced.tokens.${labelKey}`)}
                      </label>
                      <InputColorPicker
                        name={`theme-override-${token}`}
                        value={color ?? ""}
                        onChange={(next) => handleTokenChange(token, next)}
                        placeholder={t("core_ui.theme.advanced.auto")}
                        className="w-full"
                        style={
                          color && isValid
                            ? {
                                backgroundColor: withHash(color),
                                color: isColorDark(withHash(color)) ? "#ffffff" : "#000000",
                              }
                            : undefined
                        }
                        hasError={!isValid}
                      />
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
});

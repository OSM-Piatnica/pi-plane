/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import type { I_THEME_OPTION } from "@plane/constants";
import { THEME_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Select } from "@plane/blocks/select";

/** A theme in the list: the built-in ones are named by a translation key, the instance's own by `label`. */
export type TThemeSwitchOption = I_THEME_OPTION & { label?: string };

type Props = {
  value: TThemeSwitchOption | null;
  onChange: (value: TThemeSwitchOption) => void;
  /** themes the instance added, listed after the built-in ones */
  extraOptions?: TThemeSwitchOption[];
};

function ThemeOptionIcon({ option }: { option: TThemeSwitchOption }) {
  return (
    <div
      className="relative flex h-4 w-4 rotate-45 transform items-center justify-center rounded-full border"
      style={{
        borderColor: option.icon.border,
      }}
    >
      <div
        className="h-full w-1/2 rounded-l-full"
        style={{
          background: option.icon.color1,
        }}
      />
      <div
        className="h-full w-1/2 rounded-r-full border-l"
        style={{
          borderLeftColor: option.icon.border,
          background: option.icon.color2,
        }}
      />
    </div>
  );
}

export function ThemeSwitch(props: Props) {
  const { value, onChange, extraOptions = [] } = props;
  // translation
  const { t } = useTranslation();
  // derived values
  const options: TThemeSwitchOption[] = [...THEME_OPTIONS, ...extraOptions];
  const getLabel = (option: TThemeSwitchOption) => option.label ?? t(option.key);

  return (
    <Select<TThemeSwitchOption>
      getValues={() => options}
      value={value}
      onChange={(themeValue) => {
        const themeOption = options.find((option) => option.value === themeValue);
        if (themeOption) onChange(themeOption);
      }}
      getOptionValue={(option) => option.value}
      getOptionLabel={getLabel}
      getOptionIcon={(option) => <ThemeOptionIcon option={option} />}
      contentSizing="anchor"
      showSearch={false}
      pinSelected={false}
      placeholder={t("select_your_theme")}
    >
      <Select.Trigger variant="select-md" className="w-42 max-w-full border-subtle-1">
        <div className="min-w-0 grow">
          {value ? (
            <div className="flex w-full items-center gap-2">
              <ThemeOptionIcon option={value} />
              {getLabel(value)}
            </div>
          ) : (
            t("select_your_theme")
          )}
        </div>
      </Select.Trigger>
    </Select>
  );
}

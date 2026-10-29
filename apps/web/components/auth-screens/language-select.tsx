/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
// plane imports
import { Select } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import type { TLanguage } from "@plane/i18n";

type TLanguageOption = { value: string; label: string };

export const AuthLanguageSelect = observer(function AuthLanguageSelect() {
  const { currentLocale, changeLanguage, languages } = useTranslation();

  const options: TLanguageOption[] = languages.map((language) => ({ value: language.value, label: language.label }));
  const currentLanguage = options.find((language) => language.value === currentLocale) ?? {
    value: currentLocale,
    label: currentLocale,
  };

  return (
    <Select<TLanguageOption>
      getValues={() => options}
      value={currentLanguage}
      onChange={(value) => changeLanguage(value as TLanguage)}
      getOptionValue={(option) => option.value}
      getOptionLabel={(option) => option.label}
      showSearch={false}
      pinSelected={false}
    >
      <Select.Trigger variant="select-ghost-md">
        <Select.Value />
      </Select.Trigger>
    </Select>
  );
});

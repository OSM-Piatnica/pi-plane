/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
// helpers
import { EAuthModes } from "@/types/auth";

type TAuthHeader = {
  authMode: EAuthModes;
};

type TAuthHeaderContent = {
  header: string;
  subHeader: string;
};

type TAuthHeaderDetails = {
  [mode in EAuthModes]: TAuthHeaderContent;
};

type TTranslate = (key: string) => string;

const getTitles = (t: TTranslate): TAuthHeaderDetails => ({
  [EAuthModes.SIGN_IN]: {
    header: t("space_text.auth_header.sign_in_header"),
    subHeader: t("space_text.auth_header.sign_in_sub_header"),
  },
  [EAuthModes.SIGN_UP]: {
    header: t("space_text.auth_header.sign_up_header"),
    subHeader: t("space_text.auth_header.sign_up_sub_header"),
  },
});

export function AuthHeader(props: TAuthHeader) {
  const { authMode } = props;
  const { t } = useTranslation();

  const getHeaderSubHeader = (mode: EAuthModes | null): TAuthHeaderContent => {
    if (mode) {
      return getTitles(t)[mode];
    }

    return {
      header: t("space_text.auth_header.default_header"),
      subHeader: t("space_text.auth_header.default_sub_header"),
    };
  };

  const { header, subHeader } = getHeaderSubHeader(authMode);

  return (
    <>
      <div className="flex flex-col gap-1">
        <span className="text-20 leading-7 font-semibold text-primary">{header}</span>
        <span className="text-20 leading-7 font-semibold text-placeholder">{subHeader}</span>
      </div>
    </>
  );
}

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
// helpers
import { renderTaggedText } from "@/helpers/tagged-text";

type Props = {
  isSignUp?: boolean;
};

export function TermsAndConditions(props: Props) {
  const { isSignUp = false } = props;
  const { t } = useTranslation();
  return (
    <span className="flex items-center justify-center py-6">
      <p className="text-center text-13 whitespace-pre-line text-secondary">
        {renderTaggedText(isSignUp ? t("space_text.terms.agree_sign_up") : t("space_text.terms.agree_sign_in"), {
          terms: (label) => (
            <a href="https://plane.so/legals/terms-and-conditions" target="_blank" rel="noopener noreferrer">
              <span className="text-13 font-medium underline hover:cursor-pointer">{label}</span>
            </a>
          ),
          privacy: (label) => (
            <a href="https://plane.so/legals/privacy-policy" target="_blank" rel="noopener noreferrer">
              <span className="text-13 font-medium underline hover:cursor-pointer">{label}</span>
            </a>
          ),
        })}
      </p>
    </span>
  );
}

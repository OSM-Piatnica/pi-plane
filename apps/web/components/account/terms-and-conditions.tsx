/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import Link from "next/link";
import { EAuthModes } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
// helpers
import { renderTaggedText } from "@/helpers/tagged-text";

interface TermsAndConditionsProps {
  authType?: EAuthModes;
}

// Constants for better maintainability
// Placeholder URLs: replace with Pi-Plane's own terms of use and privacy policy pages.
const LEGAL_LINKS = {
  termsOfService: "https://example.com/terms-of-use",
  privacyPolicy: "https://example.com/privacy-policy",
} as const;

const MESSAGES = {
  [EAuthModes.SIGN_UP]: "app_text.terms.agree_sign_up",
  [EAuthModes.SIGN_IN]: "app_text.terms.agree_sign_in",
} as const;

// Reusable link component to reduce duplication
function LegalLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-secondary" target="_blank" rel="noopener noreferrer">
      <span className="text-13 font-medium underline hover:cursor-pointer">{children}</span>
    </Link>
  );
}

export function TermsAndConditions({ authType = EAuthModes.SIGN_IN }: TermsAndConditionsProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center">
      <p className="text-center text-13 whitespace-pre-line text-tertiary">
        {renderTaggedText(t(MESSAGES[authType]), {
          terms: (text) => <LegalLink href={LEGAL_LINKS.termsOfService}>{text}</LegalLink>,
          privacy: (text) => <LegalLink href={LEGAL_LINKS.privacyPolicy}>{text}</LegalLink>,
        })}
      </p>
    </div>
  );
}

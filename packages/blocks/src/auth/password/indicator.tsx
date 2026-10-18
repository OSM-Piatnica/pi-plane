/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import React from "react";
import { E_PASSWORD_STRENGTH } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { cn, getPasswordStrength, getPasswordCriteria } from "@plane/utils";
import { getStrengthInfo, getFragmentColor } from "./helper";
import { TickCircleOutline } from "@makeplane/propel/icons";

// Spelled out (not built from the criterion key) so the keys stay greppable. The utils label is the
// English fallback for a criterion this map does not know yet.
const CRITERIA_LABEL_KEYS: Record<string, string> = {
  length: "auth.common.password.criteria.length",
  uppercase: "auth.common.password.criteria.uppercase",
  lowercase: "auth.common.password.criteria.lowercase",
  number: "auth.common.password.criteria.number",
  special: "auth.common.password.criteria.special",
};

export interface PasswordStrengthIndicatorProps {
  password: string;
  showCriteria?: boolean;
  isFocused?: boolean;
}

export function PasswordStrengthIndicator({
  password,
  showCriteria = true,
  isFocused = false,
}: PasswordStrengthIndicatorProps) {
  // translation
  const { t } = useTranslation();
  const strength = getPasswordStrength(password);
  const criteria = getPasswordCriteria(password);
  const strengthInfo = getStrengthInfo(strength);

  const isPasswordMeterVisible = isFocused || strength !== E_PASSWORD_STRENGTH.STRENGTH_VALID;

  if ((!password && !showCriteria) || !isPasswordMeterVisible) {
    return null;
  }

  return (
    <div className={cn("space-y-3")}>
      {/* Strength Indicator */}
      <div className="space-y-2">
        <div className="flex w-full gap-1 transition-all duration-300 ease-linear">
          {[0, 1, 2].map((fragmentIndex) => (
            <div
              key={fragmentIndex}
              className={cn(
                "h-1 flex-1 rounded-xs transition-all duration-300 ease-in-out",
                getFragmentColor(fragmentIndex, strengthInfo.activeFragments)
              )}
            />
          ))}
        </div>

        {/* Strength Message */}
        {password && (
          <p className={cn("!text-body-xs-medium font-medium", strengthInfo.textColor)}>{t(strengthInfo.messageKey)}</p>
        )}
      </div>

      {/* Criteria list */}
      {showCriteria && (
        <div className="flex flex-wrap gap-2">
          {criteria.map((criterion) => (
            <div key={criterion.key} className="flex items-center gap-1.5">
              <div className="flex items-center justify-center p-0.5">
                <TickCircleOutline
                  className={cn("h-3 w-3 flex-shrink-0", {
                    "text-success-primary": criterion.isValid,
                    "text-primary": !criterion.isValid,
                  })}
                />
              </div>
              <span
                className={cn("!text-caption-sm-regular", {
                  "text-success-primary": criterion.isValid,
                  "text-primary": !criterion.isValid,
                })}
              >
                {t(CRITERIA_LABEL_KEYS[criterion.key] ?? criterion.label)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

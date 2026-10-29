/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import * as React from "react";
import { PI_PLANE_MARK_DATA_URI } from "./pi-plane-mark";

export type PlaneLockupProps = React.ComponentPropsWithoutRef<"svg">;

export function PlaneLockup({ width = "180", height = "53", className, color = "currentColor" }: PlaneLockupProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 180 53"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Pi-Plane"
    >
      <image href={PI_PLANE_MARK_DATA_URI} x="0" y="0" width="49.69" height="53" />
      <text x="60" y="38" fill={color} fontFamily="Inter, system-ui, sans-serif" fontSize="32" fontWeight="700">
        Pi-Plane
      </text>
    </svg>
  );
}

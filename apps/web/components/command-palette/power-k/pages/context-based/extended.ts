/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPowerKCommandConfig } from "@/components/power-k/core/types";
import type { TContextEntityMap } from "@/components/power-k/ui/pages/context-based";
// local imports
import type { TPowerKContextTypeExtended } from "../../types";

export const CONTEXT_ENTITY_MAP_EXTENDED: Record<TPowerKContextTypeExtended, TContextEntityMap> = {};

export const usePowerKContextBasedExtendedActions = (): TPowerKCommandConfig[] => [];

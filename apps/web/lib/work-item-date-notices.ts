/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPairedDateNotice } from "@plane/utils";

/**
 * When the server fills a work item's other planning date for the first finish/due entry (or
 * explains why it did not), the store reports it here and the toaster tells the user, with Undo.
 * A tiny bus keeps the MobX store free of React and translations.
 */
export type TWorkItemDateNoticeEvent = {
  issueId: string;
  notices: TPairedDateNotice[];
  /** Reverts only the defaulted field, leaving the user's own edit in place. */
  undo?: () => Promise<void>;
};

export type TWorkItemDateNoticeListener = (event: TWorkItemDateNoticeEvent) => void;

const listeners = new Set<TWorkItemDateNoticeListener>();

/** Subscribes to the notices; returns the unsubscribe. */
export const onWorkItemDateNotice = (listener: TWorkItemDateNoticeListener) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

export const emitWorkItemDateNotice = (event: TWorkItemDateNoticeEvent) => {
  listeners.forEach((listener) => listener(event));
};

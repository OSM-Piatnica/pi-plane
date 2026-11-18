/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useCallback, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { useLocalStorage } from "@plane/hooks";
import { cn } from "@plane/utils";
import { sanitizePinnedKeys, togglePinnedKey } from "./pinned-properties";

const COLLAPSED_STORAGE_KEY = "work_item_properties_collapsed";
const PINNED_STORAGE_KEY = "work_item_pinned_properties";

type TPropertyListContext = {
  isCollapsed: boolean;
  pinnedKeys: string[];
  togglePin: (propertyKey: string) => void;
};

const PropertyListContext = createContext<TPropertyListContext | null>(null);

/** The collapse and pin state of the enclosing property list, or null outside of one. */
export const usePropertyListContext = () => useContext(PropertyListContext);

type TCollapsiblePropertyListProps = {
  /** The heading text. */
  title: string;
  /** Accessible label of the heading button while the list is collapsed. */
  expandLabel: string;
  /** Accessible label of the heading button while the list is expanded. */
  collapseLabel: string;
  /** Classes of the heading button, e.g. its margin. */
  buttonClassName?: string;
  /** Classes of the heading text. */
  headingClassName?: string;
  listClassName?: string;
  children: ReactNode;
};

/**
 * A work item property list with a collapsible heading. While collapsed, only the properties the user pinned stay
 * visible. Both the collapsed state and the pins are a per-browser preference kept in local storage, shared by every
 * place that renders the list (the work item page and the peek view).
 */
export function CollapsiblePropertyList(props: TCollapsiblePropertyListProps) {
  const { title, expandLabel, collapseLabel, buttonClassName, headingClassName, listClassName, children } = props;
  const { storedValue: collapsedValue, setValue: setCollapsed } = useLocalStorage<boolean>(
    COLLAPSED_STORAGE_KEY,
    false
  );
  const { storedValue: pinnedValue, setValue: setPinned } = useLocalStorage<string[]>(PINNED_STORAGE_KEY, []);
  const isCollapsed = Boolean(collapsedValue);
  const pinnedKeys = useMemo(() => sanitizePinnedKeys(pinnedValue), [pinnedValue]);

  const togglePin = useCallback(
    (propertyKey: string) => {
      setPinned(togglePinnedKey(pinnedKeys, propertyKey));
    },
    [pinnedKeys, setPinned]
  );
  const contextValue = useMemo(() => ({ isCollapsed, pinnedKeys, togglePin }), [isCollapsed, pinnedKeys, togglePin]);

  return (
    <PropertyListContext.Provider value={contextValue}>
      <button
        type="button"
        onClick={() => setCollapsed(!isCollapsed)}
        aria-expanded={!isCollapsed}
        aria-label={isCollapsed ? expandLabel : collapseLabel}
        className={cn("flex items-center gap-1 rounded-sm text-primary hover:text-secondary", buttonClassName)}
      >
        <span className={headingClassName}>{title}</span>
        <ChevronDown
          className={cn("size-3.5 shrink-0 transition-transform", {
            "-rotate-90": isCollapsed,
          })}
        />
      </button>
      <div className={listClassName}>{children}</div>
    </PropertyListContext.Provider>
  );
}

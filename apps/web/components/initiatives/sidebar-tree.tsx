/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { ChevronDownOutline, ChevronRightOutline, ListLayoutOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import type { TInitiative } from "@plane/types";
import { cn } from "@plane/utils";
import { SidebarNavItem } from "@/components/sidebar/sidebar-navigation";
import { useAppTheme } from "@/hooks/store/use-app-theme";
import { useInitiative } from "@/hooks/store/use-initiative";
import { InitiativeIcon } from "./properties";

function TreeLink(props: { initiative: TInitiative; href: string; isActive: boolean; nested?: boolean }) {
  const { initiative, href, isActive, nested = false } = props;
  const { toggleSidebar } = useAppTheme();
  return (
    <Link
      href={href}
      onClick={() => {
        if (window.innerWidth < 768) toggleSidebar();
      }}
      className="min-w-0 flex-1"
    >
      <SidebarNavItem isActive={isActive} className={cn(nested && "pl-7")}>
        <div className="flex min-w-0 items-center gap-1.5 py-[1px]">
          <InitiativeIcon kind={initiative.kind} status={initiative.status} />
          <span className="truncate text-13">{initiative.name}</span>
        </div>
      </SidebarNavItem>
    </Link>
  );
}

/** Goals with their initiatives, then the initiatives without a goal. A goal can be folded. */
export const InitiativesSidebarTree = observer(function InitiativesSidebarTree() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const pathname = usePathname();
  const { tree, isListLoaded } = useInitiative();
  const [folded, setFolded] = useState<Record<string, boolean>>({});

  const base = `/${workspaceSlug?.toString() ?? ""}/initiatives`;
  const hrefOf = (initiative: TInitiative) => `${base}/${initiative.id}`;
  const isActive = (initiative: TInitiative) => pathname.replace(/\/$/, "") === hrefOf(initiative);
  const isListActive = pathname.replace(/\/$/, "") === base;

  return (
    <div className="flex flex-col gap-0.5">
      <Link href={`${base}/`}>
        <SidebarNavItem isActive={isListActive}>
          <div className="flex items-center gap-1.5 py-[1px]">
            <ListLayoutOutline className="size-4 shrink-0" />
            <span className="text-13 font-medium">{t("initiatives.all")}</span>
          </div>
        </SidebarNavItem>
      </Link>
      {isListLoaded && tree.length === 0 && (
        <p className="px-2 pt-2 text-12 text-tertiary">{t("initiatives.empty.sidebar")}</p>
      )}
      {tree.map((node) => {
        if (!node.goal)
          return (
            <div key="no-goal" className="flex flex-col gap-0.5 pt-2">
              <span className="px-2 text-11 font-medium text-tertiary uppercase">{t("initiatives.without_goal")}</span>
              {node.initiatives.map((initiative) => (
                <TreeLink
                  key={initiative.id}
                  initiative={initiative}
                  href={hrefOf(initiative)}
                  isActive={isActive(initiative)}
                />
              ))}
            </div>
          );
        const goal = node.goal;
        const isFolded = folded[goal.id] ?? false;
        return (
          <div key={goal.id} className="flex flex-col gap-0.5">
            <div className="flex items-center">
              <button
                type="button"
                className="grid size-5 shrink-0 place-items-center rounded-sm text-tertiary hover:bg-layer-transparent-hover"
                aria-label={t(isFolded ? "initiatives.expand_goal" : "initiatives.collapse_goal", { name: goal.name })}
                aria-expanded={!isFolded}
                disabled={node.initiatives.length === 0}
                onClick={() => setFolded((current) => ({ ...current, [goal.id]: !isFolded }))}
              >
                {node.initiatives.length > 0 &&
                  (isFolded ? <ChevronRightOutline className="size-3" /> : <ChevronDownOutline className="size-3" />)}
              </button>
              <TreeLink initiative={goal} href={hrefOf(goal)} isActive={isActive(goal)} />
            </div>
            {!isFolded &&
              node.initiatives.map((initiative) => (
                <TreeLink
                  key={initiative.id}
                  initiative={initiative}
                  href={hrefOf(initiative)}
                  isActive={isActive(initiative)}
                  nested
                />
              ))}
          </div>
        );
      })}
    </div>
  );
});

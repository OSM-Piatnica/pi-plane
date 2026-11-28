/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { Menu, MenuContent, MenuItem, MenuTrigger } from "@makeplane/propel/components/menu";
import { useTranslation } from "@plane/i18n";
import type { TInitiative } from "@plane/types";
import { InitiativeIcon } from "@/components/initiatives/properties";
import { useProject } from "@/hooks/store/use-project";
import { useAppRouter } from "@/hooks/use-app-router";
import { useProjectInitiatives } from "@/hooks/use-project-initiatives";

const CHIP_CLASSNAME =
  "inline-flex h-6 max-w-48 shrink-0 items-center gap-1 rounded-sm border border-subtle px-1.5 text-11 text-secondary hover:bg-layer-transparent-hover";

/**
 * The initiatives of a project, next to its name in the project header (roadmap F3). One initiative is a link
 * to it; several open a menu of them. Nothing while the Initiatives feature is off, for workspace guests, and
 * for a project in no initiative.
 */
export const ProjectInitiativeChip = observer(function ProjectInitiativeChip(props: {
  workspaceSlug: string;
  projectId: string;
}) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const router = useAppRouter();
  const { getProjectById } = useProject();
  const { isEnabled, getInitiativeById } = useProjectInitiatives();

  if (!isEnabled) return null;
  const initiatives = (getProjectById(projectId)?.initiative_ids ?? [])
    .map((initiativeId) => getInitiativeById(initiativeId))
    .filter((initiative): initiative is TInitiative => !!initiative);
  if (initiatives.length === 0) return null;

  const [first] = initiatives;
  const hrefOf = (initiative: TInitiative) => `/${workspaceSlug}/initiatives/${initiative.id}`;
  const label = t("initiatives.project_list.of_project");
  const content = (
    <>
      <InitiativeIcon kind={first.kind} status={first.status} className="size-3.5" />
      <span className="truncate">{first.name}</span>
      {initiatives.length > 1 && <span className="shrink-0 text-tertiary">+{initiatives.length - 1}</span>}
    </>
  );

  if (initiatives.length === 1)
    return (
      <Link href={hrefOf(first)} className={CHIP_CLASSNAME} aria-label={`${label}: ${first.name}`} title={label}>
        {content}
      </Link>
    );

  return (
    <Menu>
      <MenuTrigger render={<button type="button" className={CHIP_CLASSNAME} aria-label={label} title={label} />}>
        {content}
      </MenuTrigger>
      <MenuContent side="bottom" align="start">
        {initiatives.map((initiative) => (
          <MenuItem key={initiative.id} label={initiative.name} onClick={() => router.push(hrefOf(initiative))} />
        ))}
      </MenuContent>
    </Menu>
  );
});

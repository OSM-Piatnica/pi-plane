/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ContentWrapper } from "@plane/blocks/layout";
import { useTranslation } from "@plane/i18n";
import type { TProject } from "@plane/types";
import { PROJECT_NO_INITIATIVE, groupProjectsByInitiative } from "@plane/utils";
import { InitiativeIcon } from "@/components/initiatives/properties";
import { getInitiativeOrder } from "@/helpers/initiatives";
import { useProject } from "@/hooks/store/use-project";
import { useProjectInitiatives } from "@/hooks/use-project-initiatives";
import { ProjectCard } from "./card";

function GroupHeading(props: { initiativeId: string; count: number }) {
  const { initiativeId, count } = props;
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const { getInitiativeById } = useProjectInitiatives();
  const initiative = getInitiativeById(initiativeId);
  const goal = getInitiativeById(initiative?.parent ?? undefined);

  return (
    <h2 className="flex min-w-0 items-center gap-2 text-14 font-medium text-primary">
      {initiativeId === PROJECT_NO_INITIATIVE ? (
        <span>{t("initiatives.project_list.no_initiative")}</span>
      ) : (
        <Link
          href={`/${workspaceSlug?.toString() ?? ""}/initiatives/${initiativeId}`}
          className="flex min-w-0 items-center gap-1.5 hover:underline"
        >
          {initiative && <InitiativeIcon kind={initiative.kind} status={initiative.status} />}
          <span className="truncate">{initiative?.name ?? t("initiatives.kind.initiative")}</span>
        </Link>
      )}
      {goal && <span className="font-normal truncate text-12 text-tertiary">{goal.name}</span>}
      <span className="font-normal shrink-0 text-12 text-tertiary">{count}</span>
    </h2>
  );
}

/**
 * The project list grouped by initiative (roadmap F3): one group per initiative in the order of the
 * Initiatives app, a project in several initiatives in each of their groups, and the projects without an
 * initiative last.
 */
export const ProjectInitiativeGroups = observer(function ProjectInitiativeGroups(props: { projectIds: string[] }) {
  const { projectIds } = props;
  const { getProjectById } = useProject();
  const { tree } = useProjectInitiatives();

  const projects = projectIds
    .map((projectId) => getProjectById(projectId))
    .filter((project): project is TProject => !!project);
  const groups = groupProjectsByInitiative(projects, getInitiativeOrder(tree));

  return (
    <ContentWrapper>
      <div className="flex flex-col gap-8">
        {groups.map((group) => (
          <section key={group.key} className="flex flex-col gap-3">
            <GroupHeading initiativeId={group.key} count={group.projectIds.length} />
            <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
              {group.projectIds.map((projectId) => {
                const project = getProjectById(projectId);
                if (!project) return null;
                return <ProjectCard key={project.id} project={project} />;
              })}
            </div>
          </section>
        ))}
      </div>
    </ContentWrapper>
  );
});

/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { InitiativeOutline, RightSidePaneOutline } from "@makeplane/propel/icons";
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { EmptyStateDetailed } from "@plane/blocks/empty-state";
import { Header } from "@plane/blocks/layout";
import { Loader } from "@plane/blocks/skeleton";
import { useTranslation } from "@plane/i18n";
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
import { PageHead } from "@/components/core/page-title";
import { DeleteInitiativeModal } from "@/components/initiatives/delete-modal";
import { InitiativeDetailRoot } from "@/components/initiatives/detail/root";
import { canDeleteInitiative } from "@/helpers/initiatives";
import { useAppTheme } from "@/hooks/store/use-app-theme";
import { useInitiative } from "@/hooks/store/use-initiative";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";

function InitiativeDetailPage() {
  const { t } = useTranslation();
  const router = useAppRouter();
  const { workspaceSlug, initiativeId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const id = initiativeId?.toString() ?? "";
  const { getInitiativeById, fetchInitiative } = useInitiative();
  const { toggleInitiativesSidebar, initiativesSidebarCollapsed } = useAppTheme();
  const { data: currentUser } = useUser();
  const { getWorkspaceRoleByWorkspaceSlug } = useUserPermissions();
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  // fresh numbers whenever the page is opened; the list may be older
  const { error } = useSWR(slug && id ? `INITIATIVE_${slug}_${id}` : null, () => fetchInitiative(slug, id), {
    revalidateOnFocus: false,
  });
  const initiative = getInitiativeById(id);
  const goal = getInitiativeById(initiative?.parent ?? undefined);
  const canDelete =
    !!initiative && canDeleteInitiative(initiative, currentUser?.id, getWorkspaceRoleByWorkspaceSlug(slug));

  const header = (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                href={`/${slug}/initiatives/`}
                label={t("initiatives.title")}
                icon={<InitiativeOutline className="size-4 text-tertiary" />}
              />
            }
          />
          {goal && (
            <Breadcrumbs.Item
              component={<BreadcrumbLink href={`/${slug}/initiatives/${goal.id}`} label={goal.name} />}
            />
          )}
          {initiative && <Breadcrumbs.Item component={<BreadcrumbLink label={initiative.name} />} />}
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        {canDelete && (
          <Button
            variant="danger-outline"
            size="md"
            stretch="auto"
            label={t("initiatives.delete.action")}
            onClick={() => setIsDeleteOpen(true)}
          />
        )}
        <IconButton
          size="lg"
          variant="ghost"
          icon={<Icon icon={RightSidePaneOutline} />}
          aria-label={t(initiativesSidebarCollapsed ? "initiatives.show_properties" : "initiatives.hide_properties")}
          aria-pressed={!initiativesSidebarCollapsed}
          onClick={() => toggleInitiativesSidebar()}
        />
      </Header.RightItem>
    </Header>
  );

  return (
    <>
      <PageHead title={initiative?.name ?? t("initiatives.title")} />
      <AppHeader header={header} />
      <ContentWrapper>
        {initiative ? (
          <InitiativeDetailRoot workspaceSlug={slug} initiative={initiative} />
        ) : error ? (
          <div className="grid size-full place-items-center p-6">
            <EmptyStateDetailed
              assetKey="initiative"
              title={t("initiatives.not_found.title")}
              description={t("initiatives.not_found.description")}
              align="center"
              actions={[
                {
                  label: t("initiatives.all"),
                  variant: "primary",
                  onClick: () => router.push(`/${slug}/initiatives/`),
                },
              ]}
            />
          </div>
        ) : (
          <Loader className="flex flex-col gap-3 p-10">
            <Loader.Item height="36px" width="50%" />
            <Loader.Item height="120px" />
            <Loader.Item height="80px" />
          </Loader>
        )}
      </ContentWrapper>
      {initiative && (
        <DeleteInitiativeModal
          workspaceSlug={slug}
          initiative={initiative}
          isOpen={isDeleteOpen}
          onClose={() => setIsDeleteOpen(false)}
        />
      )}
    </>
  );
}

export default observer(InitiativeDetailPage);

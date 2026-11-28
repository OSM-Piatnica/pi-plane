/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Button } from "@makeplane/propel/components/button";
import { InitiativeOutline } from "@makeplane/propel/icons";
import { Breadcrumbs } from "@plane/blocks/breadcrumb";
import { EmptyStateDetailed } from "@plane/blocks/empty-state";
import { Header } from "@plane/blocks/layout";
import { Loader } from "@plane/blocks/skeleton";
import { useTranslation } from "@plane/i18n";
import type { TInitiativeKind } from "@plane/types";
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
import { PageHead } from "@/components/core/page-title";
import { CreateInitiativeModal } from "@/components/initiatives/create-modal";
import { InitiativesList } from "@/components/initiatives/list";
import { useInitiative } from "@/hooks/store/use-initiative";

function InitiativesPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { tree, isListLoaded } = useInitiative();
  const [creating, setCreating] = useState<TInitiativeKind | undefined>(undefined);

  const header = (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                label={t("initiatives.title")}
                icon={<InitiativeOutline className="size-4 text-tertiary" />}
              />
            }
          />
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        <Button
          variant="secondary"
          size="md"
          stretch="auto"
          label={t("initiatives.new_goal")}
          onClick={() => setCreating("goal")}
        />
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          label={t("initiatives.new_initiative")}
          onClick={() => setCreating("initiative")}
        />
      </Header.RightItem>
    </Header>
  );

  return (
    <>
      <PageHead title={t("initiatives.title")} />
      <AppHeader header={header} />
      <ContentWrapper>
        {!isListLoaded ? (
          <Loader className="flex flex-col gap-2 p-6">
            <Loader.Item height="40px" />
            <Loader.Item height="40px" />
            <Loader.Item height="40px" />
          </Loader>
        ) : tree.length === 0 ? (
          <div className="grid size-full place-items-center p-6">
            <EmptyStateDetailed
              assetKey="initiative"
              title={t("initiatives.empty.title")}
              description={t("initiatives.empty.description")}
              align="center"
              actions={[
                {
                  label: t("initiatives.new_initiative"),
                  variant: "primary",
                  onClick: () => setCreating("initiative"),
                },
                { label: t("initiatives.new_goal"), variant: "secondary", onClick: () => setCreating("goal") },
              ]}
            />
          </div>
        ) : (
          <InitiativesList workspaceSlug={slug} />
        )}
      </ContentWrapper>
      {creating && (
        <CreateInitiativeModal workspaceSlug={slug} kind={creating} isOpen onClose={() => setCreating(undefined)} />
      )}
    </>
  );
}

export default observer(InitiativesPage);

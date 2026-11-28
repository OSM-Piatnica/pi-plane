/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Button } from "@makeplane/propel/components/button";
import { TextAreaField } from "@makeplane/propel/components/text-area-field";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TInitiative, TInitiativeHealth } from "@plane/types";
import { calculateTimeAgo, renderFormattedDate } from "@plane/utils";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
import { getInitiativeErrorMessage } from "@/helpers/initiatives";
import { useInitiative } from "@/hooks/store/use-initiative";
import { InitiativeHealthBadge, InitiativeHealthSelect } from "../properties";

/** Status updates: how it is going, as a health and a text. The newest health is the initiative's health. */
export const InitiativeUpdates = observer(function InitiativeUpdates(props: {
  workspaceSlug: string;
  initiative: TInitiative;
}) {
  const { workspaceSlug, initiative } = props;
  const { t } = useTranslation();
  const { updatesMap, fetchUpdates, createUpdate } = useInitiative();
  const [health, setHealth] = useState<TInitiativeHealth | null>(initiative.health);
  const [text, setText] = useState("");
  const [isPosting, setIsPosting] = useState(false);
  const { isLoading } = useSWR(`INITIATIVE_UPDATES_${initiative.id}`, () => fetchUpdates(workspaceSlug, initiative.id));
  const updates = updatesMap[initiative.id] ?? [];

  const post = async () => {
    if (!health) return;
    setIsPosting(true);
    try {
      await createUpdate(workspaceSlug, initiative.id, { health, text: text.trim() });
      setText("");
      setToast({ type: "success", title: t("toast.success"), message: t("initiatives.updates.posted") });
    } catch (error) {
      setToast({ type: "error", title: t("toast.error"), message: getInitiativeErrorMessage(error, t) });
    } finally {
      setIsPosting(false);
    }
  };

  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-14 font-medium text-primary">{t("initiatives.updates.title")}</h3>
      <form
        className="flex flex-col gap-2 rounded-md border border-subtle p-3"
        onSubmit={(event) => {
          event.preventDefault();
          void post();
        }}
      >
        <TextAreaField
          size="lg"
          resize="none"
          autoResize
          maxRows={8}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t("initiatives.updates.placeholder")}
          aria-label={t("initiatives.updates.text")}
        />
        <div className="flex items-center justify-between gap-2">
          <InitiativeHealthSelect value={health} onChange={setHealth} />
          <Button
            variant="primary"
            size="sm"
            stretch="auto"
            type="submit"
            disabled={!health}
            loading={isPosting}
            label={t("initiatives.updates.post")}
          />
        </div>
      </form>
      {!isLoading && updates.length === 0 && <p className="text-13 text-tertiary">{t("initiatives.updates.empty")}</p>}
      <ol className="flex flex-col gap-3">
        {updates.map((update) => (
          <li key={update.id} className="flex flex-col gap-1.5 rounded-md border border-subtle p-3">
            <div className="flex flex-wrap items-center gap-2 text-12 text-tertiary">
              <ButtonAvatars showTooltip={false} userIds={update.author} />
              <span className="font-medium text-primary">{update.author_detail?.display_name}</span>
              <InitiativeHealthBadge health={update.health} />
              <time dateTime={update.created_at} title={renderFormattedDate(update.created_at) ?? undefined}>
                {calculateTimeAgo(update.created_at)}
              </time>
            </div>
            {update.text && <p className="text-13 whitespace-pre-wrap text-secondary">{update.text}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
});

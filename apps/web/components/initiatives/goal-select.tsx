/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { FlagOutline } from "@makeplane/propel/icons";
import { Select } from "@plane/blocks/select";
import type { SelectVariant } from "@plane/blocks/select";
import { useTranslation } from "@plane/i18n";
import { useInitiative } from "@/hooks/store/use-initiative";

type TGoalOption = { id: string; name: string };

const NO_GOAL = "";

/** The goal of an initiative: one of the workspace's goals, or none */
export const InitiativeGoalSelect = observer(function InitiativeGoalSelect(props: {
  value: string | null;
  onChange: (goalId: string | null) => void;
  disabled?: boolean;
  variant?: SelectVariant;
}) {
  const { value, onChange, disabled = false, variant = "pill-md" } = props;
  const { t } = useTranslation();
  const { goals } = useInitiative();
  const noGoal: TGoalOption = { id: NO_GOAL, name: t("initiatives.no_goal") };
  const options: TGoalOption[] = goals.map((goal) => ({ id: goal.id, name: goal.name }));
  const selected = options.find((option) => option.id === value) ?? null;

  return (
    <Select<TGoalOption>
      getValues={() => options}
      headerItems={[noGoal]}
      value={selected}
      onChange={(id) => onChange(id || null)}
      getOptionValue={(option) => option.id}
      getOptionLabel={(option) => option.name}
      getOptionIcon={(option) => (option.id ? <FlagOutline className="size-3.5" /> : undefined)}
      disabled={disabled}
      placeholder={t("initiatives.no_goal")}
      emptyMessage={t("initiatives.no_goals_yet")}
    >
      <Select.Trigger<TGoalOption>
        variant={variant}
        disabled={disabled}
        prependIcon={() => <FlagOutline className="size-3.5" />}
        label={(picked) => picked[0]?.name ?? t("initiatives.no_goal")}
      >
        {(picked) => <span className="truncate">{picked[0]?.name ?? t("initiatives.no_goal")}</span>}
      </Select.Trigger>
    </Select>
  );
});

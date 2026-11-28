/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@makeplane/propel/components/button";
import { Checkbox } from "@makeplane/propel/components/checkbox";
import { setToast } from "@plane/blocks/toast";
import { RACI_ROLES } from "@plane/types";
import type {
  TRaciNotificationEvent,
  TRaciNotificationMatrix,
  TRaciNotificationSettings,
  TRaciRole,
} from "@plane/types";
import { isDefaultRaciNotificationMatrix, toggleRaciNotificationRole } from "@plane/utils";
// hooks
import { useWorkspaceFeatures } from "@/hooks/use-workspace-features";
// services
import { issueRaciService } from "@/services/issue/raci.service";

type Props = {
  workspaceSlug: string;
};

/**
 * The RACI notification matrix of the workspace: for every event on a work item, which roles hear about it. Shown
 * while the workspace has RACI on; each tick is saved at once.
 */
export const RaciNotificationSettings = observer(function RaciNotificationSettings(props: Props) {
  const { workspaceSlug } = props;
  // translation
  const { t } = useTranslation();
  // store hooks
  const { isFeatureEnabled } = useWorkspaceFeatures();
  const isEnabled = isFeatureEnabled("raci");
  const { data, mutate } = useSWR<TRaciNotificationSettings>(
    isEnabled ? `RACI_NOTIFICATION_SETTINGS_${workspaceSlug}` : null,
    () => issueRaciService.getNotificationSettings(workspaceSlug),
    { revalidateOnFocus: false }
  );

  if (!isEnabled || !data) return null;

  const save = async (changes: Partial<TRaciNotificationMatrix>) => {
    try {
      await mutate(() => issueRaciService.updateNotificationSettings(workspaceSlug, changes), {
        optimisticData: { ...data, matrix: { ...data.matrix, ...changes } },
        rollbackOnError: true,
        revalidate: false,
      });
    } catch (error) {
      setToast({
        type: "error",
        title: t("toast.error"),
        message: (error as { error?: string } | undefined)?.error ?? t("something_went_wrong_please_try_again"),
      });
    }
  };

  const handleToggle = (event: TRaciNotificationEvent, role: TRaciRole) =>
    void save({ [event]: toggleRaciNotificationRole(data.matrix[event], role) });

  return (
    <section className="flex flex-col gap-3 pt-8">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h4 className="text-h4-medium">{t("raci.notifications.settings_title")}</h4>
          <p className="text-13 text-secondary">{t("raci.notifications.settings_description")}</p>
        </div>
        <Button
          size="md"
          stretch="auto"
          variant="secondary"
          disabled={isDefaultRaciNotificationMatrix(data.matrix, data.defaults)}
          onClick={() => void save(data.defaults)}
          label={t("raci.notifications.restore_defaults")}
        />
      </div>
      <div className="overflow-x-auto rounded-lg border border-subtle">
        <table className="w-full text-13">
          <thead>
            <tr className="border-b border-subtle text-left text-secondary">
              <th scope="col" className="px-4 py-2 font-medium">
                {t("raci.notifications.event")}
              </th>
              {RACI_ROLES.map((role) => (
                <th
                  key={role}
                  scope="col"
                  className="w-20 px-2 py-2 text-center font-medium"
                  title={t(`raci.roles.${role}.name`)}
                >
                  {t(`raci.roles.${role}.letter`)}
                  <span className="sr-only"> {t(`raci.roles.${role}.name`)}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-subtle">
            {data.events.map((event) => (
              <tr key={event}>
                <th scope="row" className="font-normal px-4 py-2 text-left text-primary">
                  {t(`raci.notifications.events.${event}`)}
                  {(event === "approval_requested" || event === "approval_decided") && (
                    <span className="block text-11 text-tertiary">{t("raci.notifications.with_acceptance")}</span>
                  )}
                </th>
                {RACI_ROLES.map((role) => (
                  <td key={role} className="px-2 py-2 text-center">
                    <span className="inline-flex justify-center">
                      <Checkbox
                        checked={data.matrix[event]?.includes(role) ?? false}
                        onCheckedChange={() => handleToggle(event, role)}
                        aria-label={t("raci.notifications.toggle", {
                          role: t(`raci.roles.${role}.name`),
                          event: t(`raci.notifications.events.${event}`),
                        })}
                      />
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-11 text-tertiary">{t("raci.notifications.settings_hint")}</p>
    </section>
  );
});

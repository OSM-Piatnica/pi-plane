/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// plane imports
import { CyclesOutline, ModuleOutline, PagesOutline, ViewsOutline, WorkItemsOutline } from "@makeplane/propel/icons";
import type { ISvgIcons } from "@plane/blocks/icons";
// types
import type { TTourSteps } from "./root";
import { renderTaggedText } from "@/helpers/tagged-text";
import { useTranslation } from "@plane/i18n";

const sidebarOptions: {
  key: TTourSteps;
  labelKey: string;
  Icon: React.FC<ISvgIcons>;
}[] = [
  {
    key: "work-items",
    labelKey: "common.work_items",
    Icon: WorkItemsOutline,
  },
  {
    key: "cycles",
    labelKey: "common.cycles",
    Icon: CyclesOutline,
  },
  {
    key: "modules",
    labelKey: "common.modules",
    Icon: ModuleOutline,
  },
  {
    key: "views",
    labelKey: "common.views",
    Icon: ViewsOutline,
  },
  {
    key: "pages",
    labelKey: "common.pages",
    Icon: PagesOutline,
  },
];

type Props = {
  step: TTourSteps;
  setStep: React.Dispatch<React.SetStateAction<TTourSteps>>;
};

export function TourSidebar({ step, setStep }: Props) {
  const { t } = useTranslation();
  return (
    <div className="col-span-3 hidden bg-surface-2 p-8 lg:block">
      <h3 className="text-16 font-medium">
        {renderTaggedText(t("app_text.tour.sidebar_heading"), { br: () => <br /> })}
      </h3>
      <div className="mt-8 space-y-5">
        {sidebarOptions.map((option) => (
          <button
            type="button"
            key={option.key}
            className={`flex w-full cursor-pointer items-center gap-2 border-l-[3px] py-0.5 pr-2 pl-3 text-left text-13 font-medium capitalize ${
              step === option.key ? "border-accent-strong text-accent-primary" : "border-transparent text-secondary"
            }`}
            onClick={() => setStep(option.key)}
          >
            <option.Icon className="h-4 w-4" aria-hidden="true" />
            {t(option.labelKey)}
          </button>
        ))}
      </div>
    </div>
  );
}

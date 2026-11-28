/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssue, TTimelineColorBy } from "@plane/types";
import { useRaciBarColors } from "@/components/issues/raci/use-raci-bar-colors";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useChartPalette } from "@/hooks/use-chart-palette";
import { getBarColor } from "./bar-color";

/** The colour of a work item's timeline bar (or marker) for the chosen "colour by", and the RACI stripes. */
export function useIssueGanttBarColor(
  workspaceSlug: string | undefined,
  issue: TIssue | undefined,
  colorBy: TTimelineColorBy | undefined
) {
  const { getProjectStates } = useProjectState();
  const { getProjectIdentifierById } = useProject();
  const chartPalette = useChartPalette();
  const stateDetails = issue && getProjectStates(issue.project_id)?.find((state) => state?.id == issue.state_id);
  // RACI: the colours of the responsible departments, when the bars are coloured by them
  const { colors: departmentColors, backgroundImage } = useRaciBarColors(workspaceSlug, colorBy, issue?.raci);

  const barColor = getBarColor({
    colorBy,
    stateColor: stateDetails?.color,
    projectIdentifier: getProjectIdentifierById(issue?.project_id),
    sequenceId: issue?.sequence_id,
    palette: chartPalette,
    departmentColors,
  });
  return { barColor, backgroundImage };
}

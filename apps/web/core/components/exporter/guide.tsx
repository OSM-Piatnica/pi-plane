/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { mutate } from "swr";
import { EXPORT_SERVICES_LIST, PROJECT_IMPORT_SERVICES_LIST } from "@/constants/fetch-keys";
import { ImportForm } from "@/components/importer/import-form";
import { PrevImports } from "@/components/importer/prev-imports";
import { WorkItemImportForm } from "@/components/importer/work-item-import-form";
import { ExportForm } from "./export-form";
import { PrevExports } from "./prev-exports";
import { ProjectExportForm } from "./project-export-form";

export const ExportGuide = observer(function ExportGuide() {
  const { workspaceSlug } = useParams();
  const per_page = 10;
  const [exportCursor, setExportCursor] = useState<string | undefined>(`10:0:0`);
  const [importCursor, setImportCursor] = useState<string | undefined>(`10:0:0`);

  const refreshExports = () => mutate(EXPORT_SERVICES_LIST(workspaceSlug as string, `${exportCursor}`, `${per_page}`));

  const refreshImports = () =>
    mutate(PROJECT_IMPORT_SERVICES_LIST(workspaceSlug as string, `${importCursor}`, `${per_page}`));

  return (
    <div className="flex size-full flex-col gap-y-13">
      <section className="flex flex-col gap-y-6" aria-label="1. Export work items">
        <div id="export-work-items">
          <ExportForm workspaceSlug={workspaceSlug as string} provider={null} mutateServices={refreshExports} />
        </div>
        <PrevExports
          workspaceSlug={workspaceSlug as string}
          cursor={exportCursor}
          per_page={per_page}
          setCursor={setExportCursor}
        />
      </section>

      <section className="flex flex-col gap-y-6 border-t border-subtle pt-13" aria-label="2. Import work items">
        <div id="import-work-items">
          <WorkItemImportForm mutateServices={refreshImports} />
        </div>
      </section>

      <section className="flex flex-col gap-y-6 border-t border-subtle pt-13" aria-label="3–4. Project configuration">
        <div id="import-project-config">
          <ImportForm mutateServices={refreshImports} />
        </div>
        <PrevImports
          workspaceSlug={workspaceSlug as string}
          cursor={importCursor}
          per_page={per_page}
          setCursor={setImportCursor}
        />
        <div id="export-project-config">
          <ProjectExportForm workspaceSlug={workspaceSlug as string} />
        </div>
      </section>
    </div>
  );
});

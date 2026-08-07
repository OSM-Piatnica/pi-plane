/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams, useSearchParams } from "next/navigation";
import { mutate } from "swr";
// constants
import { EXPORT_SERVICES_LIST, PROJECT_IMPORT_SERVICES_LIST } from "@/constants/fetch-keys";
import { ImportForm } from "@/components/importer/import-form";
import { PrevImports } from "@/components/importer/prev-imports";
import { ExportForm } from "./export-form";
import { PrevExports } from "./prev-exports";
import { ProjectExportForm } from "./project-export-form";

export const ExportGuide = observer(function ExportGuide() {
  const { workspaceSlug } = useParams();
  const searchParams = useSearchParams();
  const provider = searchParams.get("provider");
  const per_page = 10;
  const [exportCursor, setExportCursor] = useState<string | undefined>(`10:0:0`);
  const [importCursor, setImportCursor] = useState<string | undefined>(`10:0:0`);

  return (
    <div className="flex size-full flex-col gap-y-13">
      <div id="export">
        <ExportForm
          workspaceSlug={workspaceSlug as string}
          provider={provider}
          mutateServices={() =>
            mutate(EXPORT_SERVICES_LIST(workspaceSlug as string, `${exportCursor}`, `${per_page}`))
          }
        />
      </div>
      <PrevExports
        workspaceSlug={workspaceSlug as string}
        cursor={exportCursor}
        per_page={per_page}
        setCursor={setExportCursor}
      />
      <div id="import">
        <ImportForm
          mutateServices={() =>
            mutate(PROJECT_IMPORT_SERVICES_LIST(workspaceSlug as string, `${importCursor}`, `${per_page}`))
          }
        />
      </div>
      <PrevImports
        workspaceSlug={workspaceSlug as string}
        cursor={importCursor}
        per_page={per_page}
        setCursor={setImportCursor}
      />
      <ProjectExportForm workspaceSlug={workspaceSlug as string} />
    </div>
  );
});

<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Document viewer

The web app can show PDFs and images in a viewer instead of opening them in a new browser tab. Its behaviour
follows the Studio opakowań v5 prototype (roadmap step C2, `docs/plans/workflow-roadmap.md`); annotations come
in C3.

## Where it is used

- **Work item attachments.** Clicking a PDF or image in the attachment list opens the viewer; other files
  download as before. The row menu has "Preview" (for PDFs and images) and "Download".
- Later: versions in the document store (B3) and the acceptance panel (C4, C6) use the same component.

## What it does

- **Formats.** PDF (rendered with PDF.js), JPG, PNG, WebP and GIF. SVG is shown through `<img>` only, never
  inlined into the page, so it cannot run scripts or load anything. Other formats (AI, PSD, TIFF, Office) are not
  rendered: the viewer shows the source's own thumbnail if it has one (SharePoint gives one, from B3) and
  "Download".
- **Zoom.** Minus and plus in 25 % steps from 25 % to 400 %, "Fit" (the whole page with a 20 px margin; follows
  the window size), "100%", and Ctrl (or Cmd) + mouse wheel. A zoomed page scrolls both ways; the scroll area
  takes keyboard focus.
- **Pages.** Previous and next page for PDFs, with "page / pages".
- **Compare.** "Compare" lists the other previewable files (for attachments: the other PDFs and images of the
  same work item, with a thumbnail of the first page) and shows the chosen one next to the current file. Each
  panel has its own zoom and page and renders the original file. On narrow screens the panels stack.
- **Download** always returns the original bytes.

The viewer fills the browser window (the Propel dialog has no free resizing); resizing the window resizes the
panels, and "Fit" follows.

## For developers

`apps/web/components/document-viewer/`:

| File                        | Purpose                                                                                   |
| --------------------------- | ----------------------------------------------------------------------------------------- |
| `types.ts`                  | `TDocumentSource` (the input), `TDocumentOverlayRenderer` (the layer for annotations)     |
| `helpers.ts`                | pure logic: preview kind, fit scale, zoom steps, canvas resolution cap, fetch credentials |
| `pdfjs.ts`                  | lazy loading of PDF.js and its worker, `openPdf`                                          |
| `use-loaded-document.ts`    | turns a source into an open PDF or an image URL                                           |
| `document-pane.tsx`         | one panel: toolbar, scrollable stage, canvas or `<img>`, overlay slot                     |
| `document-thumbnail.tsx`    | first page (or the image) in a square box                                                 |
| `document-viewer-modal.tsx` | the full-window dialog with "Compare"                                                     |

**Source.** The viewer does not know where a file comes from. A `TDocumentSource` has an `id`, a `name`, a
`mimeType`, and either a `url` or a `fetchFile(signal)` function returning a `Blob` or `ArrayBuffer`. Optional:
`downloadUrl`, `thumbnailUrl` (used for formats the viewer cannot render) and `caption`. Images with a `url` are
shown straight from it; everything else is fetched once per open viewer. When a URL points at the app's own
origin the request carries cookies only there (`same-origin`), so storage behind a redirect needs plain CORS,
not credentialed CORS; with a separate API origin (local development) it uses `include`.

Attachments use the attachment endpoint as the URL. It checks access and redirects to the stored file. With the
bundled MinIO behind the proxy everything is same-origin. With external S3 the bucket's CORS rules must allow
`GET` from the app's origin, as they already must allow the upload `POST`.

**Overlay.** `DocumentPane` and `DocumentViewerModal` take `renderOverlay(page)`, rendered `absolute inset-0` over
the page, with the page number, page count, scale and the page's size in CSS pixels. C3 draws annotations there
with relative coordinates; compare panels never get it.

**PDF.js.** `pdfjs-dist` (Apache-2.0) is in the pnpm catalog and imported only through dynamic `import()`, so it is
a separate chunk loaded the first time a PDF is opened. The legacy build is used: the modern one needs very recent
JavaScript (`Map.prototype.getOrInsertComputed`, `Math.sumPrecise`). Document scripts and XFA forms are off. The
`pdfjsAssets` Vite plugin (`apps/web/vite-plugins/pdfjs-assets.ts`) publishes the PDF.js data files (CMaps,
standard fonts, ICC profile, wasm image decoders) at `pdfjs/<version>/`: emitted into the client build and served
from `node_modules` by the dev server. Licences: [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md).

`pdf-lib` is not a dependency yet: the viewer does not need it. It comes with the "PDF with comments" export in
C3.

Tests: `apps/web/tests/unit/document-viewer-helpers.test.ts`.

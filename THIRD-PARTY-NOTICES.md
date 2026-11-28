<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Third-party notices

Pi-Plane is licensed under AGPL-3.0-only (see [LICENSE.txt](LICENSE.txt)). Most third-party packages it uses are listed with their licences in `pnpm-lock.yaml` and ship their licence files in `node_modules`. This file names the components that need a notice of their own because their files are shipped to the browser as they are, outside the JavaScript bundle, or because their licence asks for one.

## Document viewer (web)

The document viewer (`apps/web/components/document-viewer`, see [docs/document-viewer.md](docs/document-viewer.md)) loads these only when a PDF is opened. The web build copies the data files, together with their licence files, to `pdfjs/<version>/` next to the app's assets (`apps/web/vite-plugins/pdfjs-assets.ts`).

| Component                                                  | Version  | Licence                                    | Copyright                                           | Shipped as                                                                 |
| ---------------------------------------------------------- | -------- | ------------------------------------------ | --------------------------------------------------- | -------------------------------------------------------------------------- |
| [PDF.js](https://github.com/mozilla/pdf.js) (`pdfjs-dist`) | 6.5.438  | Apache-2.0                                 | Mozilla Foundation and contributors                 | lazily loaded script and worker; licence text at `pdfjs/<version>/LICENSE` |
| Adobe CMaps (in `pdfjs-dist/cmaps`)                        | as above | BSD-3-Clause                               | Adobe Systems Incorporated                          | `pdfjs/<version>/cmaps/`, licence in that folder                           |
| Foxit standard fonts (in `pdfjs-dist/standard_fonts`)      | as above | BSD-3-Clause (PDFium)                      | PDFium Authors                                      | `pdfjs/<version>/standard_fonts/`, `LICENSE_FOXIT`                         |
| Liberation fonts (in `pdfjs-dist/standard_fonts`)          | as above | GPL-2.0 with the Liberation font exception | Red Hat, Inc.                                       | `pdfjs/<version>/standard_fonts/`, `LICENSE_LIBERATION`                    |
| ICC profile (in `pdfjs-dist/iccs`)                         | as above | CC0-1.0                                    | none claimed                                        | `pdfjs/<version>/iccs/`, `LICENSE`                                         |
| OpenJPEG decoder (wasm, in `pdfjs-dist/wasm`)              | as above | BSD-2-Clause                               | OpenJPEG contributors; Mozilla Foundation           | `pdfjs/<version>/wasm/`, `LICENSE_OPENJPEG`, `LICENSE_PDFJS_OPENJPEG`      |
| JBIG2 decoder (wasm, from PDFium)                          | as above | BSD-3-Clause; Apache-2.0 for the wrapper   | PDFium Authors; Mozilla Foundation                  | `pdfjs/<version>/wasm/`, `LICENSE_JBIG2`, `LICENSE_PDFJS_JBIG2`            |
| qcms colour management (wasm)                              | as above | MIT                                        | Mozilla Corporation; Marti Maria                    | `pdfjs/<version>/wasm/`, `LICENSE_QCMS`, `LICENSE_PDFJS_QCMS`              |
| QuickJS (wasm, used by PDF.js only for document scripts)   | as above | MIT                                        | Fabrice Bellard, Charlie Gordon; Mozilla Foundation | `pdfjs/<version>/wasm/`, `LICENSE_QUICKJS`, `LICENSE_PDFJS_QUICKJS`        |

The viewer never runs scripts embedded in PDFs; QuickJS is shipped only because it is part of the PDF.js data folder.

`pdf-lib` (MIT) is not used yet. It is needed only to build the "PDF with comments" export of roadmap step C3 and will be added here with it.

### Apache License 2.0 notice for PDF.js

```
Copyright Mozilla Foundation and contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

PDF.js is used unmodified. The full licence text ships with the web build at `pdfjs/<version>/LICENSE` and in the npm package.

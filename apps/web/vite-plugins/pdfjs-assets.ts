/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import type { Plugin } from "vite";

/** The pdf.js data folders the document viewer passes to `getDocument` (see components/document-viewer/pdfjs.ts). */
const FOLDERS = ["cmaps", "iccs", "standard_fonts", "wasm"] as const;

const CONTENT_TYPES: Record<string, string> = {
  ".wasm": "application/wasm",
  ".js": "text/javascript",
};

/**
 * Publishes pdf.js's data files (CMaps, standard fonts, ICC profiles, wasm image decoders) at
 * `pdfjs/<version>/<folder>/<file>`: emitted into the client build, and served from node_modules by
 * the dev server. pdf.js fetches them by name only when a PDF needs them, so they cannot go through
 * Vite's hashed asset imports. The version in the path keeps caches correct across upgrades.
 */
export function pdfjsAssets(): Plugin {
  const require = createRequire(import.meta.url);
  const packageDir = path.dirname(require.resolve("pdfjs-dist/package.json"));
  const manifest: unknown = JSON.parse(fs.readFileSync(path.join(packageDir, "package.json"), "utf8"));
  const version =
    manifest && typeof manifest === "object" && "version" in manifest && typeof manifest.version === "string"
      ? manifest.version
      : undefined;
  if (!version) throw new Error("pdfjs-dist/package.json has no version");
  const prefix = `pdfjs/${version}`;

  // pdf.js's own Apache-2.0 licence goes along with the data files (see THIRD-PARTY-NOTICES.md).
  const listFiles = () => [
    { folder: ".", name: "LICENSE" },
    ...FOLDERS.flatMap((folder) =>
      fs
        .readdirSync(path.join(packageDir, folder), { withFileTypes: true })
        .filter((entry) => entry.isFile())
        .map((entry) => ({ folder, name: entry.name }))
    ),
  ];

  return {
    name: "pi-plane:pdfjs-assets",
    applyToEnvironment: (environment) => environment.name === "client",
    configureServer(server) {
      const files = new Map(
        listFiles().map(({ folder, name }) => [
          path.posix.join("/", prefix, folder, name),
          path.join(packageDir, folder, name),
        ])
      );
      const base = server.config.base.replace(/\/$/, "");
      server.middlewares.use((request, response, next) => {
        const url = (request.url ?? "").split("?")[0];
        // Only exact file names from the package are served, so no path can escape its folders.
        const file = files.get(url.startsWith(base) ? url.slice(base.length) : url);
        if (!file) return next();
        response.setHeader("Content-Type", CONTENT_TYPES[path.extname(file)] ?? "application/octet-stream");
        fs.createReadStream(file).pipe(response);
      });
    },
    generateBundle() {
      for (const { folder, name } of listFiles()) {
        this.emitFile({
          type: "asset",
          fileName: path.posix.join(prefix, folder, name),
          source: fs.readFileSync(path.join(packageDir, folder, name)),
        });
      }
    },
  };
}

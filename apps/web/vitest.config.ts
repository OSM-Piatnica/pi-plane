/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import path from "node:path";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // resolve the `@/*` aliases from tsconfig.json so tests can import app modules
  plugins: [tsconfigPaths({ projects: [path.resolve(import.meta.dirname, "tsconfig.json")] })],
  test: {
    environment: "node",
    globals: true,
    include: ["tests/**/*.test.ts", "app/**/*.test.ts"],
  },
});

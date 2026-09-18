/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// Usage: tsx packages/i18n/scripts/sync-locales-dir.ts
//
// core/instance.ts loads locale JSON at runtime via a relative dynamic
// import (`../locales/${language}/${namespace}.json`), resolved against
// dist/index.js after bundling. That means a `packages/i18n/locales`
// entry pointing at `src/locales` has to exist on disk.
//
// This used to be a git-tracked symlink, but git only creates a real
// symlink on checkout when the client has symlink support enabled
// (`core.symlinks=true` plus, on Windows, Developer Mode or admin
// rights). Without it, git silently checks the symlink out as a plain
// text file containing the target path string -- no error, no warning.
// The dynamic import then fails at runtime, and because i18next treats
// a missing resource as non-fatal, it falls back to rendering the raw
// key instead of crashing, which is very easy to miss.
//
// A plain recursive copy has no such prerequisite on any platform, so
// this regenerates `locales/` from `src/locales/` at build/dev time
// instead of relying on the symlink surviving the checkout.

import fs from "node:fs";
import path from "node:path";

const SRC = path.resolve(import.meta.dirname, "../src/locales");
const DEST = path.resolve(import.meta.dirname, "../locales");

if (fs.existsSync(DEST)) {
  const stat = fs.lstatSync(DEST);
  if (!stat.isSymbolicLink()) {
    fs.rmSync(DEST, { recursive: true, force: true });
  } else {
    fs.unlinkSync(DEST);
  }
}

fs.cpSync(SRC, DEST, { recursive: true });

console.log(`Synced ${SRC} -> ${DEST}`);

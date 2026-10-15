#!/usr/bin/env bash
# Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Run ruff check + format on the given Python files (used by lint-staged).
# Uses the ruff version pinned in apps/api/pyproject.toml (dev group).
set -euo pipefail

[ "$#" -eq 0 ] && exit 0

root="$(git rev-parse --show-toplevel)"
spec="$(grep -o '"ruff==[^"]*"' "$root/apps/api/pyproject.toml" | tr -d '"')"
version="${spec#ruff==}"

if command -v uvx >/dev/null 2>&1; then
  ruff=(uvx "ruff@$version")
elif command -v ruff >/dev/null 2>&1; then
  ruff=(ruff)
  installed="$(ruff --version | awk '{print $2}')"
  [ "$installed" = "$version" ] || echo "warning: ruff $installed installed, repo pins $version" >&2
else
  echo "warning: ruff not found (install uv or 'pip install $spec'); skipping Python lint/format" >&2
  exit 0
fi

"${ruff[@]}" check --fix "$@"
"${ruff[@]}" format "$@"

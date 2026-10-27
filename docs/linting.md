# Linting in Pi-Plane - How It Works

We use [OxLint](https://oxc.rs/docs/guide/usage/linter) for linting across the entire monorepo. OxLint is a single Rust binary that's 50-100x faster than ESLint, with zero Node.js dependencies at runtime.

## Key Points

1. **Single Root Config** - One `.oxlintrc.json` at the repo root handles all packages and apps
2. **No Build Required** - OxLint doesn't need TypeScript build artifacts, so lint runs independently of build
3. **Plugin Coverage** - react, typescript, jsx-a11y, import, promise, unicorn, oxc

## How to Run

From the root of the repo:

```bash
# Check for lint errors
pnpm check:lint

# Auto-fix lint errors
pnpm fix:lint
```

To lint a specific package:

```bash
pnpm turbo run check:lint --filter=@plane/blocks
```

## VS Code Integration

Install the [OxLint extension](https://marketplace.visualstudio.com/items?itemName=oxc.oxc-vscode) for inline errors/warnings as you type.

## What Gets Linted

The config applies to all TypeScript and JavaScript files across:

- `apps/web`, `apps/admin`, `apps/space`, `apps/live`
- The packages in `packages/` that define a `check:lint` script (not `codemods`, `tailwind-config` or `typescript-config`)

The backend (`apps/api`) is linted with ruff instead, see `apps/api/ruff.toml`; the pre-commit hook runs ruff on staged Python files too.

**Ignored paths:**

- `.cache/`, `.next/`, `.react-router/`, `.storybook/`, `.turbo/`, `.vite/`, `build/`, `dist/`
- Config files (`*.config.{js,mjs,cjs,ts}`)
- `public/` folders, `coverage/`, `storybook-static/`

## Rules Overview

OxLint uses category-based configuration:

| Category        | Level | What It Catches                          |
| --------------- | ----- | ---------------------------------------- |
| **correctness** | warn  | Real bugs that will cause runtime errors |
| **suspicious**  | warn  | Code patterns that are likely mistakes   |
| **perf**        | warn  | Performance anti-patterns                |

No category is an error. Instead each package caps its warnings (`--max-warnings=N` in its `check:lint` script, from 0 in `@plane/logger` to a few thousand in `web`), and `pnpm check:lint` fails when a package goes over its cap. New code should add none.

Additional rule overrides:

- `react/prop-types` off (TypeScript handles prop validation)
- `no-unused-vars` warns with `_` prefix pattern ignored
- Several noisy unicorn rules disabled

## Backward Compatibility

OxLint supports `eslint-disable` comments, so existing inline suppressions continue to work.

## Suppressing Warnings

```typescript
// Single line
// eslint-disable-next-line no-unused-vars
const data = response;

// Block
/* eslint-disable no-unused-vars */
// ... code
/* eslint-enable no-unused-vars */
```

**Please use sparingly** - most warnings indicate real issues that should be fixed.

## Pre-commit Hook

Lint-staged runs automatically on commit via Husky:

- oxfmt formats your staged files
- OxLint fixes what it can (with `--deny-warnings`)

If the commit fails due to lint errors, fix them before committing.

## Reference Files

- [.oxlintrc.json](../.oxlintrc.json) - OxLint configuration
- [package.json](../package.json) - Available scripts

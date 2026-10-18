# Contributing to Pi-Plane

Thank you for showing an interest in contributing to Pi-Plane, the OSM Piątnica fork of [Plane](https://github.com/makeplane/plane)! All kinds of contributions are valuable to us. In this guide, we will cover how you can quickly onboard and make your first contribution.

## Submitting an issue

Before submitting a new issue, please search the [issues](https://github.com/OSM-Piatnica/pi-plane/issues) tab. Maybe an issue or discussion already exists and might inform you of workarounds. Otherwise, you can give new information.

While we want to fix all the [issues](https://github.com/OSM-Piatnica/pi-plane/issues), before fixing a bug we need to be able to reproduce and confirm it. Please provide us with a minimal reproduction scenario using a repository or [Gist](https://gist.github.com/). Having a live, reproducible scenario gives us the information without asking questions back & forth with additional questions like:

- 3rd-party libraries being used and their versions
- a use-case that fails

Without said minimal reproduction, we won't be able to investigate all [issues](https://github.com/OSM-Piatnica/pi-plane/issues), and the issue might not be resolved.

You can open a new issue with this [issue form](https://github.com/OSM-Piatnica/pi-plane/issues/new).

### Naming conventions for issues

The issue forms prefill the title, so keep the prefix and add a clear, concise description after it:

- For bugs: `[bug]: short description`
- For feature requests: `[feature]: short description`

**Examples:**

- `[bug]: API token expiry time not saving correctly`
- `[feature]: Allow custom time selection for token expiration`

This helps us triage and manage issues more efficiently.

## Projects setup and Architecture

### Requirements

- Docker Engine installed and running
- Node.js 22.22.0 or newer (see `.node-version`) and [pnpm](https://pnpm.io/) (the exact version is pinned in `packageManager` in `package.json`; Corepack installs it)
- Python 3.12 and [uv](https://docs.astral.sh/uv/) at the exact version in `apps/api/pyproject.toml` (`required-version`); only needed to run the API outside Docker, with `cd apps/api && uv sync`
- Postgres 15 (the local compose file runs `postgres:15.7-alpine`)
- Valkey 7.2 as the Redis-compatible store (the local compose file runs `valkey/valkey:7.2.11-alpine`)
- **Memory**: Minimum **12 GB RAM** recommended
  > ⚠️ Running the project on a system with only 8 GB RAM may lead to setup failures or memory crashes (especially during Docker container build/start or dependency install). Use cloud environments like GitHub Codespaces or upgrade local RAM if possible.

### Setup the project

The project is a monorepo, with backend api and frontend in a single repo.

The backend is a django project which is kept inside apps/api

1. Clone the repo

```bash
git clone https://github.com/OSM-Piatnica/pi-plane.git [folder-name]
cd [folder-name]
chmod +x setup.sh
```

2. Run setup.sh

```bash
./setup.sh
```

3. Start the containers

```bash
docker compose -f compose-local.yaml up
```

4. Start web apps:

```bash
pnpm dev
```

5. Open your browser to http://localhost:3001/god-mode/ and register yourself as instance admin
6. Open up your browser to http://localhost:3000 then log in using the same credentials from the previous step

You’re all set to begin coding. Remember to refresh your browser if changes don’t auto-reload. Happy contributing! 🎉

## Missing a Feature?

If a feature is missing, you can directly _request_ a new one [here](https://github.com/OSM-Piatnica/pi-plane/issues/new/choose). You can also do the same by choosing "Feature request" when raising a [New Issue](https://github.com/OSM-Piatnica/pi-plane/issues/new/choose) on our GitHub Repository.
If you would like to _implement_ it, an issue with your proposal must be submitted first, to be sure that we can use it. Please consider the guidelines given below.

## Coding guidelines

To ensure consistency throughout the source code, please keep these rules in mind as you are working:

- All features or bug fixes must be tested by one or more specs (unit-tests).
- Run `pnpm check` (format, lint, types) before opening a PR, and `pnpm fix` to auto-fix what it can. Run `pnpm doctor` for React changes.
- Backend tests run in Docker: `docker compose -f compose-test.yaml run --rm --build api-tests pytest -m unit`. See `apps/api/tests/RUNNING_TESTS.md` and `apps/api/tests/TESTING_GUIDE.md`.
- We lint with [OxLint](https://oxc.rs/docs/guide/usage/linter) using the shared `.oxlintrc.json` and format with [oxfmt](https://oxc.rs/docs/guide/usage/formatter) using `.oxfmtrc.json`.
- Keep the per-file copyright notices accurate on every `.ts`, `.tsx` and `.py` file you touch (see the README, "per-file notices"). New files carry only the OSM Piątnica line, changed upstream files keep the Plane line and gain `Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.`, and substantially rewritten upstream files also gain the OSM Piątnica copyright line. JSON locale files carry no notice.

## Branches and pull requests

- Branch from an up-to-date `origin/preview` (`git fetch origin`) and open pull requests against `preview` in [OSM-Piatnica/pi-plane](https://github.com/OSM-Piatnica/pi-plane). Make sure the PR targets this fork, not `makeplane/plane`.
- Fill in the pull request template.

## Ways to contribute

- Try the self hosted platform and give feedback
- Add new integrations
- Add or update translations
- Help with open [issues](https://github.com/OSM-Piatnica/pi-plane/issues) or [create your own](https://github.com/OSM-Piatnica/pi-plane/issues/new/choose)
- Share your thoughts and suggestions with us
- Help create tutorials and blog posts
- Request a feature by submitting a proposal
- Report a bug
- **Improve documentation** - fix incomplete or missing docs, bad wording, examples or explanations.

## Contributing to language support

Translations live in `packages/i18n/src/locales/<language>/`. Before touching any locale file, read the translation rules in `.claude/skills/translate/` (do-not-translate terminology, CLDR plural forms, placeholder and tag preservation, per-locale punctuation and register, and the AI-translation review workflow).

### Understanding translation structure

#### File organization

Each language has its own folder containing one JSON file per namespace, and every language has the same set of files:

```
packages/i18n/src/locales/
    ├── en/
    │   ├── common.json
    │   ├── cycle.json
    │   ├── work-item.json
    │   └── ...             # one file per namespace
    ├── fr/
    │   └── ...             # same files as en/
    └── [language]/
        └── ...
```

English (`en`) is the source language and the fallback. Locale files are loaded at runtime by namespace (`packages/i18n/src/core/instance.ts`), so a new key goes into the namespace file that fits its feature area.

#### Nested structure

To keep translations organized, we use a nested structure for keys. For example, in `work-item.json`:

```json
{
  "label": "Work item",
  "title": {
    "label": "Work item title"
  }
}
```

Flattened keys must be unique across namespace files. `pnpm --filter @plane/i18n check:sync` reports collisions and keys that are missing from or extra in any language.

### Translation formatting guide

Messages use ICU syntax, handled by [IntlMessageFormat](https://formatjs.github.io/docs/intl-messageformat/), for dynamic content such as variables and pluralization.

- **Simple variables**

  ```json
  {
    "greeting": "Hello, {name}!"
  }
  ```

- **Pluralization**
  ```json
  {
    "items": "{count, plural, one {Work item} other {Work items}}"
  }
  ```

### Contributing guidelines

#### Updating existing translations

1. Locate the key in `locales/<language>/<namespace>.json`.
2. Update the value while keeping the key structure intact.
3. Preserve existing ICU formats (variables, pluralization) and any markup tags.

#### Adding new translation keys

1. Add the key to the matching namespace file in **all** language folders. Use English as a placeholder where a translation is not available yet.
2. Keep the nesting structure consistent across all languages.
3. If the key needs variables or pluralization, apply the same ICU format in every language.

### Adding new languages

1. **Update the type definitions**: add the language code to the `TLanguage` union in `packages/i18n/src/types/language.ts`.

2. **Register the language**: add an entry to `SUPPORTED_LANGUAGES` in `packages/i18n/src/constants/language.ts`, with the label written in the language itself:

   ```ts
   { label: "Your Language", value: "your-lang" },
   ```

3. **Create the translation files**: create `packages/i18n/src/locales/your-lang/` and add one JSON file for every namespace present in `en/`, then translate all keys.

No import logic needs to change: namespaces are resolved dynamically from the language code and file name.

### Quality checklist

Before submitting your contribution, please ensure the following:

- `pnpm --filter @plane/i18n check:sync` passes (no missing keys, extra keys or collisions).
- `pnpm --filter @plane/i18n check:types` and `pnpm check` pass.
- Nested structures match across all language folders.
- ICU message formats, placeholders and tags are intact.
- The language loads without errors in the app, and dynamic values and pluralization render as expected.

When in doubt, refer to the English translations for context.

## Need help? Questions and suggestions

Questions, suggestions, and thoughts are most welcome.

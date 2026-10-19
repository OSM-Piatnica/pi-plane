# Translation keys kept although nothing uses them

Locale files are plain JSON, which has no comments, so keys that are no longer used cannot be marked inside
`src/locales/*/*.json`. They are listed here instead. They are kept (in English and all 23 other locales) on purpose, so
that a component that comes back, or an upstream change that uses them again, does not need new translations.

Remove an entry from this list when the key is used again, or delete the key from every locale and the entry together.

| Key                                                         | File                      | English                                                                        | Why it is unused                                                                                                                         |
| ----------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `app_text.base_layouts.gantt`                               | `common.json`             | Gantt Layout                                                                   | Used by the generic `base-layouts` layout framework (`components/base-layouts/constants.ts`), which was deleted because no page used it. |
| `common.drop_here_to_move`                                  | `common.json`             | Drop here to move                                                              | Drop hint of the deleted `base-layouts` kanban and list groups.                                                                          |
| `common.no_items_in_this_group`                             | `common.json`             | No items in this group                                                         | Empty-group text of the same deleted components.                                                                                         |
| `workspace_settings.settings.billing_and_plans.title`       | `workspace-settings.json` | Billing & Plans                                                                | Label of the "Billing and plans" workspace settings entry, which was removed together with the billing comparison page.                  |
| `workspace_settings.settings.billing_and_plans.heading`     | `workspace-settings.json` | Billing & Plans                                                                | Heading of the removed billing page.                                                                                                     |
| `workspace_settings.settings.billing_and_plans.description` | `workspace-settings.json` | Choose your plan, manage subscriptions, and easily upgrade as your needs grow. | Description of the removed billing page.                                                                                                 |
| `common.upgrade_cta.talk_to_sales`                          | `common.json`             | Talk to Sales                                                                  | Button of the removed "talk to sales" plan card.                                                                                         |

<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Sharing a project on the web

A project can be shared on the web. This creates a link that **anyone on the internet** can open, with no account, to read the project. It is served by the `space` app under `/spaces/issues/<anchor>` (the `/spaces` base path is the `VITE_SPACE_BASE_PATH` setting). Earlier versions called this "Publish project".

Web sharing is not a visibility level. Who can find and join a project inside the workspace is set by its network:

| Network | Meaning                                                                                                    |
| ------- | ---------------------------------------------------------------------------------------------------------- |
| Secret  | Hidden from everyone who is not a member (workspace admins can still list and join it)                     |
| Private | Listed for workspace members; access needs approval or an invite (Guests only see projects they belong to) |
| Open    | Any workspace member, except Guests, can join                                                              |

Any of the three can also be shared on the web. "Open" does not mean "visible to the internet".

## Turning it on

Project admins see **Share on the web** in the project's menu in the sidebar. Pick the layouts to show (**List** and **Board**; at least one) and whether viewers may comment, react and vote, then **Turn on web sharing**. A confirmation lists what becomes visible; sharing starts only after you confirm it. Changing the settings of an already shared project does not ask again.

> **Known gap:** the menu item is limited to project admins, but the API call behind it (`POST /api/workspaces/<slug>/projects/<id>/project-deploy-boards/`) also accepts plain project members, and a member can switch sharing on or off through the API.

**Stop sharing** switches the link off: the link shows the not-found page. Turning sharing on again creates a **new** link with a new address; the old one never works again, so links you sent earlier must be sent again.

## What anyone with the link can see

Without signing in, a viewer can read:

- every work item that is shown on the project's lists: not archived, not a draft, not waiting in triage or intake, and not in an archived project. For each: description, state, priority, dates, labels, estimate, assignee and creator ids, the parent, and the description as stored;
- the project's name, description and cover, its states (except Triage), labels, and the names of its cycles and modules;
- the id, display name and avatar of every active project member;
- images embedded in work item descriptions and in comments, for anyone who holds the image's id;
- the votes and reactions on work items, **with the names and avatars of the people behind them, whether or not voting and reactions are switched on** (the switches only decide who may add them);
- comments, when comments are allowed: only those set to **Visible on the web** (the default for a comment is **Internal**, which stays inside the project).

The address of the shared project is also returned to anyone who knows the workspace's URL slug and the project's id (`GET /api/public/workspaces/<slug>/projects/<id>/anchor/`), so the link is not secret from people who know those two values.

Viewers cannot edit project content. Commenting, reacting and voting need a sign-in; a signed-in viewer can edit and delete their own comments and reactions.

The API can also share a project's **intake** (`intake` in the same call), which lets signed-in viewers read and submit intake items. The web interface never sets it.

The link keeps working until sharing is stopped, so share only a project that holds nothing confidential.

<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Bot tokens

A personal API token sees only the projects its owner belongs to. Integrations that index or answer questions about the whole workspace (for example the Microsoft 365 Copilot connector or an MCP server) need to read every project, without anybody adding a person to all of them.

An instance admin creates such a token in **God Mode → Bot tokens → Create bot token**: choose the workspace, a name, optionally what it is for and an expiry date. The token is shown once; copy it into the settings of the application that uses it.

## What happens

- The workspace gets a service account, **Pi-Plane API** (one per workspace; every bot token of the workspace belongs to it). It is a bot: it cannot sign in, and it does not show up in member lists, pickers, notifications or counts.
- The service account is a Member of the workspace and of every project in it, private and archived ones included. A project created later gets it right away.
- With its token the public API (`/api/v1/`, header `X-Api-Key`) returns everything a project member sees: projects, work items, states, assignees, comments, members and the groups (`/groups/?assignable=1&members=1` also lists who belongs to each group).
- **The token is read-only.** Any request other than `GET`, `HEAD` or `OPTIONS` is refused with 403, whatever the endpoint. Personal tokens of people keep working as before.

Only instance admins (the people who can open God Mode) can create, list and revoke bot tokens, whatever their role in the workspace. God Mode does not accept API tokens, so a bot token cannot be used to create another one. Because a bot token reads every project, keep the list of instance admins short; the list shows who created each token and when it was last used.

## Managing tokens

The list in God Mode shows, for each token, the workspace, how many projects it reads, the last four characters, expiry, last use and who created it. The token itself cannot be read back: if it is lost, revoke it and create a new one.

**Revoke** stops the token at once. A token with an expiry date stops working after that day. Revoking the last token leaves the service account in the projects; without a token it can do nothing.

## API

All under the instance admin session, like the rest of God Mode:

| Method | Path | |
| --- | --- | --- |
| `GET` | `/api/instances/service-tokens/` | the bot tokens, without the token values |
| `POST` | `/api/instances/service-tokens/` | `{"workspace": "<id or slug>", "label": "...", "description": "...", "expired_at": "2027-01-31"}`; the answer carries `token`, the only time it is returned |
| `DELETE` | `/api/instances/service-tokens/<id>/` | revokes the token |

No database migration is needed: the service account is a user with `is_bot` and `bot_type = SERVICE_ACCOUNT`, its tokens are ordinary API tokens of type Bot bound to the workspace.

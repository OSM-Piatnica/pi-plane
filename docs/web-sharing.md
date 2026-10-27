<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Sharing a project on the web

A project can be shared on the web. This creates a link that **anyone on the internet** can open, with no account, to read the project. It is served by the `space` app under `/spaces/issues/<anchor>`. Earlier versions called this "Publish project".

Web sharing is not a visibility level. Who can find and join a project inside the workspace is set by its network:

| Network | Meaning                                                               |
| ------- | --------------------------------------------------------------------- |
| Secret  | Hidden from everyone who is not a member                              |
| Private | Listed for everyone in the workspace; access needs approval or invite |
| Open    | Any workspace member, except Guests, can join                         |

Any of the three can also be shared on the web. "Open" does not mean "visible to the internet".

## Turning it on

Open the project's menu in the sidebar and choose **Share on the web**. Pick the layouts to show (list, board, calendar, timeline, spreadsheet) and whether viewers may comment, react and vote, then **Turn on web sharing**. A confirmation lists what becomes visible; sharing starts only after you confirm it. Changing the settings of an already shared project does not ask again.

**Stop sharing** switches the link off. A link whose sharing was stopped shows the not-found page.

## What viewers can see

- every work item that is not archived, with its description, state, priority, dates and labels;
- the names and avatars of the project's members;
- comments, reactions and votes, with the names of the people behind them, when you allow them. Of the comments, only those set to **Visible on the web** are shown; the default for a comment is **Internal**, which stays inside the project.

Viewers cannot edit anything. Commenting, reacting and voting need a sign-in.

The link keeps working until sharing is stopped, so share only a project that holds nothing confidential.

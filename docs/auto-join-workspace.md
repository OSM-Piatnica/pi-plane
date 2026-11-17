<!--
Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
SPDX-License-Identifier: AGPL-3.0-only
See the LICENSE file for details.
-->

# Joining the company workspace at sign-in

Without an invite, somebody who signs up from the bare address of the instance has no workspace, and the onboarding asks them to create one. They end up alone in a workspace of their own: they do not show up in the members of the company workspace, cannot be put in its groups and do not see its projects.

An instance admin can pick one workspace that people of the company's email domains join by themselves. Open **God Mode → Workspaces → Add people to a workspace when they sign in**, choose the workspace, the role and the domains, and save.

## What happens

Every time somebody signs in to the app (email and password, one-time code, GitHub, GitLab, Gitea or single sign-on), after their invites have been handled, they become a member of the workspace when all of this holds:

- their email address is of one of the domains (`anna@example.com` for `example.com`; `anna@mail.example.com` is not);
- they have never been a member of the workspace: people an admin removed or suspended are not added again;
- the account is active and is not a bot.

They get the chosen role, Member or Guest. An invite to the workspace decides the role instead (and is used up), so an admin can still invite somebody as an Admin. They land in the workspace after signing in, and the onboarding no longer asks them to create or join a workspace. Creating more workspaces stays as it is (see **Prevent anyone else from creating a workspace** on the same page).

Signing in on the public site that shows projects shared on the web does not join anybody.

**The address is not verified.** Signing up with a password does not prove that the address belongs to the person, so anybody who can reach the instance can sign up with an address of the domains and join. Use this on an instance that only the company can reach, or only allow sign-up with a one-time code or single sign-on.

## Settings

| Key | Meaning | Default |
| --- | --- | --- |
| `AUTO_JOIN_WORKSPACE_ID` | The workspace (its UUID, so renaming it changes nothing). Empty turns joining off. | empty |
| `AUTO_JOIN_WORKSPACE_ROLE` | `15` (Member) or `5` (Guest). | `15` |
| `AUTO_JOIN_EMAIL_DOMAINS` | Domains separated by commas, for example `example.com, example.org`. Empty turns joining off. | empty |

They are seeded from environment variables of the same name and can be changed by an instance admin only. The API refuses a workspace that does not exist, any other role and entries that are not domain names. When the workspace is deleted, joining stops.

## People who already have an account

They join at their next sign-in. To add them at once, run in the API container:

```
python manage.py join_default_workspace --dry-run   # lists who would join
python manage.py join_default_workspace             # adds them
```

The command follows the same rules as signing in. People who created a workspace of their own keep it; they are members of both afterwards.

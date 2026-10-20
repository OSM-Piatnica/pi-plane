# Branding follow-ups

The Pi-Plane logo replaced the Plane logo in the apps, icons, spinners and README. Two places still show the upstream Plane branding.

## 1. Email templates still load the upstream-hosted logo

Email clients can't use embedded or repo-relative images reliably, so the logo must be a public HTTPS URL. These 11 templates under `apps/api/templates/emails/` point at `https://media.docs.plane.so/logo/new-logo-dark.png`:

- `auth/forgot_password.html`
- `auth/magic_signin.html`
- `exports/analytics.html`
- `invitations/workspace_invitation.html`
- `notifications/issue-updates.html`
- `notifications/project_addition.html`
- `notifications/webhook-deactivate.html`
- `notifications/work-item-due-reminder.html`
- `user/email_updated.html`
- `user/user_activation.html`
- `user/user_deactivation.html`

**To do:**

1. Host a Pi-Plane logo (PNG, about 2x the displayed size, readable on light email backgrounds) at a stable public URL.
2. Replace the `src` in every template above. Prefer a single setting or template variable over 11 hard-coded copies.
3. Check the same URL in the repo README if any other upstream-hosted image remains.

## 2. API static logo

`apps/api/plane/static/logos/Logo.png` is still the Plane logo. The sibling social icons (`github_32px.png` and others) are generic and can stay.

**To do:** replace `Logo.png` with a Pi-Plane PNG, keeping the same filename and a similar size, or make the final location match item 1 if the emails end up using it.

## Also worth doing

The mark was extracted as a raster image from the supplied banner, so it looks soft at large sizes. If a vector (SVG) or high-resolution original exists, regenerate the icons and spinners and swap the embedded mark in `packages/blocks/src/icons/brand/pi-plane-mark.ts`.

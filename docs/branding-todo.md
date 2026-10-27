# Branding follow-ups

The Pi-Plane logo replaced the Plane logo in the apps, icons, spinners and README. Two places still show the upstream Plane branding.

## 1. Email templates still load the upstream-hosted logo

Email clients can't use embedded or repo-relative images reliably, so the logo must be a public HTTPS URL. 14 templates under `apps/api/templates/emails/` load their logo from `media.docs.plane.so`, in two variants.

`https://media.docs.plane.so/logo/new-logo-dark.png` (for light backgrounds):

- `auth/forgot_password.html`
- `auth/one_time_code_signin.html`
- `exports/analytics.html`
- `invitations/workspace_invitation.html`
- `notifications/project_access_request.html`
- `notifications/project_access_request_decision.html`
- `notifications/project_addition.html`

`https://media.docs.plane.so/logo/new-logo-white.png` (for dark headers):

- `notifications/issue-digest.html`
- `notifications/issue-updates.html`
- `notifications/webhook-deactivate.html`
- `notifications/work-item-due-reminder.html`
- `user/email_updated.html`
- `user/user_activation.html`
- `user/user_deactivation.html`

**To do:**

1. Host a Pi-Plane logo in both variants (PNG, about 2x the displayed size, readable on the light and the dark background respectively) at a stable public URL.
2. Replace the `src` in every template above. Prefer a single setting or template variable over 14 hard-coded copies.
3. The templates also load upstream-hosted icons (`https://plane-marketing.s3.ap-south-1.amazonaws.com/plane-assets/emails/*.png`: state, priority, label and arrow icons) and third-party social icons from `creative-assets.mailinblue.com`; decide whether those stay. The repo README has no upstream-hosted image left.

## 2. API static logo

`apps/api/plane/static/logos/Logo.png` is still the Plane logo. The sibling social icons (`github_32px.png` and others) are generic and can stay.

Nothing in the repo references this file at the moment.

**To do:** replace `Logo.png` with a Pi-Plane PNG, keeping the same filename and a similar size, or delete it if the emails use the hosted logos from item 1.

## Also worth doing

The mark was extracted as a raster image from the supplied banner, so it looks soft at large sizes. If a vector (SVG) or high-resolution original exists, regenerate the icons and spinners and swap the embedded mark in `packages/blocks/src/icons/brand/pi-plane-mark.ts`.

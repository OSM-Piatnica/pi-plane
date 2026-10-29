# Branding follow-ups

The Pi-Plane logo replaced the Plane logo in the apps, icons, spinners and README. Two places still show the upstream Plane branding.

## 1. Email logo

Done in part. The emails no longer load the logo from `media.docs.plane.so`: every template calls `{% email_logo %}`, which shows the name "Pi-Plane" in type by default. An instance can show an image instead by setting `EMAIL_LOGO_URL` (a PNG for light backgrounds) and `EMAIL_LOGO_URL_ON_DARK` (a PNG for the dark header of the digest-style emails), both https addresses; see `apps/api/.env.example`. The default could become an image once a Pi-Plane logo is hosted at a stable public address and set as the default of those two settings.

The templates still load third-party and upstream-hosted pictures:

- the state, priority, due-date, label and arrow icons of the work item update emails (`https://plane-marketing.s3.ap-south-1.amazonaws.com/plane-assets/emails/*.png`);
- the GitHub icon of the footer of five emails (`creative-assets.mailinblue.com`).

Both would have to be hosted by us (or inlined) to remove the last request to somebody else's servers when an email is opened.

## 2. API static logo

`apps/api/plane/static/logos/Logo.png` is still the Plane logo. The sibling social icons (`github_32px.png` and others) are generic and can stay.

Nothing in the repo references this file at the moment.

**To do:** replace `Logo.png` with a Pi-Plane PNG, keeping the same filename and a similar size, or delete it if the emails use the hosted logos from item 1.

## Also worth doing

The mark was extracted as a raster image from the supplied banner, so it looks soft at large sizes. If a vector (SVG) or high-resolution original exists, regenerate the icons and spinners and swap the embedded mark in `packages/blocks/src/icons/brand/pi-plane-mark.ts`.

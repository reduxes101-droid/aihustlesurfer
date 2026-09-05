# AIHustleSurfer

Static editorial site. Plain HTML, CSS and JavaScript. No framework, no npm, no build step on deploy. Vercel serves the committed files as they are.

## Editing content

Everything editable lives in `content/`. After any change, regenerate the pages:

```bash
python build.py
```

Then commit the generated HTML together with the content change.

| What | Where |
|------|-------|
| Site name, tagline, contact email, newsletter form endpoint, categories | `content/site.json` |
| Every outbound tool link (the single place to swap in affiliate URLs) | `content/links.json` |
| One review per tool: score, pricing, pros and cons, body sections | `content/tools/<slug>.json` |
| Video pages: title, YouTube ID, duration, tools mentioned, notes | `content/videos.json` |
| Guides and roundups: HTML fragment with a JSON meta block at the top | `content/guides/<slug>.html` |

### Swapping in affiliate links

Edit the `url` for the tool in `content/links.json`, set `affiliate` to `true`, run `build.py`. This updates `vercel.json` (the redirect Vercel actually uses) and the fallback page in `go/<slug>/` (used on any other host). Every link on the site already points to `/go/<slug>/`, so nothing else changes.

### Adding a video

Add an object to `content/videos.json`. Use the 11-character YouTube ID, not the URL. Until an ID is set, the video page shows a "not published yet" notice instead of a broken player.

### Adding a tool

Copy an existing file in `content/tools/`, change every field, add a matching entry to `content/links.json`, run `build.py`. Category keys must match those in `site.json`. Body paragraphs may contain inline HTML links to other reviews.

### Roundups

A guide with `"type": "roundup"` in its meta block. Insert `<!--tool:slug-->` where you want a tool card with score, summary and links.

### Newsletter

Set `newsletterAction` in `content/site.json` to your form endpoint (MailerLite, Buttondown, ConvertKit, etc.). The form posts an `email` field. Leave it empty and the form shows a "not connected" message instead of failing.

## Local preview

```bash
python -m http.server 8080
```

Open http://localhost:8080/. The `/go/` fallback pages work locally; the Vercel redirects do not.

## Deploy

Push to GitHub, import the repository in Vercel, leave the build command empty and the output directory as the root. `vercel.json` sets clean URLs, trailing slashes, the `/go/` redirects and cache headers.

## Design

- Fonts: Fraunces (headlines), IBM Plex Sans (body), IBM Plex Mono (labels and scores), loaded from Google Fonts.
- Palette: navy `#0B0F1F`, purple `#7C6FEB`, cream `#F6F3EE`, ink `#16162A`. Tints are derived in `assets/css/site.css`.
- Home and index pages are dark. Reading pages are light.
- Motion is limited to scroll reveals, a pointer-tracking highlight on cards and a reading progress bar. All of it respects `prefers-reduced-motion`.

## Source assets

`logo1.png` is the original logo. `assets/img/` holds the trimmed, resized copies the site uses.

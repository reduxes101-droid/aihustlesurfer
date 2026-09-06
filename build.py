#!/usr/bin/env python3
"""
AIHustleSurfer static generator. Standard library only.

    python build.py

Reads everything under content/ and writes plain HTML into the project root.
Vercel serves the output as-is; there is no build step on deploy. Commit the
generated files together with the content that produced them.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
esc = html.escape

# --------------------------------------------------------------------------
# Load content
# --------------------------------------------------------------------------
SITE = json.loads((CONTENT / "site.json").read_text("utf-8"))
LINKS = {k: v for k, v in json.loads((CONTENT / "links.json").read_text("utf-8")).items() if not k.startswith("_")}
CATS = SITE["categories"]
USE_CASES = SITE["useCases"]
KDP = SITE.get("kdpTools")  # the KDP calculators, a separate Next.js app mounted at /kdp/
for _u in USE_CASES:
    assert _u["category"] in CATS, f"useCases: unknown category {_u['category']!r}"

TOOLS = sorted(
    (json.loads(p.read_text("utf-8")) for p in sorted((CONTENT / "tools").glob("*.json"))),
    key=lambda t: t["date"], reverse=True,
)
TOOL_BY_SLUG = {t["slug"]: t for t in TOOLS}
VIDEOS = sorted(json.loads((CONTENT / "videos.json").read_text("utf-8")), key=lambda v: v["date"], reverse=True)
SHOW_VIDEOS = bool(SITE.get("videos", True))


def load_guides() -> list[dict]:
    out = []
    for p in sorted((CONTENT / "guides").glob("*.html")):
        raw = p.read_text("utf-8")
        m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->", raw, re.S)
        if not m:
            raise SystemExit(f"{p.name}: missing <!--meta {{...}} --> block")
        meta = json.loads(m.group(1))
        meta["body"] = raw[m.end():].strip()
        meta.setdefault("slug", p.stem)
        meta.setdefault("type", "guide")
        meta.setdefault("kicker", "Roundup" if meta["type"] == "roundup" else "Guide")
        meta["tools"] = re.findall(r"<!--tool:([a-z0-9-]+)-->", meta["body"])
        out.append(meta)
    return sorted(out, key=lambda g: g["date"], reverse=True)


GUIDES = load_guides()
GUIDE_BY_SLUG = {g["slug"]: g for g in GUIDES}

for slug in TOOL_BY_SLUG:
    if slug not in LINKS:
        raise SystemExit(f"links.json has no entry for tool '{slug}'")

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
ICON = {
    "menu": '<svg class="icon-menu" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "close": '<svg class="icon-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "external": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    "x": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg>',
    "play": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.5v15l12-7.5z"/></svg>',
    "info": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    "chev": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
}

FONTS = ("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400..600"
         "&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap")


def fmt_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def score_label(score: float) -> str:
    for floor, label in SITE["scoreLabels"]:
        if score >= floor:
            return label
    return SITE["scoreLabels"][-1][1]


def read_time(text: str) -> int:
    words = len(re.sub(r"<[^>]+>", " ", text).split())
    return max(2, round(words / 220))


def tool_text(t: dict) -> str:
    return " ".join(p for s in t["sections"] for p in s["p"]) + " ".join(t["pros"] + t["cons"])


def go_href(slug: str) -> str:
    return f"/go/{slug}/"


def go_link(slug: str, label: str, cls: str = "btn btn--primary") -> str:
    return (f'<a class="{cls}" href="{go_href(slug)}" rel="sponsored nofollow noopener" target="_blank">'
            f'{esc(label)}{ICON["external"]}<span class="visually-hidden"> (opens in a new tab)</span></a>')


def score_badge(score: float) -> str:
    return f'<span class="score-badge" aria-label="Score {score:.1f} out of 10"><b>{score:.1f}</b><small>/10</small></span>'


def latest_update() -> str:
    dates = [t["date"] for t in TOOLS] + [g["date"] for g in GUIDES] + ([v["date"] for v in VIDEOS] if SHOW_VIDEOS else [])
    return fmt_date(max(dates))



def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")
    return s[:60] or "section"


def label_tables(html_body: str) -> str:
    """Add class=stack and data-label attributes so tables can stack on phones."""
    def fix(m: re.Match) -> str:
        table = m.group(0)
        heads = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)]
        if not heads:
            return table
        def row(rm: re.Match) -> str:
            cells = re.findall(r"<td([^>]*)>(.*?)</td>", rm.group(0), re.S)
            out = "<tr>"
            for i, (attrs, inner) in enumerate(cells):
                lab = esc(heads[i]) if i < len(heads) else ""
                out += f'<td data-label="{lab}"{attrs}>{inner}</td>'
            return out + "</tr>"
        body = re.sub(r"<tr>\s*<td.*?</tr>", row, table, flags=re.S)
        return body.replace("<table>", '<table class="stack">', 1)
    return re.sub(r"<table>.*?</table>", fix, html_body, flags=re.S)


def rail(inner: str) -> str:
    return f'<div class="rail" data-rail aria-label="Reading position">{inner}</div>'


SHOTS = ROOT / "assets" / "img" / "screenshots"
try:
    SHOT_DATES = json.loads((SHOTS / "captures.json").read_text("utf-8"))
except FileNotFoundError:
    SHOT_DATES = {}


def screenshot_for(t: dict):
    """Return (url, date or None) if a vendor-page capture exists for this tool, else None."""
    f = SHOTS / f"{t['slug']}.webp"
    if not f.exists():
        return None
    return f"/assets/img/screenshots/{t['slug']}.webp", SHOT_DATES.get(t["slug"])


def screenshot_figure(t: dict) -> str:
    shot = screenshot_for(t)
    if not shot:
        return ""
    url, date = shot
    when = f", captured {fmt_date(date)}" if date else ""
    alt = f"Screenshot of {t['name']}'s public website{when}. It shows the vendor's marketing page, not the product in use."
    cap = (f"{esc(t['name'])}'s own website{esc(when)}. This is the vendor's public page, reproduced for identification; "
           "it is not a view of the product in use and it was not produced by us.")
    return (f'<figure class="shot"><img src="{url}" width="1280" height="720" alt="{esc(alt)}" loading="lazy" decoding="async">'
            f'<figcaption>{cap}</figcaption></figure>')

# --------------------------------------------------------------------------
# Chrome: head, header, footer
# --------------------------------------------------------------------------
def header(current: str) -> str:
    items = [("/tools/", "tools", "Tools")]
    if SHOW_VIDEOS:
        items.append(("/videos/", "videos", "Videos"))
    items.append(("/guides/", "guides", "Guides"))
    if KDP:
        items.append((KDP["base"], "kdp", "KDP tools"))   # the calculators, distinct from /tools/ reviews
    items.append(("/about/", "about", "About"))
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if key == current else ""}>{label}</a>' for href, key, label in items
    )
    return f'''
<header class="site-header">
  <div class="container site-header__inner">
    <a class="brand" href="/" aria-label="{esc(SITE["name"])} home">
      <picture>
        <source srcset="/assets/img/logo-header.webp" type="image/webp">
        <img class="brand__logo" src="/assets/img/logo-header.png" width="186" height="128" alt="" decoding="async">
      </picture>
      <span class="brand__name">AIHustle<span>Surfer</span></span>
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">{ICON["menu"]}{ICON["close"]}<span>Menu</span></button>
    <nav id="site-nav" class="site-nav" aria-label="Primary">{nav}<span class="site-nav__meta">{esc(SITE["tagline"])}</span></nav>
  </div>
</header>'''


def disclosure_bar() -> str:
    return f'''
<div class="disclosure-bar" role="note" aria-label="Affiliate disclosure">
  <div class="container disclosure-bar__inner">{ICON["info"]}
    <p><span class="disclosure-bar__long">This page has affiliate links. If you buy through one, we may earn a commission at no extra cost to you. It does not affect scores or what we recommend.</span><span class="disclosure-bar__short">Contains affiliate links.</span> <a href="/disclosure/">How we make money</a></p>
  </div>
</div>'''


def newsletter() -> str:
    action = SITE.get("newsletterAction") or "#"
    return f'''
<section class="newsletter reveal" aria-labelledby="nl-title">
  <h2 id="nl-title">New reviews, by email</h2>
  <p>One email when we publish something worth your time. No sequences, no upsells.</p>
  <form data-newsletter action="{esc(action)}" method="post">
    <label><span class="visually-hidden">Email address</span><input type="email" name="email" autocomplete="email" inputmode="email" required placeholder="you@example.com"></label>
    <div class="hp" aria-hidden="true"><label>Leave this field empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
    <button class="btn btn--primary" type="submit">Subscribe</button>
  </form>
  <small>Unsubscribe with one click. We do not sell or share the list.</small>
  <p class="newsletter__msg" role="status" hidden></p>
</section>'''


def footer() -> str:
    year = dt.date.today().year
    return f'''
<footer class="site-footer">
  <div class="container">
    <div class="site-footer__grid">
      <div>
        <a class="brand" href="/"><picture><source srcset="/assets/img/logo-header.webp" type="image/webp"><img class="brand__logo" src="/assets/img/logo-header.png" width="186" height="128" alt="" loading="lazy" decoding="async"></picture><span class="brand__name">AIHustle<span>Surfer</span></span></a>
        <p class="site-footer__about">{esc(SITE["description"])}</p>
      </div>
      <div>
        <h2>Sections</h2>
        <ul><li><a href="/tools/">Tool reviews</a></li>{'<li><a href="/videos/">Videos</a></li>' if SHOW_VIDEOS else ''}<li><a href="/guides/">Guides</a></li><li><a href="/about/">About &amp; how we work</a></li></ul>
      </div>
      <div>
        <h2>Site</h2>
        <ul><li><a href="/disclosure/">Affiliate disclosure</a></li><li><a href="/about/#corrections">Corrections</a></li><li><a href="mailto:{esc(SITE["contactEmail"])}">{esc(SITE["contactEmail"])}</a></li></ul>
      </div>
    </div>
    <p class="site-footer__disclosure"><strong>Disclosure.</strong> {esc(SITE["name"])} is reader-supported. Some links to tools are affiliate links: if you sign up or buy through them, we may earn a commission at no extra cost to you. Affiliate status never influences a score, a ranking, or whether a tool gets reviewed at all. <a href="/disclosure/">Read the full disclosure</a>.</p>
    <div class="site-footer__legal"><span>&copy; {year} {esc(SITE["name"])}</span><span>Independent. Not affiliated with any tool maker.</span><span>Prices checked at time of publishing and may change.</span></div>
  </div>
</footer>'''



# --------------------------------------------------------------------------
# Structured data (schema.org JSON-LD)
# --------------------------------------------------------------------------
BASE = SITE["url"].rstrip("/")
ORG_ID = f"{BASE}/#organization"
SITE_ID = f"{BASE}/#website"
OG_IMAGE = f"{BASE}/assets/img/og-image.png"
PRICE_RE = re.compile(r"\$\s?([0-9]+(?:\.[0-9]{1,2})?)")


def ld(*nodes: dict) -> str:
    graph = {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}
    return '<script type="application/ld+json">' + json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "</script>\n"


def org_node() -> dict:
    return {"@type": "Organization", "@id": ORG_ID, "name": SITE["name"], "url": BASE + "/",
            "description": SITE["description"], "email": SITE["contactEmail"],
            "logo": {"@type": "ImageObject", "url": OG_IMAGE, "width": 1200, "height": 630}}


def website_node() -> dict:
    return {"@type": "WebSite", "@id": SITE_ID, "url": BASE + "/", "name": SITE["name"],
            "inLanguage": "en", "publisher": {"@id": ORG_ID}}


def breadcrumbs(*crumbs) -> dict:
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": BASE + path}
        for i, (name, path) in enumerate(crumbs, 1)]}


def offers_for(t: dict) -> list:
    out = []
    for p in t.get("pricing", []):
        raw = str(p.get("price", ""))
        m = PRICE_RE.search(raw)
        if m:
            out.append({"@type": "Offer", "name": p["plan"], "price": float(m.group(1)), "priceCurrency": "USD"})
        elif re.search(r"free", raw, re.I):
            out.append({"@type": "Offer", "name": p["plan"], "price": 0, "priceCurrency": "USD"})
    return out


def review_node(t: dict) -> dict:
    canonical = f"{BASE}/tools/{t['slug']}/"
    product = {"@type": "SoftwareApplication", "name": t["name"],
               "applicationCategory": CATS[t["category"]], "operatingSystem": "Web",
               "description": t["tagline"]}
    offers = offers_for(t)
    if offers:
        product["offers"] = offers
    shot = screenshot_for(t)
    if shot:
        product["image"] = BASE + shot[0]
    return {"@type": "Review", "@id": canonical + "#review", "url": canonical,
            "name": f"{t['name']} review", "reviewBody": t["dek"], "datePublished": t["date"],
            "itemReviewed": product,
            "reviewRating": {"@type": "Rating", "ratingValue": t["score"], "bestRating": 10, "worstRating": 0},
            **({"image": BASE + shot[0]} if shot else {}),
            "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}}


def article_node(g: dict) -> dict:
    canonical = f"{BASE}/guides/{g['slug']}/"
    return {"@type": "Article", "@id": canonical + "#article", "headline": g["title"],
            "description": g["dek"], "datePublished": g["date"], "dateModified": g["date"],
            "mainEntityOfPage": canonical, "image": OG_IMAGE, "inLanguage": "en",
            "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}}


def tool_list_node() -> dict:
    return {"@type": "ItemList", "name": "AI tool reviews", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": t["name"], "url": f"{BASE}/tools/{t['slug']}/"}
        for i, t in enumerate(TOOLS, 1)]}


def layout(*, title: str, description: str, path: str, body: str, theme: str, current: str = "",
           affiliate: bool = False, article: bool = False, og_type: str = "website", extra_head: str = "",
           jsonld: str = "") -> str:
    canonical = SITE["url"].rstrip("/") + path
    full_title = f"{title} | {SITE['name']}" if path != "/" else f"{SITE['name']} — {title}"
    progress = '<div class="progress" aria-hidden="true"></div>' if article else ""
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(SITE["name"])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{SITE["url"].rstrip("/")}/assets/img/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(SITE["name"])} logo: a purple wave with an upward arrow">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE["url"].rstrip("/")}/assets/img/og-image.png">
<meta name="theme-color" content="#0B0F1F">
<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="icon" href="/assets/img/favicon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="/assets/img/favicon-192.png" type="image/png" sizes="192x192">
<link rel="icon" href="/assets/img/favicon-512.png" type="image/png" sizes="512x512">
<link rel="apple-touch-icon" href="/assets/img/favicon-180.png" sizes="180x180">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="/assets/css/site.css">
{jsonld}{extra_head}<script>document.documentElement.classList.add('js')</script>
</head>
<body class="theme-{theme}">
<a class="skip-link" href="#main">Skip to content</a>
{progress}{header(current)}{disclosure_bar() if affiliate else ""}
<main id="main" tabindex="-1">{body}</main>
{footer()}
<script src="/assets/js/site.js" defer></script>
</body>
</html>
'''


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------
def tool_card(t: dict) -> str:
    search = " ".join([t["name"], t["tagline"], t["bestFor"], CATS[t["category"]]]).lower()
    return f'''
<article class="card tool-card" data-category="{t["category"]}" data-name="{esc(t["name"])}" data-score="{t["score"]}" data-date="{t["date"]}" data-search="{esc(search)}">
  <div class="card__top"><span class="pill">{esc(CATS[t["category"]])}</span>{score_badge(t["score"])}</div>
  <h3><a href="/tools/{t["slug"]}/">{esc(t["name"])}</a></h3>
  <p class="verdict-line">{esc(t["tagline"])}</p>
  <div class="card__meta"><span>{esc(t["priceFrom"])}</span><span>Best for: {esc(t["bestFor"])}</span></div>
</article>'''


def video_thumb(v: dict, big: bool = False) -> str:
    vid = v["youtubeId"]
    if vid.startswith("YOUTUBE_ID"):
        img = '<span class="thumb-placeholder">Video coming</span>'
    else:
        img = f'<img src="https://i.ytimg.com/vi/{esc(vid)}/{"hqdefault" if big else "mqdefault"}.jpg" alt="" loading="lazy" decoding="async" width="320" height="180">'
    return f'<span class="video-card__thumb">{img}<span class="video-card__play">{ICON["play"]}</span><span class="video-card__len">{esc(v["duration"])}</span></span>'


def video_card(v: dict) -> str:
    return f'''
<a class="video-card" href="/videos/{v["slug"]}/">
  {video_thumb(v)}
  <h3>{esc(v["title"])}</h3>
  <p>{esc(v["dek"])}</p>
</a>'''


def story_row(kicker: str, href: str, title: str, dek: str, meta: str) -> str:
    return f'''
<article class="story-row">
  <span class="kicker">{esc(kicker)}</span>
  <h3><a href="{href}">{esc(title)}</a></h3>
  <p>{esc(dek)}</p>
  <span class="byline">{meta}</span>
</article>'''


def mentioned_item(t: dict) -> str:
    return f'''
<div class="mentioned__item">
  {score_badge(t["score"])}
  <div>
    <h3><a href="/tools/{t["slug"]}/">{esc(t["name"])}</a></h3>
    <p>{esc(t["tagline"])}</p>
  </div>
  <div class="mentioned__actions">
    <a class="btn btn--ghost" href="/tools/{t["slug"]}/">Read the review</a>
    {go_link(t["slug"], f"Visit {t['name']}")}
  </div>
</div>'''


def byline(parts: list[str]) -> str:
    return '<p class="byline">' + " <span aria-hidden=\"true\">·</span> ".join(parts) + "</p>"


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def kdp_card(item: dict) -> str:
    href = f"{KDP['base']}{item['slug']}/"
    return f'''
    <article class="card">
      <span class="pill">Free tool</span>
      <h3><a href="{href}">{esc(item["name"])}</a></h3>
      <p>{esc(item["description"])}</p>
    </article>'''


def kdp_section() -> str:
    if not KDP:
        return ""
    cards = "".join(kdp_card(i) for i in KDP["items"])
    return f'''
<section id="kdp-tools" class="section section--tight container" aria-labelledby="kdp-tools-title">
  <div class="section-head"><h2 id="kdp-tools-title">{esc(KDP["title"])}</h2><a href="{KDP["base"]}">All KDP tools</a></div>
  <p class="dek">{esc(KDP["intro"])}</p>
  <div class="grid grid--pairs reveal-group">{cards}</div>
</section>
'''


def usecase_card(u: dict) -> str:
    """One use-case card. The count comes from the reviews actually on disk, and a category
    with a single review names it rather than implying a shelf of options."""
    tools = sorted((t for t in TOOLS if t["category"] == u["category"]), key=lambda t: -t["score"])
    n = len(tools)
    href = f"/tools/?category={u['category']}"
    if n == 0:
        count = "No reviews yet"
    elif n == 1:
        count = f"1 review · {esc(tools[0]['name'])}"
        href = f"/tools/{tools[0]['slug']}/"   # one review: go straight to it, not to a one-card filter
    else:
        count = f"{n} reviews"
    return f'''
<article class="card usecase-card">
  <h3><a href="{href}">{esc(u["title"])} {ICON["arrow"]}</a></h3>
  <p>{esc(u["description"])}</p>
  <div class="card__meta"><span>{count}</span><span>{esc(CATS[u["category"]])}</span></div>
</article>'''


def page_home() -> str:
    lead = next((t for t in TOOLS if t.get("featured")), TOOLS[0])
    others = [t for t in TOOLS if t["slug"] != lead["slug"]]
    guide = next((g for g in GUIDES if g.get("featured")), GUIDES[0]) if GUIDES else None
    usecases = "".join(usecase_card(u) for u in USE_CASES)
    trust = "".join(f'<li>{ICON["check"]}<b>{esc(label)}</b></li>' for label in ("Honest reviews", "Independent", "Built for earners"))
    guide_html = f'''
    <article class="card feature feature--guide">
      <span class="kicker">Featured guide</span>
      <h2><a href="/guides/{guide["slug"]}/">{esc(guide["title"])}</a></h2>
      <p class="dek">{esc(guide["dek"])}</p>
      {byline([esc(fmt_date(guide["date"])), f"{read_time(guide['body'])} min read"])}
    </article>''' if guide else ""
    latest = "".join(tool_card(t) for t in others[:6])
    roundups = [g for g in GUIDES if g["type"] == "roundup"][:2]
    roundup_html = "".join(
        f'<article class="card"><span class="pill">Roundup</span><h3><a href="/guides/{g["slug"]}/">{esc(g["title"])}</a></h3><p>{esc(g["dek"])}</p><div class="card__meta"><span>{len(g["tools"])} tools compared</span><span>{esc(fmt_date(g["date"]))}</span></div></article>'
        for g in roundups
    )
    guides_html = "".join(
        story_row(g["kicker"], f"/guides/{g['slug']}/", g["title"], g["dek"], f"{esc(fmt_date(g['date']))} · {read_time(g['body'])} min read")
        for g in [g for g in GUIDES if g["type"] != "roundup"][:4]
    )
    videos_html = "".join(video_card(v) for v in VIDEOS[:3]) if SHOW_VIDEOS else ""
    videos_section = f'''
<section class="section section--tight container">
  <div class="section-head"><h2>Videos</h2><a href="/videos/">All videos</a></div>
  <div class="grid grid--3 reveal-group">{videos_html}</div>
</section>
''' if SHOW_VIDEOS else ""

    body = f'''
<div class="aurora">
  <div class="hero-art" aria-hidden="true">
    <picture>
      <source media="(min-width: 60rem)" srcset="/assets/img/hero-beach-1200.webp 1200w, /assets/img/hero-beach-1672.webp 1672w" sizes="100vw" type="image/webp">
      <source media="(min-width: 60rem)" srcset="/assets/img/hero-beach-1672.jpg" type="image/jpeg">
      <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="" width="1672" height="941" fetchpriority="high" decoding="async">
    </picture>
  </div>
  <div class="aurora__bg" aria-hidden="true"><div class="aurora__layer"></div></div>
<section class="hero container">
  <div class="hero-intro">
    <h1>AI tools that earn their subscription.</h1>
    <p class="dek">Independent reviews for freelancers, creators and small businesses. See what each tool actually does, what it costs, and whether it can make or save you money.</p>
    <div class="hero-intro__actions">
      <a class="btn btn--primary" href="#use-cases">Find the right tool {ICON["arrow"]}</a>
      <a class="btn btn--ghost" href="/tools/">See all reviews</a>
    </div>
    <ul class="trust" aria-label="What to expect">{trust}<li class="trust__updated">Updated {esc(latest_update())}</li></ul>
  </div>
</section>
</div>

<section id="use-cases" class="section section--tight container">
  <div class="section-head"><h2>What do you want to do?</h2><a href="/tools/">Browse every category</a></div>
  <div class="grid grid--3 reveal-group">{usecases}</div>
</section>

<section class="section section--tight container">
  <div class="feature-grid reveal-group">
    <article class="card feature feature--review">
      <span class="kicker">Latest review · {esc(CATS[lead["category"]])}</span>
      <h2><a href="/tools/{lead["slug"]}/">{esc(lead["headline"])}</a></h2>
      <p class="dek">{esc(lead["dek"])}</p>
      <span class="feature__score score"><span class="score__num">{lead["score"]:.1f}</span><span class="score__den">/10 · {esc(score_label(lead["score"]))}</span></span>
      {byline([f"<b>{esc(SITE['byline'])}</b>", esc(fmt_date(lead["date"])), f"{read_time(tool_text(lead))} min read"])}
    </article>{guide_html}
  </div>
</section>

<section class="section section--tight container">
  <div class="section-head"><h2>Latest reviews</h2><a href="/tools/">All {len(TOOLS)} tools reviewed</a></div>
  <div class="grid grid--3 reveal-group">{latest}</div>
</section>

{kdp_section()}
<section class="section section--tight container">
  <div class="section-head"><h2>Roundups</h2><a href="/guides/">All guides</a></div>
  <div class="grid grid--2 reveal-group">{roundup_html}</div>
</section>

{videos_section}
<section class="section section--tight container">
  <div class="section-head"><h2>Guides</h2><a href="/guides/">All guides</a></div>
  <div class="story-list reveal">{guides_html}</div>
</section>

<section class="section container">{newsletter()}</section>
'''
    preload = '<link rel="preload" as="image" href="/assets/img/hero-beach-1672.webp" imagesrcset="/assets/img/hero-beach-1200.webp 1200w, /assets/img/hero-beach-1672.webp 1672w" imagesizes="100vw" type="image/webp" media="(min-width: 60rem)" fetchpriority="high">\n'
    # Impact.com site verification: home page only, quotes and attribute order kept exactly as issued.
    preload += "<meta name='impact-site-verification' value='f74b2363-f21e-4600-9143-2260b178ba02'>" + chr(10)
    return layout(title=SITE["tagline"], description=SITE["description"], path="/", body=body, theme="dark", current="home", extra_head=preload,
                  jsonld=ld(org_node(), website_node()))

def page_tools_index() -> str:
    chips = '<button class="chip" type="button" data-category="all" aria-pressed="true">All</button>' + "".join(
        f'<button class="chip" type="button" data-category="{k}" aria-pressed="false">{esc(v)}</button>'
        for k, v in CATS.items() if any(t["category"] == k for t in TOOLS)
    )
    cards = "".join(tool_card(t) for t in sorted(TOOLS, key=lambda t: -t["score"]))
    body = f'''
<div class="aurora">
  <div class="aurora__bg" aria-hidden="true"><div class="aurora__layer"></div></div>
  <div class="container"><div class="page-head">
    <span class="kicker">Directory</span>
    <h1>AI tools, reviewed</h1>
    <p class="dek">Each tool here is assessed from its documentation, current pricing and what users consistently report, then scored on one question: is it worth the money for someone earning with it? Sort, filter, then read the review before you pay for anything.</p>
  </div></div>
</div>
<div class="container" data-tools-directory>
  <div class="toolbar">
    <div class="toolbar__row toolbar__row--between">
      <div class="field field--search">{ICON["search"]}<label class="visually-hidden" for="tool-search">Search tools</label><input id="tool-search" type="search" placeholder="Search by name or use case" autocomplete="off"></div>
      <div class="field field--select"><label class="visually-hidden" for="tool-sort">Sort</label><select id="tool-sort"><option value="score">Highest score</option><option value="date">Newest review</option><option value="name">Name A–Z</option></select>{ICON["chev"]}</div>
    </div>
    <div class="toolbar__row"><div class="chips" role="group" aria-label="Filter by category">{chips}</div></div>
    <p class="results-count" data-results-count aria-live="polite">{len(TOOLS)} tools</p>
  </div>
  <div class="grid grid--3 reveal-group" data-tools-grid>{cards}</div>
  <p class="empty-state" data-empty hidden>Nothing matches that. Try a broader search or clear the category.</p>
  <section class="section">{newsletter()}</section>
</div>'''
    return layout(title="AI tool reviews and ratings", description="A filterable directory of AI tools with honest scores, real pricing, and the pros and cons of each one.",
                  path="/tools/", body=body, theme="dark", current="tools",
                  jsonld=ld(breadcrumbs(("Home", "/"), ("Tools", "/tools/")), tool_list_node()))


def page_tool(t: dict) -> str:
    link = LINKS[t["slug"]]
    pros = "".join(f"<li>{ICON['check']}<span>{esc(p)}</span></li>" for p in t["pros"])
    cons = "".join(f"<li>{ICON['x']}<span>{esc(c)}</span></li>" for c in t["cons"])
    figure = screenshot_figure(t)
    parts = []
    for i, s in enumerate(t["sections"]):
        parts.append(f'<h2 id="{slugify(s["h"])}">{esc(s["h"])}</h2>')
        if i == 1 and figure:
            parts.append(figure)  # reference figure sits inside the second section, after the opening one
        parts.extend(f"<p>{p}</p>" for p in s["p"])
    if figure and len(t["sections"]) < 2:
        parts.append(figure)
    sections = "".join(parts)
    pricing = ('<div class="table-scroll"><table class="pricing-table"><thead><tr><th scope="col">Plan</th><th scope="col">Price</th><th scope="col">What you get</th></tr></thead><tbody>'
               + "".join(f'<tr><td>{esc(p["plan"])}</td><td>{esc(p["price"])}</td><td>{esc(p["notes"])}</td></tr>' for p in t["pricing"])
               + '</tbody></table></div>')
    alts = "".join(
        f'<a href="/tools/{a}/">{score_badge(TOOL_BY_SLUG[a]["score"])}<div><b>{esc(TOOL_BY_SLUG[a]["name"])}</b><span>{esc(TOOL_BY_SLUG[a]["tagline"])}</span></div></a>'
        for a in t.get("alternatives", []) if a in TOOL_BY_SLUG
    )
    vids = [v for v in VIDEOS if t["slug"] in v["tools"]] if SHOW_VIDEOS else []
    vids_html = ""
    if vids:
        vids_html = f'<div><span class="kicker">Videos featuring {esc(t["name"])}</span><div class="grid grid--2">{"".join(video_card(v) for v in vids[:2])}</div></div>'
    fine = ("Affiliate link. We may earn a commission if you sign up. It does not change the score."
            if link.get("affiliate") else "Direct link to the vendor. If this becomes an affiliate link we will say so here.")
    minutes = read_time(tool_text(t))

    body = f'''
<div class="container">
  <header class="article-head">
    <span class="kicker">{esc(CATS[t["category"]])} · Review</span>
    <h1>{esc(t["headline"])}</h1>
    <p class="dek" data-clamp id="dek">{esc(t["dek"])}</p>
    <button class="dek-more" type="button" aria-expanded="false" aria-controls="dek" hidden>Read more</button>
    {byline([f"<b>{esc(SITE['byline'])}</b>", f"Updated {esc(fmt_date(t['date']))}", f'<span class="byline__read">{minutes} min read</span>'])}
  </header>
  <section class="verdict-top" aria-label="Verdict at a glance">
    <div class="verdict-top__row">
      {score_badge(t["score"])}
      <div class="verdict-top__text"><b>{esc(t["name"])}</b> <span class="verdict-top__label">{esc(score_label(t["score"]))}</span><p>{esc(t["tagline"])}</p></div>
    </div>
    <div class="verdict-top__cta">{go_link(t["slug"], f"Visit {t['name']}")}<span class="verdict__fine">{esc(fine)} <a href="/disclosure/">Disclosure</a></span></div>
  </section>
  <div class="review-layout">
    {rail(f'<span class="rail__score score-badge"><b>{t["score"]:.1f}</b><small>/10</small></span><span class="rail__section" aria-live="polite">{esc(t["name"])}</span><a href="#pricing">Pricing</a><a href="{go_href(t["slug"])}" rel="sponsored nofollow noopener" target="_blank">Visit</a>')}
    <div class="prose" data-article>
      <div class="proscons">
        <div class="pros"><h3>What works</h3><ul>{pros}</ul></div>
        <div class="cons"><h3>What doesn't</h3><ul>{cons}</ul></div>
      </div>
      <p class="cta-inline">{go_link(t["slug"], f"Visit {t['name']}")}<span class="verdict__fine">{esc(fine)} <a href="/disclosure/">Disclosure</a></span></p>
      {sections}
      <h2 id="pricing">Pricing</h2>
      <p>Prices checked {esc(fmt_date(t["date"]))}. Vendors change plans often, so confirm on their site before you pay.</p>
      {pricing}
      {"<h2 id='alternatives'>Alternatives we would consider</h2><div class='related'>" + alts + "</div>" if alts else ""}
      <div class="article-foot">
        {vids_html}
        {newsletter()}
      </div>
    </div>
    <aside class="verdict" aria-labelledby="verdict-title">
      <span class="kicker" id="verdict-title">Verdict</span>
      <div class="verdict__score score"><span class="score__num">{t["score"]:.1f}</span><span class="score__den">/10</span></div>
      <p class="verdict__label">{esc(score_label(t["score"]))}</p>
      <dl>
        <dt>Best for</dt><dd>{esc(t["bestFor"])}</dd>
        <dt>Price</dt><dd>{esc(t["priceFrom"])}</dd>
        <dt>Free tier</dt><dd>{esc(t["freeTier"])}</dd>
        <dt>Worth paying?</dt><dd>{esc(t["worthPaying"])}</dd>
      </dl>
      <div class="verdict__actions">
        {go_link(t["slug"], f"Visit {t['name']}")}
        <a class="btn btn--ghost" href="/tools/">Compare other tools</a>
      </div>
      <p class="verdict__fine">{esc(fine)} <a href="/disclosure/">Disclosure</a></p>
    </aside>
  </div>
</div>'''
    return layout(title=f"{t['name']} review", description=t["dek"], path=f"/tools/{t['slug']}/",
                  body=body, theme="light", current="tools", affiliate=True, article=True, og_type="article",
                  jsonld=ld(breadcrumbs(("Home", "/"), ("Tools", "/tools/"), (t["name"], f"/tools/{t['slug']}/")), review_node(t)))


def page_videos_index() -> str:
    cards = "".join(video_card(v) for v in VIDEOS)
    body = f'''
<div class="container">
  <div class="page-head">
    <span class="kicker">Videos</span>
    <h1>Watch the workflow, not the pitch</h1>
    <p class="dek">Walkthroughs of real workflows. Each video page lists the tools used, with the review for each, so you can decide before you sign up for anything.</p>
  </div>
  <div class="grid grid--3 reveal-group">{cards}</div>
  <section class="section">{newsletter()}</section>
</div>'''
    return layout(title="Video tutorials", description="Curated video walkthroughs of AI tools used for real income work, each with the tools mentioned and links to our reviews.",
                  path="/videos/", body=body, theme="dark", current="videos")


def page_video(v: dict) -> str:
    vid = v["youtubeId"]
    if vid.startswith("YOUTUBE_ID"):
        player = f'<div class="player__missing"><p>This video is not published yet.<br>Set <code>youtubeId</code> for <code>{esc(v["slug"])}</code> in <code>content/videos.json</code>.</p></div>'
    else:
        player = (f'<button class="player__facade" type="button" data-youtube-id="{esc(vid)}" aria-label="Play: {esc(v["title"])}">'
                  f'<img src="https://i.ytimg.com/vi/{esc(vid)}/hqdefault.jpg" alt="" width="480" height="360" decoding="async">'
                  f'<span class="video-card__play">{ICON["play"]}</span></button>')
    tools = [TOOL_BY_SLUG[s] for s in v["tools"] if s in TOOL_BY_SLUG]
    mentioned = "".join(mentioned_item(t) for t in tools)
    notes = "".join(f"<p>{esc(p)}</p>" for p in v["notes"])
    related = [x for x in VIDEOS if x["slug"] != v["slug"]][:3]
    related_html = "".join(video_card(x) for x in related)

    body = f'''
<div class="video-band">
  <div class="container">
    <div class="player">{player}</div>
    <div class="video-head">
      <span class="kicker">Video · {esc(v["duration"])} · {esc(fmt_date(v["date"]))}</span>
      <h1>{esc(v["title"])}</h1>
      <p>{esc(v["dek"])}</p>
    </div>
  </div>
</div>
<div class="container container--narrow">
  <section class="section section--tight" aria-labelledby="mentioned-title">
    <div class="section-head"><h2 id="mentioned-title">Tools mentioned in this video</h2></div>
    <div class="mentioned">{mentioned}</div>
  </section>
  <section class="section section--tight">
    <div class="section-head"><h2>What the video covers</h2></div>
    <div class="prose">{notes}</div>
  </section>
  <section class="section section--tight">
    <div class="section-head"><h2>More videos</h2><a href="/videos/">All videos</a></div>
    <div class="grid grid--3 reveal-group">{related_html}</div>
  </section>
  <section class="section section--tight">{newsletter()}</section>
</div>'''
    return layout(title=v["title"], description=v["dek"], path=f"/videos/{v['slug']}/", body=body,
                  theme="light", current="videos", affiliate=bool(tools), og_type="video.other")


def page_guides_index() -> str:
    rows = "".join(
        story_row(g["kicker"], f"/guides/{g['slug']}/", g["title"], g["dek"], f"{esc(fmt_date(g['date']))} · {read_time(g['body'])} min read")
        for g in GUIDES
    )
    body = f'''
<div class="container">
  <div class="page-head">
    <span class="kicker">Guides</span>
    <h1>Long reads on earning with AI tools</h1>
    <p class="dek">Practical workflows built from what practitioners consistently report and what the platforms themselves document, with the costs, the time involved, and the parts that tend not to work. Roundups compare tools we have reviewed in full.</p>
  </div>
  <div class="story-list reveal">{rows}</div>
  <section class="section">{newsletter()}</section>
</div>'''
    return layout(title="Guides", description="Long-form guides to earning with AI tools, written from real workflows with honest numbers.",
                  path="/guides/", body=body, theme="dark", current="guides")


def page_guide(g: dict) -> str:
    def replace_tool(m: re.Match) -> str:
        t = TOOL_BY_SLUG.get(m.group(1))
        return mentioned_item(t) if t else ""
    body_html = re.sub(r"<!--tool:([a-z0-9-]+)-->", replace_tool, g["body"])
    toc_items = []
    def add_id(m: re.Match) -> str:
        text = re.sub(r"<[^>]+>", "", m.group(1))
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or f"section-{len(toc_items)+1}"
        toc_items.append((slug, text))
        return f'<h2 id="{slug}">{m.group(1)}</h2>'
    body_html = re.sub(r"<h2>(.*?)</h2>", add_id, body_html, flags=re.S)
    toc = ""; toc_inline = ""
    if len(toc_items) >= 3:
        items = "".join(f'<li><a href="#{s}">{esc(x)}</a></li>' for s, x in toc_items)
        toc = f'<nav class="toc" aria-label="On this page"><span class="kicker">On this page</span><ol>{items}</ol></nav>'
        toc_inline = f'<details class="toc-inline"><summary>On this page</summary><ol>{items}</ol></details>'
    body_html = label_tables(body_html)
    body = f'''
<div class="container container--narrow">
  <header class="article-head">
    <span class="kicker">{esc(g["kicker"])}</span>
    <h1>{esc(g["title"])}</h1>
    <p class="dek">{esc(g["dek"])}</p>
    {byline([f"<b>{esc(SITE['byline'])}</b>", esc(fmt_date(g["date"])), f"{read_time(g['body'])} min read"])}
    {toc_inline}
  </header>
  <div class="guide-layout">
    {rail(f'<span class="kicker">{esc(g["kicker"])}</span><span class="rail__section" aria-live="polite">{esc(g["title"])}</span><a href="#main">Top</a>')}
    <div class="prose" data-article>
      {body_html}
      <div class="article-foot">{newsletter()}</div>
    </div>
    {toc}
  </div>
</div>'''
    return layout(title=g["title"], description=g["dek"], path=f"/guides/{g['slug']}/", body=body,
                  jsonld=ld(breadcrumbs(("Home", "/"), ("Guides", "/guides/"), (g["title"], f"/guides/{g['slug']}/")), article_node(g)),
                  theme="light", current="guides", affiliate=bool(g["tools"]), article=True, og_type="article")


def page_about() -> str:
    body = f'''
<div class="container container--narrow">
  <header class="article-head">
    <span class="kicker">About</span>
    <h1>Who we are and how we work</h1>
    <p class="dek">{esc(SITE["name"])} is a small independent publication. We research AI tools for the kind of work our readers do: freelance writing, faceless video channels, design gigs, small automations, Pinterest and search traffic. Then we say plainly which ones are worth paying for.</p>
  </header>
  <div class="prose" data-article>
    <h2>The masthead</h2>
    <p>Reviews are published under the {esc(SITE["byline"])} byline. The date at the top of each review is when it was last researched and its pricing checked.</p>
    <p>We are not affiliated with any tool maker. No vendor sees a review before it is published, and none can pay to be included, excluded, or moved up a list.</p>

    <h2>How reviews are researched</h2>
    <p>Our reviews are researched overviews, not hands-on lab tests. Each one is built from the same sources, in the same order:</p>
    <ol>
      <li><strong>The vendor's own documentation and pricing page</strong>, read in full, including the limits and licence terms that marketing pages leave out.</li>
      <li><strong>Independent reviews and published comparisons</strong> from writers, creators and developers who use the tool for paid work.</li>
      <li><strong>User reports</strong> in community forums and review platforms, weighted towards complaints that recur across many accounts rather than one-off gripes.</li>
      <li><strong>Direct comparison with alternatives</strong> in the same category, on price, limits and the jobs each is best known for.</li>
    </ol>
    <p>Where a strength or weakness comes from user reports rather than documentation, the review says so. Where we could not verify a claim, it is not in the review.</p>

    <h2>How a tool gets scored</h2>
    <p>Scores are out of 10 and reflect one question: <strong>is this worth the money for someone trying to earn with it?</strong> A tool can be technically impressive and still score a 6 because the price does not match the output. The other way around also happens.</p>
    <ul>
      <li><strong>9 to 10</strong> — Exceptional. The clear choice in its category at its price.</li>
      <li><strong>8 to 8.9</strong> — Recommended. Clear value for the price for its core use case.</li>
      <li><strong>7 to 7.9</strong> — Good, with caveats. Worth it for a specific type of user, and we say which.</li>
      <li><strong>6 to 6.9</strong> — Mixed. Something real is there, but a cheaper or better option usually exists.</li>
      <li><strong>Under 6</strong> — Hard to recommend. We explain what would change our mind.</li>
    </ul>
    <p>We revisit a review when a tool changes materially, and update the score and date. Old scores are not left standing quietly.</p>

    <h2>What we weigh</h2>
    <p>Reported output quality on real briefs, how much cleanup a human still has to do, pricing and quota traps, export and ownership terms, and whether the free tier is genuinely useful or just a demo.</p>

    <h2 id="corrections">Corrections</h2>
    <p>If something is wrong, tell us at <a href="mailto:{esc(SITE["contactEmail"])}">{esc(SITE["contactEmail"])}</a>. Factual errors get fixed and noted at the bottom of the page. Pricing changes get a new "checked" date.</p>

    <h2>How the site makes money</h2>
    <p>Some links to tools are affiliate links. It is how the site pays for itself. It is not how we decide what to recommend. The <a href="/disclosure/">full disclosure</a> spells out the rules we follow.</p>
    <div class="article-foot">{newsletter()}</div>
  </div>
</div>'''
    return layout(title="About and how we work", description="Who runs AIHustleSurfer, how tools are researched and scored, and how the site makes money.",
                  path="/about/", body=body, theme="light", current="about", article=True)


def page_disclosure() -> str:
    body = f'''
<div class="container container--narrow">
  <header class="article-head">
    <span class="kicker">Disclosure</span>
    <h1>Affiliate disclosure</h1>
    <p class="dek">The plain version: some links earn us a commission. Here is exactly how that works and the rules we hold ourselves to.</p>
  </header>
  <div class="prose" data-article>
    <h2>What an affiliate link is</h2>
    <p>When you click a link on this site that goes to a tool's website and then sign up or buy something, the tool maker may pay us a commission. It costs you nothing extra. In some cases you get a discount through our link; when that is true we say so on the page.</p>
    <p>Links that can earn a commission go through our own <code>/go/</code> address before reaching the vendor, and are marked as sponsored in the page code. If a tool has no affiliate programme, or we have not joined it, the link goes to the vendor directly.</p>

    <h2>Where you will see them</h2>
    <ul>
      <li>The "Visit" button in the verdict box on tool reviews.</li>
      <li>The "Tools mentioned in this video" section on video pages.</li>
      <li>Tool cards inside roundup guides.</li>
    </ul>
    <p>Every page that contains an affiliate link shows a notice near the top, and this disclosure is linked from the footer of every page.</p>

    <h2>Our rules</h2>
    <ol>
      <li><strong>Scores are set before we look at whether a link pays.</strong> The reviewer scores the tool. Affiliate links are added afterwards, by someone else, from the links file.</li>
      <li><strong>A tool without an affiliate programme gets the same treatment</strong> as one with a generous one. Several of our highest-scored tools pay us nothing.</li>
      <li><strong>We do not accept payment, free plans, or sponsorships in exchange for coverage.</strong></li>
      <li><strong>Vendors do not see reviews before publication</strong> and cannot request changes beyond factual corrections.</li>
      <li><strong>No fake urgency.</strong> We do not use countdown timers, "limited spots", or income screenshots. If a real discount exists, we state the terms.</li>
    </ol>

    <h2>Amazon and other networks</h2>
    <p>If we participate in the Amazon Services LLC Associates Program or similar networks, we earn from qualifying purchases. We list the programmes we belong to here when that changes.</p>

    <h2>Questions</h2>
    <p>Ask us anything about this at <a href="mailto:{esc(SITE["contactEmail"])}">{esc(SITE["contactEmail"])}</a>. This page was last updated {esc(latest_update())}.</p>
  </div>
</div>'''
    return layout(title="Affiliate disclosure", description="How AIHustleSurfer makes money from affiliate links, where they appear, and the editorial rules that keep them from affecting reviews.",
                  path="/disclosure/", body=body, theme="light", current="disclosure", article=True)



def page_subscribed(ok: bool) -> str:
    if ok:
        head, dek, extra = ("You are on the list",
                            "One email when we publish something worth your time. No sequences, no upsells, and one click to leave.",
                            "")
    else:
        head, dek, extra = ("That did not go through",
                            "We could not add that address. Either it was not a valid email, or our email service was unavailable for a moment.",
                            f'<p>Try again from any page, or email <a href="mailto:{esc(SITE["contactEmail"])}">{esc(SITE["contactEmail"])}</a> and we will add you by hand.</p>')
    body = f'''
<div class="container container--narrow">
  <header class="article-head">
    <span class="kicker">Newsletter</span>
    <h1>{head}</h1>
    <p class="dek">{dek}</p>
    {extra}
    <p><a class="btn btn--ghost" href="/tools/">Browse tool reviews</a> <a class="btn btn--ghost" href="/">Home</a></p>
  </header>
</div>'''
    path = "/subscribed/" if ok else "/subscribed/problem/"
    return layout(title=head, description=dek, path=path, body=body, theme="light",
                  extra_head='<meta name="robots" content="noindex">' + chr(10))

def page_404() -> str:
    body = f'''
<div class="container container--narrow">
  <header class="article-head">
    <span class="kicker">404</span>
    <h1>That page is not here</h1>
    <p class="dek">It may have moved, or the link was wrong. The directory and guides are the best places to start over.</p>
    <p><a class="btn btn--primary" href="/tools/">Browse tool reviews</a> <a class="btn btn--ghost" href="/">Home</a></p>
  </header>
</div>'''
    return layout(title="Page not found", description="Page not found.", path="/404", body=body, theme="dark")


def page_go(slug: str, url: str, name: str) -> str:
    u = esc(url, quote=True)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Taking you to {esc(name)}</title>
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="refresh" content="0; url={u}">
<script>location.replace({json.dumps(url)})</script>
<style>body{{font-family:system-ui,sans-serif;background:#0B0F1F;color:#F6F3EE;display:grid;place-items:center;min-height:100vh;margin:0}}a{{color:#8579EC}}</style>
</head>
<body><p>Taking you to <a href="{u}" rel="sponsored nofollow noopener">{esc(name)}</a>…</p></body>
</html>
'''


# --------------------------------------------------------------------------
# Write everything
# --------------------------------------------------------------------------
def write(rel: str, content: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, "utf-8", newline="\n")


def clean_generated(dirname: str, keep: set[str]) -> None:
    d = ROOT / dirname
    if not d.exists():
        return
    for child in d.iterdir():
        if child.is_dir() and child.name not in keep:
            shutil.rmtree(child)


def main() -> None:
    pages: list[str] = []

    write("index.html", page_home()); pages.append("/")
    write("tools/index.html", page_tools_index()); pages.append("/tools/")
    for t in TOOLS:
        write(f"tools/{t['slug']}/index.html", page_tool(t)); pages.append(f"/tools/{t['slug']}/")
    if SHOW_VIDEOS:
        write("videos/index.html", page_videos_index()); pages.append("/videos/")
        for v in VIDEOS:
            write(f"videos/{v['slug']}/index.html", page_video(v)); pages.append(f"/videos/{v['slug']}/")
    write("guides/index.html", page_guides_index()); pages.append("/guides/")
    for g in GUIDES:
        write(f"guides/{g['slug']}/index.html", page_guide(g)); pages.append(f"/guides/{g['slug']}/")
    write("about/index.html", page_about()); pages.append("/about/")
    write("disclosure/index.html", page_disclosure()); pages.append("/disclosure/")
    write("404.html", page_404())
    write("subscribed/index.html", page_subscribed(True))
    write("subscribed/problem/index.html", page_subscribed(False))

    for slug, link in LINKS.items():
        name = TOOL_BY_SLUG.get(slug, {}).get("name", slug)
        write(f"go/{slug}/index.html", page_go(slug, link["url"], name))

    clean_generated("tools", {t["slug"] for t in TOOLS})
    if SHOW_VIDEOS:
        clean_generated("videos", {v["slug"] for v in VIDEOS})
    else:
        shutil.rmtree(ROOT / "videos", ignore_errors=True)
    clean_generated("guides", {g["slug"] for g in GUIDES})
    clean_generated("go", set(LINKS))

    redirects = []
    for slug, link in LINKS.items():
        for src in (f"/go/{slug}", f"/go/{slug}/"):
            redirects.append({"source": src, "destination": link["url"], "permanent": False})
    # The KDP Research Tool is a separate Next.js project (reduxes101-droid/
    # kdp-research-tool, basePath /kdp) mounted here by rewrite. vercel.json is
    # generated, so the rewrite lives in this block, not in the JSON file.
    kdp_origin = "https://kdp-research-tool.vercel.app"
    vercel = {
        "cleanUrls": True,
        "trailingSlash": True,
        "redirects": redirects,
        "rewrites": [
            {"source": "/kdp", "destination": f"{kdp_origin}/kdp/"},
            {"source": "/kdp/(.*)", "destination": f"{kdp_origin}/kdp/$1"},
        ],
        "headers": [
            {"source": "/assets/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
            {"source": "/api/(.*)", "headers": [{"key": "Cache-Control", "value": "no-store"}]},
            {"source": "/(.*)", "headers": [
                {"key": "X-Content-Type-Options", "value": "nosniff"},
                {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
            ]},
        ],
    }
    write("vercel.json", json.dumps(vercel, indent=2) + "\n")

    base = SITE["url"].rstrip("/")
    today = dt.date.today().isoformat()
    urls = "".join(f"  <url><loc>{base}{p}</loc><lastmod>{today}</lastmod></url>\n" for p in pages)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /go/\nDisallow: /api/\nDisallow: /subscribed/\nSitemap: {base}/sitemap.xml\nSitemap: {base}/kdp/sitemap.xml\n")

    print(f"Built {len(pages)} pages, {len(LINKS)} redirects.")


if __name__ == "__main__":
    main()

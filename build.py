#!/usr/bin/env python3
"""
Build script for 915devotional.com

Master list:  devotionals.json            (the daily GitHub Action adds new YouTube videos here)
Optional:     content/devotionals/*.txt   (a written devotional + transcript for any video)
Writes dist/  (the folder Netlify publishes):
    archive/<slug>.html   one page per video (video + schema; write-up + transcript when a .txt exists)
    devotionals.json      same data plus each page's url, feeds the home/archive/list pages
    sitemap.xml           every page on the site
    robots.txt            only if the repo doesn't already have one
and copies every other site file (html, css, js, images...) into dist/.

Every video gets a page automatically, so the daily Action -> push -> Netlify build
publishes a new page with no manual step. Adding a .txt later upgrades that page in place
(same URL).

Standard library only. Python 3.8+.
Run locally:  python3 build.py      then open dist/
"""

import datetime
import html
import json
import os
import re
import shutil
import sys
from string import Template

SITE = "https://915devotional.com"
SHOW = "9:15 Devotional"
HOST = "DeWayne Dunko"
HOST_VARIANTS = ["Carlton DeWayne Dunko", "Carlton Dunko", "Carlton D. Dunko", "Dewayne Dunko"]

# One person entity shared across all three sites (same @id as carltondewaynedunko.com).
PERSON_ID = "https://carltondewaynedunko.com/#person"
PERSON_SAMEAS = [
    "https://carltondewaynedunko.com/",
    "https://carltondewaynedunkoblog.com/",
    "https://www.linkedin.com/in/dewayne-dunko-81503a135/",
    "https://www.youtube.com/@915devotional",
]
ORG_SAMEAS = ["https://www.youtube.com/@915devotional"]
FOOTER_LINKS = [
    ("carltondewaynedunko.com", "https://carltondewaynedunko.com/"),
    ("Devotional Journal", "https://carltondewaynedunkoblog.com/"),
    ("YouTube", "https://www.youtube.com/@915devotional"),
]

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content", "devotionals")
DIST = os.path.join(ROOT, "dist")

# Never published.
SKIP_COPY = {"dist", "content", "scripts", "build.py", "netlify.toml", "README.md",
             "ziWxXINS", "node_modules", "__pycache__"}


def fail(msg):
    print("BUILD ERROR: " + msg)
    sys.exit(1)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", re.sub(r"['\u2019]", "", text.lower())).strip("-")
    return s or "devotional"


# ---------------------------------------------------------------- .txt sources

def parse_source(path):
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\r\n", "\n")
    name = os.path.basename(path)
    m = re.search(r"^---[ \t]*$", text, re.M)
    if not m:
        fail("%s: missing the '---' line under the header" % name)
    head, body = text[:m.start()], text[m.end():]
    meta = {"_file": name}
    for line in head.split("\n"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if ":" not in line:
            fail("%s: header line without a colon: %r" % (name, line))
        k, v = line.split(":", 1)
        meta[k.strip().lower()] = v.strip()
    mk = re.search(r"(?m)^=== transcript ===[ \t]*$", body)
    meta["written"] = body[:mk.start()].strip() if mk else body.strip()
    meta["body"] = body[mk.end():] if mk else ""
    meta["draft"] = "TODO" in meta["written"] or any(
        "TODO" in v for k, v in meta.items() if k not in ("body", "written"))
    yt = meta.get("youtube", "")
    if not re.match(r"^[A-Za-z0-9_-]{11}$", yt):
        fail("%s: youtube must be the 11-character video id" % name)
    return meta


TIMESTAMP = re.compile(r"(?m)^[ \t]*\d{1,2}:\d{2}(?::\d{2})?\d+ (?:hours?|minutes?|seconds?)(?:, \d+ (?:minutes?|seconds?))*")


def clean_transcript(raw):
    opens = len(re.findall(r"\[\[cut\]\]", raw, re.I))
    if opens != len(re.findall(r"\[\[/cut\]\]", raw, re.I)):
        fail("a transcript has unmatched [[cut]] / [[/cut]]")
    text = re.sub(r"\[\[cut\]\].*?\[\[/cut\]\]", " ", raw, flags=re.S | re.I)
    text = re.sub(r"(?m)^[ \t]*//.*$", "", text)
    text = TIMESTAMP.sub("", text)
    text = re.sub(r"(?im)^[ \t]*sync to video time[ \t]*$", "", text)
    text = re.sub(r"\[[^\]\n]{1,40}\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.?!;:])", r"\1", text)
    if not text:
        return [], opens > 0
    paragraphs, current = [], ""
    for sent in re.split(r"(?<=[.?!])\s+", text):
        current = (current + " " + sent).strip()
        if len(current) >= 550:
            paragraphs.append(current)
            current = ""
    if current:
        paragraphs.append(current)
    return paragraphs, opens > 0


def render_written(text):
    """blank line = new paragraph, '## ' = heading, '- ' lines = bullet list."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if lines and lines[0].startswith("## "):
            out.append("<h2>%s</h2>" % html.escape(lines[0][3:]))
            lines = lines[1:]
        if lines and all(l.startswith("- ") for l in lines):
            out.append("<ul>" + "".join("<li>%s</li>" % html.escape(l[2:]) for l in lines) + "</ul>")
        elif lines:
            out.append("<p>%s</p>" % html.escape(" ".join(lines)))
    return "\n".join(out)


# ---------------------------------------------------------------- page

PAGE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${head_title}</title>
<meta name="description" content="${desc_attr}">
<link rel="canonical" href="${url}">
<meta name="author" content="${host}">
<meta property="og:type" content="video.other">
<meta property="og:site_name" content="${show}">
<meta property="og:title" content="${head_title}">
<meta property="og:description" content="${desc_attr}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${thumb}">
<meta property="og:video" content="https://www.youtube.com/embed/${yt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${head_title}">
<meta name="twitter:description" content="${desc_attr}">
<meta name="twitter:image" content="${thumb}">
<link rel="stylesheet" href="/styles.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<script type="application/ld+json">
${jsonld}
</script>
<style>
.breadcrumb{font-size:13px;color:var(--color-muted);margin:0 0 14px}
.breadcrumb a{color:var(--color-muted)}
.devo-wrap{padding:36px 0 10px}
.devo-embed{max-width:860px;margin:0 auto}
.devo-ratio{position:relative;width:100%;padding-top:56.25%;background:#000;border-radius:var(--radius-lg);overflow:hidden;box-shadow:var(--shadow-md)}
.devo-ratio iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.devo-meta{max-width:860px;margin:18px auto 0;font-size:15px;line-height:1.7;color:var(--color-text-soft)}
.devo-meta a{font-weight:600}
.byline{font-size:14px;color:var(--color-text-soft);margin:14px 0 0}
.written{max-width:860px;margin:36px auto 0;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:8px 28px 20px}
.written h2{font-family:var(--font-serif);font-size:28px;font-weight:600;color:var(--color-accent);margin:22px 0 8px}
.written p,.written li{font-size:17px;line-height:1.75;color:var(--color-text)}
.written p{margin:0 0 14px}
.written ul{margin:0 0 14px;padding-left:22px}
.transcript{max-width:860px;margin:36px auto 0;background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);padding:0 28px}
.transcript summary{cursor:pointer;font-family:var(--font-serif);font-size:26px;font-weight:600;color:var(--color-accent);padding:20px 0}
.transcript p{font-size:16px;line-height:1.8;color:var(--color-text);margin:0 0 18px}
.transcript .transcript-note{font-size:13px;color:var(--color-muted);font-style:italic}
.devo-nav{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;max-width:860px;margin:32px auto 60px;font-size:15px;font-weight:600}
.site-footer .footer-note a{color:var(--color-gold-soft)}
@media (max-width:600px){.written,.transcript{padding-left:18px;padding-right:18px}}
</style>
</head>
<body>
<header class="site-header">
<div class="container header-inner">
<a href="/index.html" class="logo"><span class="logo-mark">9:15</span><span class="logo-text">Devotional</span></a>
<nav class="nav">
<a href="/index.html">Home</a>
<a href="/devotionals.html" class="active">Archive</a>
<a href="/list.html">List</a>
<a href="/prayer.html">Prayer Requests</a>
</nav>
</div>
</header>

<section class="page-hero">
<div class="container">
<p class="breadcrumb"><a href="/index.html">Home</a> / <a href="/devotionals.html">Archive</a> / ${scripture_plain}</p>
<p class="eyebrow">${eyebrow}</p>
<h1>${title}</h1>
<p class="lede">${summary}</p>
<p class="byline">With <a href="https://carltondewaynedunko.com/">${host}</a> &middot; ${date_pretty}</p>
</div>
</section>

<section class="host-strip"><div class="container"><div class="host-strip-inner">
<div class="host-photo"><img src="/images/dewayne.png" alt="${host}" onerror="this.style.display='none'; this.parentElement.classList.add('host-photo-placeholder');"></div>
<div class="host-text"><p class="host-label">Brought to you by</p><p class="host-name">${host}</p></div>
</div></div></section>

<section class="devo-wrap">
<div class="container">
<div class="devo-embed"><div class="devo-ratio"><iframe src="https://www.youtube.com/embed/${yt}?rel=0&amp;modestbranding=1" title="${title_attr}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div></div>
<p class="devo-meta">${host} leads the 9:15 Devotional live on Zoom, Monday through Thursday at 9:15 AM Eastern. <a href="/index.html">Join the next one</a> or <a href="https://www.youtube.com/watch?v=${yt}">watch on YouTube</a>.${extra_links}</p>
${written_block}
${transcript_block}
<div class="devo-nav">${prev_link}${next_link}</div>
</div>
</section>

<section class="prayer-cta"><div class="container"><div class="prayer-cta-inner"><h2>Need prayer?</h2><p>&ldquo;Cast all your anxiety on him because he cares for you.&rdquo; &mdash; 1 Peter 5:7</p><a href="/prayer.html" class="btn btn-primary">Submit a Prayer Request</a></div></div></section>

<footer class="site-footer"><div class="container footer-inner">
<p>&copy; <span id="year"></span> 9:15 Devotional</p>
<p class="footer-note">${footer_links}</p>
</div></footer>
<script src="/script.js"></script>
</body>
</html>
""")


def pretty_date(iso):
    y, m, d = [int(x) for x in iso.split("-")]
    dt = datetime.date(y, m, d)
    return "%s %d, %d" % (dt.strftime("%B"), dt.day, dt.year)


def auto_summary(d):
    scr = d["scripture"] or d["title"]
    return ("%s on %s: a 9:15 Devotional Bible study and prayer, recorded live %s."
            % (HOST, scr, pretty_date(d["date"])))


def build_jsonld(d, url):
    oid, wid = SITE + "/#organization", SITE + "/#website"
    thumb = "https://img.youtube.com/vi/%s/hqdefault.jpg" % d["youtube"]
    person = {
        "@type": "Person", "@id": PERSON_ID, "name": HOST, "alternateName": HOST_VARIANTS,
        "url": "https://carltondewaynedunko.com/", "jobTitle": "Bible Teacher", "sameAs": PERSON_SAMEAS,
    }
    org = {"@type": "Organization", "@id": oid, "name": SHOW, "url": SITE + "/",
           "founder": {"@id": PERSON_ID}, "sameAs": ORG_SAMEAS}
    site = {"@type": "WebSite", "@id": wid, "url": SITE + "/", "name": SHOW, "publisher": {"@id": oid}}
    main_id = url + ("#article" if d["written"] else "#video")
    webpage = {
        "@type": "WebPage", "@id": url + "#webpage", "url": url, "name": d["title"],
        "description": d["summary"], "isPartOf": {"@id": wid}, "about": {"@id": PERSON_ID},
        "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": main_id},
        "primaryImageOfPage": thumb,
    }
    breadcrumb = {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Archive", "item": SITE + "/devotionals.html"},
        {"@type": "ListItem", "position": 3, "name": d["title"], "item": url},
    ]}
    video = {
        "@type": "VideoObject", "@id": url + "#video", "name": d["title"], "description": d["summary"],
        "thumbnailUrl": [thumb], "uploadDate": d["date"],
        "embedUrl": "https://www.youtube.com/embed/%s" % d["youtube"],
        "url": "https://www.youtube.com/watch?v=%s" % d["youtube"],
        "inLanguage": "en", "isFamilyFriendly": True,
        "actor": {"@id": PERSON_ID}, "creator": {"@id": PERSON_ID}, "publisher": {"@id": oid},
        "partOfSeries": {"@type": "CreativeWorkSeries", "name": SHOW, "@id": oid},
        "mainEntityOfPage": {"@id": url + "#webpage"},
    }
    if d["scripture"]:
        video["about"] = d["scripture"]
    graph = [person, org, site, webpage, breadcrumb, video]
    if d["written"]:
        graph.append({
            "@type": "Article", "@id": url + "#article", "headline": d["title"], "description": d["summary"],
            "image": [thumb], "datePublished": d["date"], "dateModified": d["date"], "inLanguage": "en",
            "author": {"@id": PERSON_ID}, "publisher": {"@id": oid},
            "mainEntityOfPage": {"@id": url + "#webpage"}, "video": {"@id": url + "#video"},
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=1).replace("</", "<\\/")


def render_page(d, newer, older):
    url = "%s/archive/%s.html" % (SITE, d["slug"])
    paragraphs, had_cut = clean_transcript(d["body"])
    if paragraphs:
        note = "Transcript generated from the recording and lightly edited for readability."
        if had_cut:
            note += " Personal prayer requests and side conversations have been omitted."
        transcript_block = (
            '<details class="transcript"><summary>Read the full transcript</summary>\n'
            + "\n".join("<p>%s</p>" % html.escape(p) for p in paragraphs)
            + '\n<p class="transcript-note">%s</p>\n</details>' % html.escape(note))
    else:
        transcript_block = ""

    extra = []
    if d.get("transcript_url"):
        extra.append('<a href="%s">Read the full transcript</a>' % html.escape(d["transcript_url"], quote=True))
    if d.get("blog"):
        extra.append('<a href="%s">Read the longer reflection on the Journal</a>' % html.escape(d["blog"], quote=True))
    extra_links = (" " + ". ".join(extra) + ".") if extra else ""

    prev_link = ('<a href="/archive/%s.html">&larr; %s</a>' % (older["slug"], html.escape(older["title"]))) if older else "<span></span>"
    next_link = ('<a href="/archive/%s.html">%s &rarr;</a>' % (newer["slug"], html.escape(newer["title"]))) if newer else "<span></span>"

    if d["written"]:
        head_title = "%s | %s with %s" % (d["title"], SHOW, HOST)
    else:
        head_title = "%s Devotional with %s | %s" % (d["title"], HOST, SHOW)
    if len(d["summary"]) > 165:
        print("  note: %s summary is %d chars (Google shows ~155)" % (d["slug"], len(d["summary"])))

    scripture_plain = d["scripture"] or d["title"]
    return PAGE.substitute(
        head_title=html.escape(head_title, quote=True),
        desc_attr=html.escape(d["summary"], quote=True),
        url=url, host=HOST, show=SHOW,
        thumb="https://img.youtube.com/vi/%s/hqdefault.jpg" % d["youtube"],
        yt=d["youtube"],
        jsonld=build_jsonld(d, url),
        scripture_plain=html.escape(scripture_plain),
        eyebrow=html.escape(scripture_plain if scripture_plain != d["title"] else "9:15 Devotional"),
        title=html.escape(d["title"]),
        title_attr=html.escape(d["title"], quote=True),
        summary=html.escape(d["summary"]),
        date_pretty=pretty_date(d["date"]),
        extra_links=extra_links,
        written_block=('<section class="written">\n%s\n</section>' % render_written(d["written"])) if d["written"] else "",
        transcript_block=transcript_block,
        prev_link=prev_link, next_link=next_link,
        footer_links=" &middot; ".join('<a href="%s">%s</a>' % (u, html.escape(n)) for n, u in FOOTER_LINKS),
    ), len(paragraphs)


# ---------------------------------------------------------------- main

def load_master():
    path = os.path.join(ROOT, "devotionals.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        fail("devotionals.json not found")
    except ValueError as e:
        fail("devotionals.json is not valid JSON: %s" % e)


def load_sources():
    sources, drafts = {}, []
    if not os.path.isdir(CONTENT):
        return sources, drafts
    for name in sorted(os.listdir(CONTENT)):
        if not name.endswith(".txt") or name.startswith("_"):
            continue
        meta = parse_source(os.path.join(CONTENT, name))
        if meta["draft"]:
            drafts.append(name)
            continue
        if meta["youtube"] in sources:
            fail("%s and %s use the same YouTube id" % (sources[meta["youtube"]]["_file"], name))
        sources[meta["youtube"]] = meta
    return sources, drafts


def main():
    data = load_master()
    entries = data.get("devotionals", [])
    sources, drafts = load_sources()

    # Assign stable slugs, oldest first, so a later duplicate title never steals an older URL.
    items, used = [], set()
    for e in sorted(entries, key=lambda e: (e.get("date", ""), e.get("youtubeId", ""))):
        yt = e.get("youtubeId", "")
        if not re.match(r"^[A-Za-z0-9_-]{11}$", yt) or not re.match(r"^\d{4}-\d{2}-\d{2}$", e.get("date", "")):
            print("  skipped an entry with a bad youtubeId/date: %r" % e.get("title"))
            continue
        src = sources.get(yt, {})
        slug = src.get("slug") or e.get("slug") or slugify(e.get("title") or yt)
        if slug in used:
            slug = "%s-%s" % (slug, e["date"])
        used.add(slug)
        scriptures = e.get("scriptures") or []
        d = {
            "slug": slug, "youtube": yt,
            "date": src.get("date") or e["date"],
            "title": src.get("title") or e.get("title") or "9:15 Devotional",
            "scripture": src.get("scripture") or "; ".join(scriptures),
            "summary": src.get("summary") or e.get("summary") or "",
            "written": src.get("written", ""), "body": src.get("body", ""),
            "blog": src.get("blog", ""), "transcript_url": src.get("transcript", ""),
            "entry": e,
        }
        if not d["summary"]:
            d["summary"] = auto_summary(d)
            d["auto_summary"] = True
        items.append(d)

    orphan = set(sources) - {d["youtube"] for d in items}
    for yt in orphan:
        print("  note: %s has youtube %s, which isn't in devotionals.json yet (page not built)"
              % (sources[yt]["_file"], yt))

    items.sort(key=lambda d: (d["date"], d["slug"]), reverse=True)

    # copy the static site
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "archive"))
    for name in sorted(os.listdir(ROOT)):
        if name in SKIP_COPY or name.startswith("."):
            continue
        src, dst = os.path.join(ROOT, name), os.path.join(DIST, name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)

    written = 0
    for i, d in enumerate(items):
        newer = items[i - 1] if i > 0 else None
        older = items[i + 1] if i + 1 < len(items) else None
        page, n_paras = render_page(d, newer, older)
        with open(os.path.join(DIST, "archive", d["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page)
        if d["written"] or n_paras:
            written += 1
            print("  %-40s %s  written: %-9s transcript: %s" % (
                d["slug"], d["date"], ("%d words" % len(d["written"].split())) if d["written"] else "none",
                ("%d paragraphs" % n_paras) if n_paras else "none"))

    # dist/devotionals.json: same shape as the repo file + url, and the .txt title/summary when present
    out_entries = []
    for d in items:
        e = dict(d["entry"])
        e["title"], e["date"] = d["title"], d["date"]
        if not d.get("auto_summary"):
            e["summary"] = d["summary"]
        e["url"] = "/archive/%s.html" % d["slug"]
        out_entries.append(e)
    out = dict(data)
    out["devotionals"] = out_entries
    with open(os.path.join(DIST, "devotionals.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # sitemap.xml
    urls = []
    for name in sorted(os.listdir(ROOT)):
        if name.endswith(".html") and name.lower() != "404.html":
            urls.append((SITE + "/" if name == "index.html" else "%s/%s" % (SITE, name), None))
    for d in items:
        urls.append(("%s/archive/%s.html" % (SITE, d["slug"]), d["date"]))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += ["  <url><loc>%s</loc>%s</url>" % (loc, ("<lastmod>%s</lastmod>" % lm) if lm else "") for loc, lm in urls]
    lines.append("</urlset>")
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    if not os.path.exists(os.path.join(ROOT, "robots.txt")):
        with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8") as f:
            f.write("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)

    if drafts:
        print("Skipped %d draft(s) that still contain TODO: %s" % (len(drafts), ", ".join(drafts)))
    print("Done. %d video pages (%d with a write-up/transcript), %d URLs in sitemap.xml."
          % (len(items), written, len(urls)))


if __name__ == "__main__":
    main()

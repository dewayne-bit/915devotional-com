#!/usr/bin/env python3
"""
915 Devotional — daily YouTube sync.

Runs on a schedule inside GitHub Actions. Checks the channel's public RSS
feed for any newly uploaded videos and adds them to devotionals.json so the
site publishes them automatically.

Scripture references are parsed from the video TITLE. It understands the
common ways DeWayne titles videos:
  "1 Peter 3:15"            -> 1 Peter 3:15
  "Acts 15: 36-41"          -> Acts 15:36-41
  "Mark 11 25"              -> Mark 11:25
  "Colossians 3 12 13"      -> Colossians 3:12-13
  "James 2 2to 4"           -> James 2:2-4
  "Galatians 5 and 22"      -> Galatians 5:22
  "matthew 13 31and 32"     -> Matthew 13:31-32
  "Proverbs 20 18 and 21 23"-> Proverbs 20:18, Proverbs 21:23
When a title is too ambiguous to be sure, it leaves the scripture blank
rather than guessing wrong — DeWayne can add it in a few seconds.
"""

import json
import re
import html
import urllib.request
import datetime
import os
import sys

CHANNEL_ID = "UCxjMHqqFNMEzl4aBwidt17Q"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "devotionals.json")

BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Songs",
    "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
    "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum",
    "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew",
    "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]
BOOKS_SORTED = sorted(BOOKS, key=len, reverse=True)
BOOK_ALT = "|".join(re.escape(b) for b in BOOKS_SORTED)
BOOK_RE = re.compile(rf"\b({BOOK_ALT})\b", re.IGNORECASE)


def fetch_feed():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def parse_entries(xml):
    entries = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        block = m.group(1)
        vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", block)
        title = re.search(r"<title>(.*?)</title>", block, re.S)
        pub = re.search(r"<published>([^<]+)</published>", block)
        if vid and title and pub:
            entries.append({
                "id": vid.group(1),
                "title": html.unescape(title.group(1).strip()),
                "published": pub.group(1)[:10],
            })
    return entries


def clean_title(raw):
    t = re.sub(r"^\s*915\s*devotional\s*[:\-]?\s*", "", raw, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t or raw.strip()


def canonical_book(name):
    for b in BOOKS:
        if b.lower() == name.lower():
            return b
    return name.title()


def _fmt(book, chap, v1, v2=None):
    return f"{book} {chap}:{v1}" + (f"-{v2}" if v2 else "")


def _parse_tail(book, tail):
    """Interpret the text right after a book name into scripture refs."""
    tokens = re.findall(r"\d+|:|-|–|to|thru|and|&|,", tail.lower())
    if not any(t.isdigit() for t in tokens):
        return []

    # ---- Colon form: authoritative — parse "chap:verse[-verse]" possibly repeated
    if ":" in tokens:
        refs = []
        for m in re.finditer(r"(\d+)\s*:\s*(\d+)(?:\s*[-–]\s*(\d+))?", tail):
            refs.append(_fmt(book, m.group(1), m.group(2), m.group(3)))
        return refs

    # ---- No colon: infer from the number groups, split on 'and'/'&'/','
    segments = [[]]
    for tok in tokens:
        if tok in ("and", "&", ","):
            if segments[-1]:
                segments.append([])
        elif tok.isdigit():
            segments[-1].append(int(tok))
        # '-','to','thru','–' are range hints; the numbers themselves carry it
    segments = [s for s in segments if s]
    if not segments:
        return []

    if len(segments) == 1:
        s = segments[0]
        if len(s) == 2:
            return [_fmt(book, s[0], s[1])]
        if len(s) == 3:
            return [_fmt(book, s[0], s[1], s[2])]
        return []  # 1 number (chapter only) or 4+ (too ambiguous)

    if len(segments) == 2:
        a, b = segments
        if len(a) == 1 and len(b) == 1:
            return [_fmt(book, a[0], b[0])]                          # "5 and 22" -> 5:22
        if len(a) == 2 and len(b) == 2:
            return [_fmt(book, a[0], a[1]), _fmt(book, b[0], b[1])]  # two refs
        if len(a) == 2 and len(b) == 1:
            if b[0] == a[1] + 1:
                return [_fmt(book, a[0], a[1], b[0])]                # consecutive -> range
            return [_fmt(book, a[0], a[1]), _fmt(book, a[0], b[0])]
        return []

    return []  # 3+ segments: too ambiguous, leave blank


def parse_scriptures(raw):
    refs = []
    matches = list(BOOK_RE.finditer(raw))
    for i, m in enumerate(matches):
        book = canonical_book(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        for ref in _parse_tail(book, raw[start:end]):
            if ref not in refs:
                refs.append(ref)
    return refs


def make_title(raw):
    """Prefer a clean scripture-reference title; fall back to the cleaned raw title."""
    scr = parse_scriptures(raw)
    if scr:
        return " & ".join(scr)
    return clean_title(raw)


def snap_to_devotional_day(iso_date):
    """Devotionals run Mon-Thu. Snap Fri/Sat/Sun uploads back to Thursday."""
    y, m, d = map(int, iso_date.split("-"))
    dt = datetime.date(y, m, d)
    wd = dt.weekday()  # Mon=0 .. Sun=6
    if wd >= 4:
        dt = dt - datetime.timedelta(days=wd - 3)
    return dt.isoformat()


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    devotionals = data.get("devotionals", [])
    existing_ids = {d.get("youtubeId") for d in devotionals}

    try:
        entries = parse_entries(fetch_feed())
    except Exception as e:
        print(f"Could not fetch/parse feed: {e}", file=sys.stderr)
        return 1

    added = []
    for e in entries:
        if e["id"] in existing_ids:
            continue
        entry = {
            "date": snap_to_devotional_day(e["published"]),
            "title": make_title(e["title"]),
            "scriptures": parse_scriptures(e["title"]),
            "youtubeId": e["id"],
            "summary": "",
        }
        devotionals.append(entry)
        existing_ids.add(e["id"])
        added.append(entry)

    if not added:
        print("No new devotionals.")
        return 0

    devotionals.sort(key=lambda d: d.get("date", ""), reverse=True)
    data["devotionals"] = devotionals
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Added {len(added)} new devotional(s):")
    for a in added:
        print(f"  {a['date']}  {a['title']}  ({a['youtubeId']})  {a['scriptures']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
915 Devotional — daily YouTube sync.

Runs on a schedule inside GitHub Actions. Checks the channel's public RSS
feed for any newly uploaded videos and adds them to devotionals.json so the
site publishes them automatically. Best-effort: it fills in the video title
and (when it can parse one) a scripture reference. DeWayne can polish any
title/scripture by editing devotionals.json directly.
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

# Bible books, longest-first so "1 John" wins over "John", etc.
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
# Matches "Book Chapter:Verse" or "Book Chapter:Verse-Verse" (conservative: colon required)
REF_RE = re.compile(rf"\b({BOOK_ALT})\s+(\d+):\s*(\d+)(?:\s*-\s*(\d+))?", re.IGNORECASE)


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


def parse_scriptures(raw):
    refs = []
    for m in REF_RE.finditer(raw):
        book = canonical_book(m.group(1))
        chap, v1, v2 = m.group(2), m.group(3), m.group(4)
        ref = f"{book} {chap}:{v1}" + (f"-{v2}" if v2 else "")
        if ref not in refs:
            refs.append(ref)
    return refs


def snap_to_devotional_day(iso_date):
    """Devotionals run Mon-Thu. Snap Fri/Sat/Sun uploads back to Thursday."""
    y, m, d = map(int, iso_date.split("-"))
    dt = datetime.date(y, m, d)
    wd = dt.weekday()  # Mon=0 .. Sun=6
    if wd >= 4:  # Fri, Sat, Sun
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
            "title": clean_title(e["title"]),
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

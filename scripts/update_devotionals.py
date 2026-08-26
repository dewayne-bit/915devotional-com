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
import difflib
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

# ---- Fuzzy book-name matching -------------------------------------------
# DeWayne types titles fast on his phone, so book names get misspelled
# ("Galations", "corithians", "Eccleciastes"). Exact matching silently
# dropped those scriptures. We now fall back to a close-match lookup.

# Books that only ever appear with a number in front of them.
NUMBERED_ONLY = {
    "samuel", "kings", "chronicles", "corinthians",
    "thessalonians", "timothy", "peter",
}
# Books that exist both bare and numbered (the Gospel of John vs 1-3 John).
NUMBERED_OPTIONAL = {"john"}

# base name (no leading number) -> canonical display name
BASE_TO_BOOK = {}
for _b in BOOKS:
    _base = _b.split(" ", 1)[1] if _b[0].isdigit() else _b
    BASE_TO_BOOK.setdefault(_base.lower(), _base)
BASE_TO_BOOK["psalm"] = "Psalms"          # normalize to one heading
BASE_NAMES = list(BASE_TO_BOOK.keys())

NUM_PREFIX = {
    "1": 1, "2": 2, "3": 3,
    "1st": 1, "2nd": 2, "3rd": 3,
    "first": 1, "second": 2, "third": 3,
    "i": 1, "ii": 2, "iii": 3,
}

WORD_RE = re.compile(r"[A-Za-z]+|\d+")


def _canonical_from_base(base_key, number):
    """Build the display name, e.g. ('peter', 1) -> '1 Peter'."""
    base = BASE_TO_BOOK[base_key]
    if base_key in NUMBERED_ONLY:
        return f"{number or 1} {base}"
    if base_key in NUMBERED_OPTIONAL and number:
        return f"{number} {base}"
    return base


def find_books(raw):
    """Yield (canonical_book, span_start, name_end) for each book named in raw.

    Exact names match anywhere. Misspellings only match when a digit follows
    close behind — that keeps ordinary words ('Joy', 'Last', 'Mom') from
    being mistaken for books.
    """
    tokens = [(m.group(0), m.start(), m.end()) for m in WORD_RE.finditer(raw)]
    found = []
    for i, (tok, ts, te) in enumerate(tokens):
        if not tok.isalpha():
            continue
        low = tok.lower()
        if low in NUM_PREFIX:      # this is a prefix, not a book name
            continue

        # "Song of Solomon" / "Song of Songs" — the only multi-word titles.
        if low == "song" and i + 2 < len(tokens) and tokens[i + 1][0].lower() == "of":
            third = tokens[i + 2][0].lower()
            if third in ("solomon", "songs"):
                found.append(("Song of Solomon", ts, tokens[i + 2][2]))
                continue

        base_key = None
        if low in BASE_TO_BOOK:
            base_key = low
        elif len(low) >= 5 and re.match(r"[\s:.,\-]*\d", raw[te:te + 12]):
            close = difflib.get_close_matches(low, BASE_NAMES, n=1, cutoff=0.8)
            if close:
                base_key = close[0]
        if not base_key:
            continue

        # Look back one token for a leading 1/2/3.
        number = None
        span_start = ts
        if i > 0:
            prev, ps, pe = tokens[i - 1]
            if prev.lower() in NUM_PREFIX and raw[pe:ts].strip(" .") == "":
                number = NUM_PREFIX[prev.lower()]
                span_start = ps
        found.append((_canonical_from_base(base_key, number), span_start, te))
    return found


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
        if len(s) == 1:
            return [f"{book} {s[0]}"]   # whole chapter, e.g. "Psalm 23"
        return []  # 4+ numbers: too ambiguous

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
    matches = find_books(raw)
    for i, (book, span_start, name_end) in enumerate(matches):
        end = matches[i + 1][1] if i + 1 < len(matches) else len(raw)
        for ref in _parse_tail(book, raw[name_end:end]):
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

    # Anything without a scripture won't appear under a book on list.html —
    # it lands in "Other Devotionals" instead. Call it out loudly in the log.
    missing = [a for a in added if not a["scriptures"]]
    if missing:
        print("")
        print("WARNING: no scripture could be read from these video titles.")
        print("They will show under 'Other Devotionals' on the Scripture List")
        print("page until a reference is added to devotionals.json:")
        for a in missing:
            print(f"  {a['date']}  {a['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

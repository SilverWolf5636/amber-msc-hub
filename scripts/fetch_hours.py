#!/usr/bin/env python3
"""Daily MSC hours robot. Standard library only.
Fetches https://mdsci.org/visit/hours-schedule, reads the weekly hours and the
holiday hours from the page TEXT, and writes hours.json only if the result
looks sane. If anything looks wrong it keeps the last good hours.json.
Usage: fetch_hours.py [--file saved_page.html] [--out hours.json] [--today YYYY-MM-DD]
"""
import json, re, sys, os, datetime, urllib.request
from html.parser import HTMLParser

URL = "https://mdsci.org/visit/hours-schedule"
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
T = r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?"
RANGE = re.compile(T + r"\s*(?:-|–|—|to)\s*" + T, re.I)
CLOSED = re.compile(r"\bclosed\b", re.I)

class Text(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "table", "ul", "ol", "dt", "dd"}
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"): self.skip += 1
        if tag in self.BLOCK: self.out.append("\n")
        if tag in ("td", "th"): self.out.append(" ")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"): self.skip = max(0, self.skip - 1)
        if tag in self.BLOCK: self.out.append("\n")
    def handle_data(self, d):
        if not self.skip: self.out.append(re.sub(r"\s+", " ", d))

def page_lines(html):
    p = Text(); p.feed(html)
    txt = "".join(p.out).replace("\xa0", " ").replace("|", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip(" #*") for l in txt.split("\n")]
    return [l for l in lines if l]

def mins(h, m, ap):
    h = int(h) % 12
    if ap.lower() == "p": h += 12
    return h * 60 + int(m or 0)

def parse_range(s):
    """Return {'closed':True} or {'open':min,'close':min} or None."""
    r = RANGE.search(s)
    if r:
        a = mins(r.group(1), r.group(2), r.group(3)); b = mins(r.group(4), r.group(5), r.group(6))
        return {"open": a, "close": b}
    if CLOSED.search(s): return {"closed": True}
    return None

def sane(x):
    if x is None: return False
    if x.get("closed"): return True
    return 6 * 60 <= x["open"] < x["close"] <= 23 * 60

def parse_weekly(lines):
    pats = {"mon": r"^mon(?:day)?\b", "tuefri": r"^tue(?:s|sday)?\s*(?:-|–|to)\s*fri", "satsun": r"^sat(?:urday)?\s*(?:-|–|to)\s*sun"}
    out = {}
    for k, pat in pats.items():
        for i, l in enumerate(lines):
            if re.search(pat, l, re.I):
                # the hours may be on the same line or the next one
                v = parse_range(l) or parse_range(" ".join(lines[i + 1:i + 3]))
                if v is not None: out[k] = v; break
    return out

DATE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b(?!\s*(?:am|pm))", re.I)

def parse_holidays(lines, today):
    out = []; seen = set()
    for i, l in enumerate(lines):
        m = DATE.search(l)
        if not m: continue
        rest = l[m.end():]
        v = parse_range(rest)
        if v is None and not rest.strip() and i + 1 < len(lines): v = parse_range(lines[i + 1])
        if v is None: continue
        mo = MONTHS[m.group(1).lower()]; d = int(m.group(2))
        # pick the year that puts this date within [today-60d, today+305d]
        for y in (today.year - 1, today.year, today.year + 1):
            try: dt = datetime.date(y, mo, d)
            except ValueError: continue
            if today - datetime.timedelta(days=60) <= dt <= today + datetime.timedelta(days=305): break
        else: continue
        label = ""
        if i > 0 and not DATE.search(lines[i - 1]) and not parse_range(lines[i - 1]) and len(lines[i - 1]) < 40:
            label = lines[i - 1]
        key = dt.isoformat()
        if key in seen: continue
        seen.add(key)
        e = {"date": key}
        if label: e["label"] = label
        e.update(v); out.append(e)
    return sorted(out, key=lambda e: e["date"])

def build(html, today):
    lines = page_lines(html)
    weekly = parse_weekly(lines)
    problems = []
    for k in ("mon", "tuefri", "satsun"):
        if k not in weekly or not sane(weekly[k]): problems.append("weekly row missing or odd: " + k)
    hol = parse_holidays(lines, today)
    for e in hol:
        if not sane(e): problems.append("odd holiday hours: " + e["date"])
    return {"updated": today.isoformat(), "source": URL, "weekly": weekly, "holidays": hol}, problems

def main(argv):
    a = {}
    i = 1
    while i < len(argv):
        if argv[i].startswith("--"): a[argv[i][2:]] = argv[i + 1]; i += 2
        else: i += 1
    out = a.get("out", "hours.json")
    today = datetime.date.fromisoformat(a["today"]) if "today" in a else datetime.datetime.now(datetime.timezone.utc).date()
    if "file" in a:
        html = open(a["file"], encoding="utf-8", errors="replace").read()
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (compatible; AmberHubHoursBot/1.0; +https://github.com/SilverWolf5636/amber-msc-hub)", "Accept": "text/html"})
        try:
            html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        except Exception as e:
            print("FETCH FAILED (keeping the last good file):", e); return 0
    data, problems = build(html, today)
    if problems:
        print("PARSE LOOKS WRONG (keeping the last good file):"); [print(" -", p) for p in problems]; return 0
    try:
        old = json.load(open(out))
        future_old = [e for e in old.get("holidays", []) if e["date"] >= today.isoformat()]
        if future_old and not data["holidays"]:
            print("NO HOLIDAY ROWS FOUND but the old file had some (keeping the last good file)"); return 0
    except Exception:
        pass
    json.dump(data, open(out, "w"), indent=1); open(out, "a").write("\n")
    print("Wrote", out, "-", len(data["holidays"]), "holiday rows"); return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

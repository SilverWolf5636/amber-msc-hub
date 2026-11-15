#!/usr/bin/env python3
"""Daily MSC "coming up" events robot. Standard library only.

Reads the public Calendar of Events page ONCE (one page load, like a visitor), finds the
Special Events and Adult Events lists, and writes events.json (title, link, dates, times).
It never asks for anything else. If the page looks different from what it expects, it keeps
the last good events.json. It also writes events-debug.txt (public page text only) so a person
can see what the robot saw and fix the reading rules.

Usage: fetch_events.py [--out events.json] [--debug events-debug.txt] [--today YYYY-MM-DD] [--fixture page.html]
"""
import datetime, html, json, re, sys, urllib.request

PAGE = "https://www.mdsci.org/whats-happening/events/"
UA = "Mozilla/5.0 (compatible; AmberHubShowtimesBot/1.0; +https://github.com/SilverWolf5636/amber-msc-hub)"
MON = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
MNAME = {1: "Jan.", 2: "Feb.", 3: "Mar.", 4: "Apr.", 5: "May", 6: "June", 7: "July", 8: "Aug.", 9: "Sept.", 10: "Oct.", 11: "Nov.", 12: "Dec."}
DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})((?:\s*(?:,|and|&|–|—|-|to)\s*\d{1,2}\b(?!\s*(?::|am|pm|a\.m|p\.m|–|—|-\s*\d)))*)", re.I)
CLOCK = r"\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)"
RANGE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:–|—|-|to)\s*" + CLOCK, re.I)
ONE = re.compile(r"\b" + CLOCK, re.I)
LINK = re.compile(r"<a\b[^>]*?href=[\"'](?:https?://(?:www\.)?mdsci\.org)?/events/([a-z0-9][a-z0-9-]*)/?[\"'][^>]*>(.*?)</a>", re.I | re.S)
MARK = re.compile(r"id=[\"']upcoming-(special|adult)-event[\"']", re.I)
GENERIC = {"learn more", "read more", "more info", "details", "buy tickets", "register", "tickets", "view event", "view details", "get tickets"}


class Abort(Exception):
    pass


def flat(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def tokens(body):
    """Page -> list of (kind, value): ('sec', 'Special'|'Adult'), ('ev', slug, title), ('txt', text)."""
    spots = []
    for m in MARK.finditer(body):
        spots.append((m.start(), "sec", m.group(1).capitalize()))
    for m in LINK.finditer(body):
        spots.append((m.start(), "ev", m.group(1), flat(m.group(2)), m.end()))
    spots.sort(key=lambda s: s[0])
    out, pos = [], 0
    for s in spots:
        if s[0] > pos:
            t = flat(body[pos:s[0]])
            if t:
                out.append(("txt", t))
        if s[1] == "sec":
            out.append(("sec", s[2])); pos = max(pos, body.find(">", s[0]) + 1 or s[0])
        else:
            out.append(("ev", s[2], s[3])); pos = max(pos, s[4])
    t = flat(body[pos:])
    if t:
        out.append(("txt", t))
    return out


def days_from(m, today):
    mon = MON[m.group(1).lower()[:3]]
    nums = [int(x) for x in re.findall(r"\d{1,2}", m.group(2) + " " + (m.group(3) or ""))]
    tail = m.group(3) or ""
    if re.search(r"[–—-]|\bto\b", tail) and len(nums) >= 2:
        nums = list(range(nums[0], nums[-1] + 1)) if 0 < nums[-1] - nums[0] < 14 else [nums[0], nums[-1]]
    out = []
    for d in nums:
        if not 1 <= d <= 31:
            continue
        y = today.year
        try:
            dt = datetime.date(y, mon, d)
            if dt < today - datetime.timedelta(days=60):
                dt = datetime.date(y + 1, mon, d)
        except ValueError:
            continue
        out.append(dt)
    return out


def parse(body, today):
    toks = tokens(body)
    sec, cur, order, events = "Special", None, [], {}
    for t in toks:
        if t[0] == "sec":
            sec = t[1]; cur = None
        elif t[0] == "ev":
            slug, title = t[1], t[2]
            if slug not in events:
                events[slug] = {"slug": slug, "title": "", "type": sec, "dts": [], "dates": [], "times": []}
                order.append(slug)
            cur = events[slug]
            if sec == "Adult":
                cur["type"] = "Adult"
            if title and title.lower() not in GENERIC and not cur["title"]:
                cur["title"] = title
        elif cur is not None:
            txt = t[1]
            if len(txt) > 90:
                txt = txt[:90]
            for m in DATE.finditer(txt):
                ds = days_from(m, today)
                if ds:
                    cur["dts"] += ds; cur["dates"].append(m.group(0).strip())
            rest = DATE.sub(" ", txt)
            tm = [m.group(0).strip() for m in RANGE.finditer(rest)]
            rest2 = RANGE.sub(" ", rest)
            tm += [m.group(0).strip() for m in ONE.finditer(rest2)]
            cur["times"] += tm
    rows, problems = [], []
    for slug in order:
        e = events[slug]
        title = e["title"] or slug.replace("-", " ").title()
        if not e["dts"]:
            problems.append("no date found for " + title); continue
        dts = sorted(set(e["dts"]))
        by = {}
        for d in dts:
            by.setdefault(d.month, []).append(d)
        dates = ["%s %s" % (MNAME[mo], ", ".join(str(x.day) for x in v)) for mo, v in sorted(by.items(), key=lambda kv: kv[1][0])]
        seen, times = set(), []
        for x in e["times"]:
            k = x.lower().replace(" ", "")
            if k not in seen:
                seen.add(k); times.append(x)
        rows.append({"title": title, "url": "https://www.mdsci.org/events/%s/" % slug, "type": e["type"],
                     "dates": "; ".join(dates), "times": " and ".join(times[:3]),
                     "first": dts[0].isoformat(), "last": dts[-1].isoformat(),
                     "days": [d.isoformat() for d in dts]})
    rows.sort(key=lambda r: (r["first"], r["title"]))
    return rows, problems, toks


def debug_text(body, toks, rows, problems, today):
    lines = ["Events robot debug, %s" % today.isoformat(), "page bytes: %d" % len(body),
             "section markers: %s" % [m.group(0) for m in MARK.finditer(body)],
             "event links: %d" % len(LINK.findall(body)), "events kept: %d" % len(rows)]
    lines += ["problem: " + p for p in problems]
    lines.append("--- parsed ---")
    lines += [json.dumps(r) for r in rows]
    lines.append("--- what the robot read (page text order, first 120 pieces from the first event link) ---")
    i = next((k for k, t in enumerate(toks) if t[0] in ("sec", "ev")), 0)
    for t in toks[i:i + 120]:
        lines.append(" | ".join(str(x)[:160] for x in t))
    return "\n".join(lines) + "\n"


def main(argv):
    a, i = {}, 1
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            a[argv[i][2:]] = argv[i + 1]; i += 2
        else:
            i += 1
    out, dbg = a.get("out", "events.json"), a.get("debug", "events-debug.txt")
    if "today" in a:
        today = datetime.date.fromisoformat(a["today"])
    else:
        try:
            from zoneinfo import ZoneInfo
            today = datetime.datetime.now(ZoneInfo("America/New_York")).date()
        except Exception:
            today = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date()
    try:
        if "fixture" in a:
            body = open(a["fixture"], encoding="utf-8").read()
        else:
            req = urllib.request.Request(PAGE, headers={"User-Agent": UA, "Accept": "text/html"})
            body = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        print("FETCH FAILED (keeping the last good file):", e); return 0
    rows, problems, toks = parse(body, today)
    open(dbg, "w", encoding="utf-8").write(debug_text(body, toks, rows, problems, today))
    if problems:
        print("SOME EVENTS HAD NO DATE (kept the rest):"); [print(" -", p) for p in problems[:10]]
    if not rows:
        print("NO EVENTS FOUND (keeping the last good events.json)"); return 0
    data = {"updated": today.isoformat(), "source": PAGE,
            "note": "Names, dates and times come from mdsci.org. Check before relying.", "events": rows}
    json.dump(data, open(out, "w", encoding="utf-8"), indent=1); open(out, "a").write("\n")
    print("Wrote", out, "-", len(rows), "events"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

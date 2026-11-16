#!/usr/bin/env python3
"""Daily MSC showtimes robot. Standard library only.

Reads the public Calendar of Events page the same way a visitor's browser does:
  1. one page load (to get the page's own one-time code), then
  2. the same two data requests the page makes for IMAX and Planetarium, per day.
It asks for today and the next 6 days, and waits 10 seconds between requests
(the pause MSC's robots.txt asks for). About 15 requests, about 2.5 minutes.

Writes showtimes.json only if the result looks sane. If anything looks wrong it
keeps the last good file. The page gives start times only, so runtimes are
looked up once from outside film listings (see RUNTIMES). Titles not on that list get an
ESTIMATE (see DEFAULT_DUR) and are marked "est": true, so the app can say so.

Usage: fetch_showtimes.py [--out showtimes.json] [--today YYYY-MM-DD] [--fixture file.json] [--delay 10]
  --fixture: read answers from a saved file instead of the network (for tests).
             Format: {"YYYY-MM-DD": {"imax-showings": [posts], "planetarium-showings": [posts]}}
"""
import datetime, html, json, re, sys, time, urllib.parse, urllib.request

PAGE = "https://www.mdsci.org/whats-happening/events/"
ALLOWED_HOST = "www.mdsci.org"
UA = "Mozilla/5.0 (compatible; AmberHubShowtimesBot/1.0; +https://github.com/SilverWolf5636/amber-msc-hub)"
DAYS = 7
CATEGORIES = [("imax-showings", "IMAX"), ("planetarium-showings", "Planetarium")]
DEFAULT_DUR = {"IMAX": 45, "Planetarium": 35}   # estimates, in minutes, for titles not listed below

# Runtimes in minutes, looked up Nov 15 2026 from outside listings (MSC's own pages give none).
# Where sources disagreed, the shorter one is used so staff are ready early.
#   Deep Sky 39-40 (BBFC, IMAX.com)         Penguins: A Love Story 40 (BBFC)
#   The Blue Angels 3D 46 (IMAX.com)         Coral Sea 40-45 (Royal BC Museum 40, Fernbank 45)
#   Wingsuit Flyers 3D 40 (Royal BC Museum)  One World One Sky: Big Bird's Adventure 25 (Smithsonian)
#   Two Small Pieces of Glass 23 (fddb.org)  Live Sky: live talk, no listing (estimate)
RUNTIMES_BY_TITLE = {
    "Deep Sky": 40,
    "Penguins: A Love Story": 40,
    "The Blue Angels 3D": 46,
    "Coral Sea": 40,
    "Wingsuit Flyers 3D": 40,
    "One World One Sky: Big Bird's Adventure": 25,
    "Two Small Pieces of Glass: The Amazing Telescope": 23,
}


def norm(t):
    t = re.sub(r"[^a-z0-9]+", "", html.unescape(str(t)).lower())
    return t[:-2] if t.endswith("3d") else t


RUNTIMES = {norm(k): v for k, v in RUNTIMES_BY_TITLE.items()}
TIME = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\s*$", re.I)


class Abort(Exception):
    pass


def to_hhmm(s):
    m = TIME.match(s or "")
    if not m:
        return None
    h12, mi = int(m.group(1)), int(m.group(2) or 0)
    if not 1 <= h12 <= 12 or mi > 59:
        return None
    h = h12 % 12 + (12 if m.group(3).lower() == "p" else 0)
    return "%02d:%02d" % (h, mi)


def clean_posts(posts, venue_hint):
    """Turn the page's data rows into app rows. Returns (rows, problems)."""
    rows, problems = [], []
    for p in posts or []:
        title = html.unescape(str(p.get("title", ""))).strip()
        venue = str(p.get("location", "")).strip()
        start = to_hhmm(p.get("start_time"))
        if venue not in DEFAULT_DUR:
            venue = venue_hint            # the request itself says which venue it is
        if not title or start is None:
            problems.append("odd row: %r" % (p.get("title"),))
            continue
        h = int(start[:2])
        if not 7 <= h <= 22:
            problems.append("odd time %s for %s" % (start, title))
            continue
        known = RUNTIMES.get(norm(title))
        row = {"title": title, "venue": venue, "start": start, "dur": known or DEFAULT_DUR[venue]}
        if not known:
            row["est"] = True
        rows.append(row)
    rows.sort(key=lambda r: (r["start"], r["venue"]))
    return rows, problems


class Net:
    """Polite network source: one request at a time, with a pause between."""
    def __init__(self, delay):
        self.delay = delay
        self.last = 0.0
        self.ajaxurl = None
        self.nonce = None

    def _wait(self):
        gap = self.delay - (time.time() - self.last)
        if self.last and gap > 0:
            time.sleep(gap)

    def _open(self, req):
        self._wait()
        try:
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        except Exception as e:
            raise Abort("request failed: %s" % e)
        finally:
            self.last = time.time()

    def start(self):
        body = self._open(urllib.request.Request(PAGE, headers={"User-Agent": UA, "Accept": "text/html"}))
        m = re.search(r"var\s+events_ajax\s*=\s*(\{.*?\});", body, re.S)
        if not m:
            raise Abort("could not find the page's data settings")
        try:
            cfg = json.loads(m.group(1))
            self.ajaxurl, self.nonce = cfg["ajaxurl"], cfg["nonce"]
        except Exception:
            raise Abort("page data settings look different")
        if urllib.parse.urlparse(self.ajaxurl).hostname != ALLOWED_HOST or not self.nonce:
            raise Abort("page data settings point somewhere unexpected")

    def day(self, date, category):
        data = urllib.parse.urlencode({"action": "mission_ajax_get_events_by_category",
                                       "nonce": self.nonce, "date": date, "category": category}).encode()
        req = urllib.request.Request(self.ajaxurl, data=data, headers={
            "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        txt = self._open(req)
        try:
            j = json.loads(txt)
            if not j.get("success"):
                raise ValueError("not successful")
            posts = j["data"]["posts"] if isinstance(j["data"], dict) else j["data"]
            if not isinstance(posts, list):
                raise ValueError("no list")
            return posts
        except Exception:
            raise Abort("answer for %s %s looks different" % (date, category))


class Fixture:
    def __init__(self, path):
        self.data = json.load(open(path, encoding="utf-8"))

    def start(self):
        pass

    def day(self, date, category):
        return self.data.get(date, {}).get(category, [])


def build(src, today):
    src.start()
    days, problems = {}, []
    for n in range(DAYS):
        d = (today + datetime.timedelta(days=n)).isoformat()
        rows = []
        for cat, venue in CATEGORIES:
            r, pr = clean_posts(src.day(d, cat), venue)
            rows += r
            problems += pr
        rows.sort(key=lambda r: (r["start"], r["venue"]))
        days[d] = rows
    out = {"updated": today.isoformat(), "source": PAGE,
           "note": "Start times come from mdsci.org. Runtimes come from outside film listings; rows marked est are estimates.",
           "days": days}
    return out, problems


def main(argv):
    a = {}
    i = 1
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            a[argv[i][2:]] = argv[i + 1]; i += 2
        else:
            i += 1
    out = a.get("out", "showtimes.json")
    if "today" in a:
        today = datetime.date.fromisoformat(a["today"])
    else:
        try:
            from zoneinfo import ZoneInfo
            today = datetime.datetime.now(ZoneInfo("America/New_York")).date()
        except Exception:
            today = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date()
    src = Fixture(a["fixture"]) if "fixture" in a else Net(float(a.get("delay", 10)))
    try:
        data, problems = build(src, today)
    except Abort as e:
        print("FETCH OR READ FAILED (keeping the last good file):", e); return 0
    if problems:
        print("SOME ROWS LOOKED WRONG (keeping the last good file):"); [print(" -", p) for p in problems[:10]]; return 0
    total = sum(len(v) for v in data["days"].values())
    est = sorted({r["title"] for v in data["days"].values() for r in v if r.get("est")})
    if est:
        print("TITLES WITH ESTIMATED RUNTIME (add to RUNTIMES_BY_TITLE):", "; ".join(est))
    try:
        old = json.load(open(out))
        if total == 0 and any(old.get("days", {}).values()):
            print("NO SHOWS FOUND but the old file had some (keeping the last good file)"); return 0
    except Exception:
        pass
    if total == 0:
        print("NO SHOWS FOUND at all (not writing a file)"); return 0
    json.dump(data, open(out, "w"), indent=1); open(out, "a").write("\n")
    print("Wrote", out, "-", total, "shows over", len(data["days"]), "days"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

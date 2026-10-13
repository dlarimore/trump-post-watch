#!/usr/bin/env python3
"""Trump Post Alert - cloud edition (runs on GitHub Actions every 5-15 minutes).

Each run: fetch Trump's newest Truth Social posts (Truth Social API, falling back to the
trumpstruth.org archive), score every new one (Market Heat 0-10, confrontation 0-5 + target,
SHOCK yes/no), push WATCH+ posts to the ntfy app on your phone, and append them to
alert_log.csv. state.json remembers what was already seen.

Env: NTFY_TOPIC (required, a GitHub secret), NTFY_SERVER (default https://ntfy.sh),
     PHONE_MIN_HEAT (default 3), MAX_AGE_MIN (default 180 - older posts are logged, not pushed).
"""
import csv
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trump_heat import heat, confront, is_shock, short_desc  # noqa: E402

TRUTH_API = "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses?exclude_replies=true&limit=40"
RSS_URL = "https://www.trumpstruth.org/feed"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
STATE = os.path.join(HERE, "state.json")
LOG = os.path.join(HERE, "alert_log.csv")
COLS = ["timestamp_et", "weekday", "detected_et", "source", "heat", "level", "topics", "conf", "target", "shock", "likes", "text", "url"]
PRIORITY = {"LOW": 2, "WATCH": 3, "HIGH": 4, "EXTREME": 5}
TAGS = {"LOW": "speech_balloon", "WATCH": "eyes", "HIGH": "warning", "EXTREME": "rotating_light"}


def to_et(dt_utc):
    y = dt_utc.year
    mar1 = datetime(y, 3, 1, tzinfo=timezone.utc)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7, hours=7)
    nov1 = datetime(y, 11, 1, tzinfo=timezone.utc)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7, hours=6)
    return (dt_utc + timedelta(hours=-4 if dst_start <= dt_utc < dst_end else -5)).replace(tzinfo=None)


def get(url, accept):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace").lstrip("﻿")


def strip_html(s):
    s = re.sub(r"<br\s*/?>|</p>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def fetch_truth():
    out = []
    for s in json.loads(get(TRUTH_API, "application/json")):
        src = s.get("reblog") or s
        text = strip_html(src.get("content", "")) or ("[video/image post]" if s.get("media_attachments") else "")
        if s.get("reblog"):
            text = "RT: " + text
        out.append({"id": str(s["id"]), "utc": datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")),
                    "text": text, "url": s.get("url") or "", "likes": s.get("favourites_count", "")})
    return out


def fetch_rss():
    root = ET.fromstring(get(RSS_URL, "application/rss+xml,application/xml"))
    out = []
    for it in root.iter("item"):
        oid = next((c.text for c in it if c.tag.endswith("originalId")), None)
        text = strip_html(it.findtext("description") or it.findtext("title") or "") or "[video/image post]"
        out.append({"id": str(oid or it.findtext("guid") or it.findtext("link")),
                    "utc": parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc),
                    "text": text, "url": it.findtext("link") or "", "likes": ""})
    return out


def push(topic, server, title, body, level, url):
    req = urllib.request.Request(f"{server.rstrip('/')}/{topic}", data=body.encode("utf-8"), method="POST")
    req.add_header("Title", title.encode("ascii", "replace").decode())
    req.add_header("Priority", str(PRIORITY[level]))
    req.add_header("Tags", TAGS[level])
    if url:
        req.add_header("Click", url)
    urllib.request.urlopen(req, timeout=20).read()


def main():
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
    min_heat = int(os.environ.get("PHONE_MIN_HEAT", "3"))
    max_age = int(os.environ.get("MAX_AGE_MIN", "180"))
    if "--test" in sys.argv:
        push(topic, server, "TRUMP SHOCK 8/10 vs IRAN (4/5) - TEST", "Cloud watcher test - alerts are working.", "EXTREME", "")
        print("test push sent")
        return
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"seen": []}
    first = not st["seen"]
    posts, source = None, None
    for name, fn in (("TruthSocial", fetch_truth), ("trumpstruth.org", fetch_rss)):
        try:
            posts, source = fn(), name
            break
        except Exception as e:  # noqa: BLE001
            print(f"{name} unavailable: {str(e)[:120]}")
    if posts is None:
        print("no source reachable this run")
        return
    seen = set(st["seen"])
    keys = set(st.get("keys", []))
    now_et = to_et(datetime.now(timezone.utc))
    rows = []
    for p in sorted(posts, key=lambda x: x["utc"]):
        key = f'{p["utc"]:%Y%m%d%H%M}|{p["text"][:40]}'
        if p["id"] in seen or key in keys:
            continue
        seen.add(p["id"]); keys.add(key)
        if first:
            continue
        et = to_et(p["utc"])
        h, lvl, tops = heat(p["text"], et)
        c, who = confront(p["text"])
        sh = is_shock(h, c)
        tag = "/".join(tops) or "general"
        rows.append([f"{et:%Y-%m-%d %H:%M}", f"{et:%a}", f"{now_et:%Y-%m-%d %H:%M}", source, h, lvl, tag, c, who,
                     "Y" if sh else "N", p["likes"], p["text"][:500], p["url"]])
        age = (now_et - et).total_seconds() / 60
        print(f"{'SHOCK' if sh else lvl:7} {h}/10 conf {c} {who:20} age {age:.0f}m | {p['text'][:90]}")
        if topic and (h >= min_heat or sh) and age <= max_age:
            title = (f"TRUMP SHOCK {h}/10 vs {who} ({c}/5)" if sh else f"TRUMP {lvl} {h}/10 - {tag}") + f" - {et:%I:%M %p} ET"
            body = short_desc(p["text"], 60) + "\n\n" + p["text"][:350]
            if age >= 3:
                body += f"\n(posted {age:.0f} min ago - found via {source})"
            try:
                push(topic, server, title, body, "EXTREME" if sh else lvl, p["url"])
            except Exception as e:  # noqa: BLE001
                print("push failed:", e)
    if rows:
        new = not os.path.exists(LOG)
        with open(LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(COLS)
            w.writerows(rows)
    st = {"seen": sorted(seen)[-800:], "keys": sorted(keys)[-800:], "last_run_et": f"{now_et:%Y-%m-%d %H:%M}", "source": source}
    json.dump(st, open(STATE, "w"), indent=0)
    print(f"{source}: {len(posts)} fetched, {len(rows)} new" + (" (first run - baseline only)" if first else ""))


if __name__ == "__main__":
    main()

"""Market Heat score for a Trump post: 0-10, how likely it is to move futures sharply.

Shared by trump_post_alert.py (live alerts), build_pine_radar.py (TradingView arrays)
and the Posting Clock PDF. Pure stdlib.

Score = topic weight (biggest single topic + 1 per extra topic, max 5)
      + action words (0-2: 'effective immediately', 'I have ordered', tariff %, deadlines)
      + intensity (0-1: mostly CAPS or '!!!')
      + timing (0-2: inside the market-mover windows / during the cash session)
      - discount (-2 for link-only or repost, -1 for 'previously posted' / pure praise)
Levels: 0-2 LOW, 3-4 WATCH, 5-6 HIGH, 7-10 EXTREME
"""
import re
from datetime import datetime

TOPICS = [
    # (label, weight, regex)
    ("IRAN/WAR",   4, r"\biran|hormuz|strike|bomb|annihilat|nuclear|missile|military action|ceasefire|\bwar\b"),
    ("TARIFFS",    4, r"tariff|trade deal|trade war|sanction|embargo|import tax|reciprocal"),
    ("FED/RATES",  4, r"\bfed\b|federal reserve|powell|interest rate|rate cut|\brates\b|basis points|treasury|bond"),
    ("OIL/ENERGY", 3, r"\boil\b|gasoline|gas prices|diesel|opec|barrel|refiner|energy|lng|pipeline"),
    ("CHINA",      3, r"china|chinese|\bxi\b|beijing|taiwan|rare earth"),
    ("RUSSIA/UKR", 3, r"russia|putin|ukrain|zelensk|kremlin"),
    ("MARKETS",    3, r"stock market|\bdow\b|nasdaq|s&p|\bstocks\b|crypto|bitcoin|dollar|recession|inflation|\bcpi\b|jobs report"),
    ("DEALS",      2, r"\bdeal\b|agreement|negotiat|talks|summit|productive discussions"),
    ("COMPANIES",  2, r"boeing|nvidia|apple|tesla|intel|exxon|chevron|amazon|google|microsoft|meta\b|u\.?s\.? steel|nippon"),
    ("CANADA/EU",  2, r"canada|carney|mexico|europe|\beu\b|european union"),
]
ACTION = r"effective immediately|i have (just )?(ordered|authorized|signed|directed|instructed|terminated|approved)|" \
         r"will be imposed|\d+\s?%|percent|deadline|by (monday|tuesday|wednesday|thursday|friday|saturday|sunday)|" \
         r"as of (today|tomorrow)|starting (today|tomorrow|monday)|i am (hereby )?(announcing|ordering|imposing)|breaking"
LINK_ONLY = r"^\s*(https?://\S+\s*)+$"
REPOST = r"^(rt:|retruth|↻)|previously posted|also posted"


def market_windows(dt_et: datetime) -> int:
    """Timing bonus from the Sep 7 - Oct 8, 2026 baseline (times ET)."""
    if dt_et is None:
        return 0
    m = dt_et.hour * 60 + dt_et.minute
    wd = dt_et.weekday()  # 0=Mon
    if wd >= 5:
        return 1  # weekend: gap risk into the Sunday 6pm ET open
    if 9 * 60 + 30 <= m < 16 * 60:
        bonus = 2   # cash session
    elif 7 * 60 + 30 <= m < 9 * 60 + 30 or 16 * 60 <= m < 18 * 60:
        bonus = 1   # pre-open / around the close and Globex reopen
    else:
        bonus = 0
    return bonus


def heat(text: str, dt_et: datetime = None):
    """Return (score 0-10, level, [topic labels])."""
    t = (text or "").strip()
    if not t:
        return 0, "LOW", []
    low = t.lower()
    hits = [(lab, w) for lab, w, rx in TOPICS if re.search(rx, low)]
    labels = [lab for lab, _ in hits]
    topic = 0
    if hits:
        topic = max(w for _, w in hits) + (len(hits) - 1)
        topic = min(topic, 5)
    action = min(2, len(re.findall(ACTION, low)))
    letters = [c for c in t if c.isalpha()]
    caps = sum(c.isupper() for c in letters) / max(1, len(letters))
    intensity = 1 if (caps > 0.5 and len(letters) > 20) or "!!!" in t else 0
    disc = 0
    if re.match(LINK_ONLY, t):
        disc = 2
    elif re.search(REPOST, low):
        disc = 1
    if re.search(r"complete and total endorsement|has my endorsement|will never let you down", low):
        disc = max(disc, 3)  # endorsements are not market movers
    score = topic + action + intensity + (market_windows(dt_et) if topic else 0) - disc
    score = max(0, min(10, score))
    level = "EXTREME" if score >= 7 else "HIGH" if score >= 5 else "WATCH" if score >= 3 else "LOW"
    return score, level, labels


if __name__ == "__main__":
    tests = [
        ("We are having productive discussions with the Islamic Republic of Iran.", datetime(2026, 10, 8, 12, 17)),
        ("IRAN CAN NOT HAVE A NUCLEAR WEAPON!!! President DJT", datetime(2026, 9, 26, 8, 18)),
        ("Interest Rates in the United States should be 1%, or less, because we are the Best Credit", datetime(2026, 9, 16, 16, 38)),
        ("Mike Rogers has my Complete and Total Endorsement to be the next U.S. Senator", datetime(2026, 9, 18, 14, 17)),
        ("Thank you Oklahoma! President DONALD J. TRUMP", datetime(2026, 10, 2, 18, 6)),
    ]
    for txt, dt in tests:
        print(heat(txt, dt), "|", txt[:60])


# ---------------------------------------------------------------- confrontation + SHOCK
# Who he is going after (first two found, in order of appearance) and how hard (0-5,
# same scale as the News Pulse confrontation meter).
TARGETS = [
    ("IRAN", r"\biran|tehran|ayatollah|irgc"),
    ("CHINA/XI", r"china|chinese|\bxi\b|beijing"),
    ("RUSSIA/PUTIN", r"russia|putin|kremlin"),
    ("UKRAINE/ZELENSKY", r"ukrain|zelensk"),
    ("CANADA/CARNEY", r"canada|carney|trudeau"),
    ("MEXICO", r"mexico|sheinbaum"),
    ("EU/EUROPE", r"\beu\b|european union|europe"),
    ("NATO", r"\bnato\b"),
    ("VENEZUELA", r"venezuela|maduro"),
    ("INDIA", r"\bindia|modi\b"),
    ("JAPAN", r"\bjapan"),
    ("NORWAY/NOBEL", r"norway|nobel|noble peace"),
    ("FED/POWELL", r"powell|federal reserve|\bthe fed\b"),
    ("MEDIA", r"new york times|\bnyt\b|\bcnn\b|msnbc|ms now|msdnc|politico|washington post|\babc\b|\bnbc\b|\bcbs\b|fox ?news|fake news|axios|artificial news"),
    ("DEMOCRATS", r"dumocrat|democrat|radical left|schumer|jeffries|pelosi|newsom|mamdani|biden|obama|kamala|harris|pritzker|hochul"),
    ("COURTS/DOJ", r"jack smith|\bjudge|supreme court|prosecutor|\bdoj\b|special counsel"),
    ("GOP RIVALS", r"tom cotton|rand paul|massie|karl rove|mcconnell|paul ryan|rino"),
]
CONF_TIERS = [
    (5, r"annihilat|obliterat|\bbomb|military action|wipe (them )?out|\bstrike(s)? on|total destruction|declare war"),
    (4, r"tariff|sanction|\bban\b|banned|arrest|prosecut|indict|terminat|cut off|investigat|\bsue\b|lawsuit|pay a big price|consequences|revok|\bcancel"),
    (3, r"loser|crook|deranged|corrupt|\bfake\b|disgrace|sleaze|scam|\bliar\b|\blies\b|dishonest|failing|traitor|dirty|incompetent|stupid|pathetic|nasty|hoax|trannie|lunatic|\bsick\b"),
    (2, r"\bbad\b|wrong|unfair|ripping (us )?off|taking advantage|terrible|weak|should be ashamed|stain"),
    (1, r"friend of mine|my friend"),
]


def confront(text: str):
    """Return (level 0-5, target label or '-')."""
    low = (text or "").lower()
    found = []
    for lab, rx in TARGETS:
        m = re.search(rx, low)
        if m:
            found.append((m.start(), lab))
    found.sort()
    target = "/".join(lab for _, lab in found[:2]) if found else "-"
    lvl = 0
    for tier, rx in CONF_TIERS:
        if re.search(rx, low):
            lvl = tier
            break
    if not found:
        lvl = min(lvl, 2) if lvl != 1 else 0   # a threat word with nobody named is not a confrontation
    return lvl, target


def is_shock(heat_score: int, conf_level: int) -> bool:
    """SHOCK = likely to move futures sharply: EXTREME heat, or HIGH heat with a threat, or a military threat."""
    return heat_score >= 7 or (heat_score >= 5 and conf_level >= 4) or (heat_score >= 3 and conf_level >= 5)


def short_desc(text: str, n: int = 40) -> str:
    t = re.sub(r"https?://\S+", "", text or "")
    t = re.sub(r"^(rt:\s*)", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -")
    words, out = t.split(" "), ""
    for w in words:
        if len(out) + len(w) + 1 > n:
            break
        out = (out + " " + w).strip()
    return out or t[:n]

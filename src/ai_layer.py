"""P7 / P10: the AI layer. Claude reads each new FOMC statement (plus the previous one and what the
core holds) and records ONE decision from a fixed menu. Decisions are hashed and sealed before use.

Menu: action in {hold, engine, safe, cash}; days in {5, 10, 20}.
'hold' = follow the rule. Others override the core for `days` trading days.
The decision file is append-only: one decision per statement, never edited.
"""
import hashlib
import json
import re
from datetime import date
from pathlib import Path
import requests
from .config import ROOT

FED = ROOT / "calls" / "fed"
DECISIONS = FED / "decisions.jsonl"
MENU_ACTIONS, MENU_DAYS = {"hold", "engine", "safe", "cash"}, {5, 10, 20}
CAL_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
UA = {"User-Agent": "alpha-trading-research-bot"}


def list_statements():
    """Statement URLs (monetary YYYYMMDDa.htm) from the Fed calendar page, newest first."""
    html = requests.get(CAL_URL, headers=UA, timeout=30).text
    links = sorted(set(re.findall(r"/newsevents/pressreleases/monetary(\d{8})a\.htm", html)), reverse=True)
    return [(d, f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{d}a.htm") for d in links]


def fetch_text(url):
    r = requests.get(url, headers=UA, timeout=30); r.encoding = "utf-8"; html = r.text
    body = re.search(r'<div class="col-xs-12 col-sm-8 col-md-8">(.*?)</div>', html, re.S)
    txt = re.sub(r"<[^>]+>", " ", body.group(1) if body else html)
    return re.sub(r"\s+", " ", txt).strip()


def redact(text):
    """fed_redact: mask dates, names and rates so the model cannot look up the outcome from memory."""
    t = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b[^.,;]*?\d{4}", "[DATE]", text)
    t = re.sub(r"\b(19|20)\d{2}\b", "[YEAR]", t)
    num = r"\d+(?:[-\s]\d/\d|\.\d+)?"
    t = re.sub(num + r"(?:\s*(?:to|-)\s*" + num + r")?\s*(?:percent|%)", "[RATE]", t)
    t = re.sub(r"\b\d+\s*\W\s*\d+ vote", "[N-M] vote", t)
    t = re.sub(r"\b[1-9]\s*/\s*[1-9]\b", "[FRAC]", t)
    t = re.sub(r"Voting for[^.]*\.", "Voting for [NAMES].", t)
    t = re.sub(r"\b[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+\b", "[NAME]", t)
    return t


def decided():
    if not DECISIONS.exists():
        return {}
    return {d["statement"]: d for d in map(json.loads, DECISIONS.read_text().splitlines())}


def record(statement_date, action, days, reason):
    """Append one sealed decision. Refuses duplicates and stale statements (> 5 business days)."""
    if action not in MENU_ACTIONS or int(days) not in MENU_DAYS:
        raise ValueError("decision outside the menu")
    if statement_date in decided():
        raise ValueError("already decided for this statement")
    import numpy as np
    sd = date(int(statement_date[:4]), int(statement_date[4:6]), int(statement_date[6:]))
    if np.busday_count(sd, date.today()) > 5:
        raise ValueError("statement older than 5 business days")
    rec = dict(statement=statement_date, decided_on=str(date.today()), action=action, days=int(days), reason=reason)
    rec["seal"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
    FED.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def verify(rec):
    r = {k: v for k, v in rec.items() if k != "seal"}
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest() == rec["seal"]


def active_override(today, trading_days):
    """Latest valid decision still in force on `today` (counted in trading days from the day after deciding)."""
    best = None
    for rec in decided().values():
        if not verify(rec) or rec["action"] == "hold":
            continue
        start = [d for d in trading_days if str(d.date()) > rec["decided_on"]]
        if start and start[0] <= today and today in start[:rec["days"]]:
            best = rec
    return best


if __name__ == "__main__":
    st = list_statements()[:2]
    for d, u in st:
        print(d, u)
    if st:
        print(redact(fetch_text(st[0][1]))[:600])

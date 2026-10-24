"""Zapis/odczyt stanu symulacji: JSON, CSV, JSONL. Tylko stdlib."""
from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime, timezone

from . import session as ses

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADER = os.path.join(ROOT, "trader")
STATE = os.path.join(ROOT, "sim", "state")
DOCS = os.path.join(ROOT, "docs")

for _d in (TRADER, os.path.join(TRADER, "state"), STATE, DOCS):
    os.makedirs(_d, exist_ok=True)


def p(*parts: str) -> str:
    return os.path.join(*parts)


def read_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read().strip()
    if not txt:
        return default
    return json.loads(txt)


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def append_jsonl(path: str, obj) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def append_csv(path: str, row: dict, header: list[str]) -> None:
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ny_stamp(now=None) -> str:
    return ses.now_ny(now).strftime("%Y-%m-%d %H:%M")


# --- sciezki w projekcie -----------------------------------------------------
SIM_JSON = p(STATE, "sim.json")
LEDGER = p(STATE, "ledger.csv")
DECISIONS = p(STATE, "decisions.jsonl")
EQUITY = p(STATE, "equity.csv")
TRADES = p(STATE, "trades.csv")
NEWS_STATE = p(STATE, "news.json")
PORTFOLIO = p(TRADER, "portfolio.json")          # konto USD (format skilla)
CONFIG = p(TRADER, "config.json")                # limity skilla (USD)
PLAN = p(TRADER, "plan.json")
ENTRY = p(TRADER, "entry.json")
ORDERS = p(TRADER, "orders.json")
PRICES = p(TRADER, "prices.json")
WATCHLIST = p(TRADER, "watchlist.json")
RISK_STATE = p(TRADER, "state", "risk.json")
BROKER_STATE = p(TRADER, "state", "broker.json")
SIM_CONFIG = p(ROOT, "sim", "config.json")
UNIVERSE = p(ROOT, "universe.txt")
SPOLKI = p(ROOT, "data", "spolki.csv")          # katalog: nazwa i kategoria

LEDGER_COLS = [
    "ts_ny", "event", "symbol", "qty", "price_usd", "notional_usd",
    "fee_usd", "cash_usd_after", "equity_usd", "note",
]
TRADE_COLS = [
    "open_ts_ny", "close_ts_ny", "symbol", "qty", "entry_usd", "exit_usd",
    "pnl_usd", "ret_pct", "r_multiple", "exit_reason", "setup", "hold_min",
]

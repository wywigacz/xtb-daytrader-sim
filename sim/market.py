"""Dane rynkowe z darmowego Yahoo (nieoficjalne, opoznione). Tylko stdlib.

To ten sam endpoint, z ktorego korzysta skill day-trader-skill
(query2.finance.yahoo.com/v8/finance/chart). Tu mamy wlasny, lekki klient,
zeby silnik symulacji nie zalezal od wewnetrznej logiki skilla.
"""
from __future__ import annotations

import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sim import session as ses
else:
    from . import session as ses

UA = "xtb-daytrader-sim/1.0 (+github.com; symulacja edukacyjna)"
HOSTS = ("query2.finance.yahoo.com", "query1.finance.yahoo.com")


class MarketError(RuntimeError):
    pass


def _get(path: str, params: dict, retries: int = 3, timeout: int = 20) -> dict:
    qs = urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        for host in HOSTS:
            url = "https://%s%s?%s" % (host, path, qs)
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": UA,
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                    },
                )
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return json.loads(raw.decode("utf-8", "replace"))
            except urllib.error.HTTPError as e:
                last = "HTTP %s %s" % (e.code, host)
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(2 + attempt * 2)
                    continue
                break
            except Exception as e:  # noqa: BLE001
                last = "%s %s" % (type(e).__name__, host)
        time.sleep(1 + attempt)
    raise MarketError("Yahoo nie odpowiedzialo (%s)" % last)


def _parse_chart(doc: dict, symbol: str) -> dict:
    chart = (doc.get("chart") or {})
    if chart.get("error"):
        raise MarketError("Yahoo: %s dla %s" % (chart["error"].get("description"), symbol))
    res = (chart.get("result") or [None])[0]
    if not res:
        raise MarketError("Yahoo: brak danych dla %s" % symbol)
    ts = res.get("timestamp") or []
    q = (((res.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    meta = res.get("meta") or {}
    bars = []
    for i, t in enumerate(ts):
        try:
            o = q["open"][i]
            h = q["high"][i]
            lo = q["low"][i]
            c = q["close"][i]
        except (KeyError, IndexError):
            continue
        if None in (o, h, lo, c):
            continue
        v = None
        try:
            v = q["volume"][i]
        except (KeyError, IndexError):
            v = None
        bars.append(
            {
                "t": int(t),
                "ny": ses.to_ny(int(t)).isoformat(),
                "o": float(o),
                "h": float(h),
                "l": float(lo),
                "c": float(c),
                "v": float(v) if v is not None else None,
            }
        )
    return {"symbol": symbol.upper(), "meta": meta, "bars": bars}


def chart(symbol: str, rng: str = "1d", interval: str = "5m") -> dict:
    doc = _get(
        "/v8/finance/chart/" + urllib.parse.quote(symbol.upper()),
        {
            "range": rng,
            "interval": interval,
            "includePrePost": "false",
            "events": "div,split",
        },
    )
    return _parse_chart(doc, symbol)


def bars(symbol: str, rng: str = "1d", interval: str = "5m") -> list[dict]:
    return chart(symbol, rng, interval)["bars"]


def bars_for_day(symbol: str, day: date, interval: str = "5m") -> list[dict]:
    out = []
    for b in bars(symbol, "5d" if interval != "1d" else "1y", interval):
        if ses.to_ny(b["t"]).date() == day:
            out.append(b)
    out.sort(key=lambda b: b["t"])
    return out


def last_price(symbol: str) -> tuple[float, float]:
    """(cena, znacznik czasu epoch). Bierze ostatnia niepusta swiece 5m."""
    doc = chart(symbol, "1d", "5m")
    bs = doc["bars"]
    if not bs:
        mp = doc["meta"].get("regularMarketPrice")
        if mp:
            return float(mp), float(doc["meta"].get("regularMarketTime") or time.time())
        raise MarketError("brak ceny dla %s" % symbol)
    return bs[-1]["c"], bs[-1]["t"]


def fx_usdpln() -> float:
    """Kurs USD/PLN z Yahoo (symbol PLN=X). Fallback: 3.65."""
    for sym in ("PLN=X", "USDPLN=X"):
        try:
            doc = chart(sym, "5d", "1d")
            if doc["bars"]:
                return float(doc["bars"][-1]["c"])
        except Exception:  # noqa: BLE001
            continue
    return 3.65


def daily_closes(symbol: str, rng: str = "3mo") -> list[tuple[date, float]]:
    out = []
    for b in bars(symbol, rng, "1d"):
        out.append((ses.to_ny(b["t"]).date(), b["c"]))
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sim import market as _m

    sym = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    b = _m.bars(sym, "1d", "5m")
    print("%s: %d swiec 5m" % (sym, len(b)))
    for x in b[-4:]:
        print("  ", x["ny"], x["c"])
    print("USD/PLN:", _m.fx_usdpln())

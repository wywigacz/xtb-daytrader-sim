"""Lejek decyzji + obserwacje z wlasnych transakcji ("czego bot sie nauczyl").

Uczciwie: to NIE jest uczenie maszynowe. To zwykla statystyka z dziennika
wlasnych transakcji. Pokazujemy tylko wnioski, na ktore sa dane (n >= 5),
a przy mniejszej probie mowimy wprost "za malo danych".
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from . import store

MIN_N = 5


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _read_decisions() -> list[dict]:
    import os
    if not os.path.exists(store.DECISIONS):
        return []
    out = []
    with open(store.DECISIONS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def funnel(sim: dict) -> dict:
    """Lejek: ile swiata -> ile obserwowanych -> ile sygnalow -> ile transakcji."""
    dec = _read_decisions()
    trades = store.read_csv(store.TRADES)
    scans = [d for d in dec if d.get("decision") == "scan" and d.get("scanned")]
    last_scan = scans[-1] if scans else {}
    universe = 0
    try:
        with open(store.UNIVERSE, encoding="utf-8") as f:
            universe = len([l for l in f if l.strip() and not l.startswith("#")])
    except OSError:
        pass
    opens = [d for d in dec if d.get("decision") == "open"]
    skips = [d for d in dec if d.get("decision") == "skip"]
    blocks = [d for d in dec if d.get("decision") == "block"]
    reads = sum(int(d.get("read") or 0) for d in dec if d.get("decision") == "news")
    return {
        "universe_usa": 5943,           # tyle spolki USA widzi skaner skilla
        "watched": universe or last_scan.get("scanned") or 0,
        "scanned": int(last_scan.get("scanned") or 0),
        "hits": int(last_scan.get("hits") or 0),
        "signals_total": sum(int(d.get("hits") or 0) for d in scans),
        "checked": len(opens) + len(skips) + len(blocks),
        "opened": len(opens),
        "skipped": len(skips),
        "blocked": len(blocks),
        "trades": len(trades),
        "news_read": reads,
    }


def observations(sim: dict) -> list[dict]:
    """Lista obserwacji: {title, text, value, tone, n}."""
    trades = store.read_csv(store.TRADES)
    out: list[dict] = []
    n = len(trades)
    if n == 0:
        return out

    pnl = [_f(t.get("pnl_usd")) for t in trades]
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]

    # 1. Skutecznosc
    wr = len(wins) / n * 100
    sr = sum(pnl) / n
    out.append({
        "title": "Skutecznosc",
        "value": "%.0f%%" % wr,
        "text": ("Na %d transakcji %d wyszlo na plus. Sredni wynik jednej transakcji: %+.0f USD."
                 % (n, len(wins), sr)),
        "tone": "up" if sum(pnl) > 0 else "down",
        "n": n,
    })

    # 2. Jak koncza sie transakcje
    reasons = Counter((t.get("exit_reason") or "-") for t in trades)
    parts = []
    for code, label in (("target", "cel"), ("stop", "stop"), ("flat_by", "koniec dnia"), ("eod_flat", "awaryjnie")):
        if reasons.get(code):
            parts.append("%d %s" % (reasons[code], label))
    if parts:
        top = reasons.most_common(1)[0]
        out.append({
            "title": "Jak koncza sie transakcje",
            "value": "%d z %d" % (reasons.get("target", 0), n),
            "text": "Rozstrzygniecia: %s. Najczestszy scenariusz: %s." % (
                ", ".join(parts), {"target": "cel", "stop": "stop", "flat_by": "koniec dnia",
                                   "eod_flat": "awaryjne domkniecie"}.get(top[0], top[0])),
            "tone": "up" if reasons.get("target", 0) > reasons.get("stop", 0) else "down",
            "n": n,
        })

    # 3. R multiple
    rs = [_f(t.get("r_multiple"), None) for t in trades]
    rs = [r for r in rs if r is not None]
    if len(rs) >= MIN_N:
        avg_r = sum(rs) / len(rs)
        out.append({
            "title": "Sredni wynik w jednostkach ryzyka",
            "value": "%+.2f R" % avg_r,
            "text": ("1R = tyle, ile bylem gotow stracic na jednej transakcji. "
                     "Srednio wychodze na %s." % ("plus" if avg_r > 0 else "minus")),
            "tone": "up" if avg_r > 0 else "down",
            "n": len(rs),
        })

    # 4. Pora dnia
    buckets = defaultdict(list)
    for t in trades:
        ts = str(t.get("open_ts_ny") or "")
        try:
            h = int(ts[11:13])
        except ValueError:
            continue
        key = "rano (do 11:00)" if h < 11 else ("w poludnie (11-13)" if h < 13 else "po poludniu (po 13)")
        buckets[key].append(_f(t.get("pnl_usd")))
    usable = {k: v for k, v in buckets.items() if len(v) >= 3}
    if len(usable) >= 2:
        best = max(usable.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        worst = min(usable.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        out.append({
            "title": "Pora dnia ma znaczenie",
            "value": best[0].split(" ")[0],
            "text": ("Najlepiej wychodza mi wejscia %s (srednio %+.0f USD), najgorzej %s (%+.0f USD)."
                     % (best[0], sum(best[1]) / len(best[1]), worst[0], sum(worst[1]) / len(worst[1]))),
            "tone": "up",
            "n": sum(len(v) for v in usable.values()),
        })

    # 5. Najlepsza i najgorsza spolka
    per = defaultdict(list)
    for t in trades:
        per[str(t.get("symbol") or "")].append(_f(t.get("pnl_usd")))
    if len(per) >= 3:
        best = max(per.items(), key=lambda kv: sum(kv[1]))
        worst = min(per.items(), key=lambda kv: sum(kv[1]))
        out.append({
            "title": "Ktore spolki mi sluza",
            "value": best[0],
            "text": "%s dal mi %+.0f USD, %s %+.0f USD." % (
                best[0], sum(best[1]), worst[0], sum(worst[1])),
            "tone": "up" if sum(best[1]) >= 0 else "down",
            "n": len(per),
        })

    # 6. Jak wybiorczy jestem
    f = funnel(sim)
    if f["opened"]:
        ratio = (f["skipped"] + f["blocked"]) / f["opened"]
        out.append({
            "title": "Jak czesto odpuszczam",
            "value": "%.1f : 1" % ratio,
            "text": ("Na kazda otwarta pozycje przypadaja %.1f odrzucone okazje. "
                     "Wybiórczosc jest czescia metody, nie awaria." % ratio),
            "tone": "neutral",
            "n": f["checked"],
        })
    return out


def skipped_reasons(sim: dict, limit: int = 5) -> list[dict]:
    """Najczestsze powody odpuszczenia - do sekcji 'dlaczego nie kupil'."""
    dec = [d for d in _read_decisions() if d.get("decision") in ("skip", "block")]
    cnt = Counter((d.get("code") or "inne") for d in dec)
    titles = {}
    for d in dec:
        titles.setdefault(d.get("code") or "inne", d.get("title") or "Odrzucone")
    return [{"code": c, "title": titles.get(c, c), "count": n}
            for c, n in cnt.most_common(limit)]


def today_actions(sim: dict) -> list[dict]:
    """Os czasu dzisiejszych dzialan: chronologicznie, max 10 wpisow.

    Pomijamy drobnice (kursy walut, powtarzane "odpuszczam bo brak miejsca"),
    zeby os byla czytelna, a nie byla sciana tekstu.
    """
    day = store.ny_stamp()[:10]
    keep = {"deposit", "scan", "open", "close", "block", "scan_empty", "news_summary"}
    dec = [d for d in _read_decisions()
           if str(d.get("ts_ny", "")).startswith(day) and d.get("decision") in keep]
    dec.sort(key=lambda d: str(d.get("ts_ny")))
    if len(dec) > 10:
        # jesli za duzo - zostaw najwazniejsze typy, potem najnowsze
        prio = {"deposit": 0, "open": 0, "close": 0, "news_summary": 1, "block": 2, "scan": 3, "scan_empty": 4}
        dec.sort(key=lambda d: (prio.get(d.get("decision"), 9), str(d.get("ts_ny"))))
        dec = dec[:10]
        dec.sort(key=lambda d: str(d.get("ts_ny")))
    out = []
    for d in dec:
        out.append({
            "time": str(d.get("ts_ny", ""))[11:16],
            "kind": d.get("decision"),
            "title": d.get("title") or "",
            "why": d.get("why") or "",
            "symbol": d.get("symbol") or "",
            "numbers": d.get("numbers") or {},
        })
    return out

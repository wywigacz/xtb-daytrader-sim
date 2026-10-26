"""Lejek decyzji + obserwacje z własnych transakcji ("czego bot się nauczył").

Uczciwie: to NIE jest uczenie maszynowe. To zwykla statystyka z dziennika
własnych transakcji. Pokazujemy tylko wnioski, na które są dane (n >= 5),
a przy mniejszej probie mowimy wprost "za mało danych".
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
    """Lejek: ile swiata -> ile obserwowanych -> ile sygnałów -> ile transakcji."""
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
        "title": "Trafione zakupy",
        "value": "%.0f%%" % wr,
        "text": ("%d z %d zakupów na plus. Średnio jeden zakup: %+.0f USD."
                 % (len(wins), n, sr)),
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
            "title": "Jak kończą się zakupy",
            "value": "%d z %d" % (reasons.get("target", 0), n),
            "text": "Najczęściej: %s." % {
                "target": "cel", "stop": "stop", "flat_by": "koniec dnia",
                "eod_flat": "domknięcie awaryjne"}.get(top[0], top[0]),
            "tone": "up" if reasons.get("target", 0) > reasons.get("stop", 0) else "down",
            "n": n,
        })

    # 3. R multiple
    rs = [_f(t.get("r_multiple"), None) for t in trades]
    rs = [r for r in rs if r is not None]
    if len(rs) >= MIN_N:
        avg_r = sum(rs) / len(rs)
        out.append({
            "title": "Wynik na tle ryzyka",
            "value": ("%+.2f razy" % avg_r).replace(".", ","),
            "text": "Ile zarabiam na złotówkę, którą ryzykowałem.",
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
            "title": "Pora dnia",
            "value": best[0].split(" ")[0],
            "text": ("Najlepiej %s (%+.0f USD), najgorzej %s (%+.0f USD)."
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
            "title": "Spółki, które się wyróżniły",
            "value": best[0],
            "text": "Najlepiej %s (%+.0f USD), najgorzej %s (%+.0f USD)." % (
                best[0], sum(best[1]), worst[0], sum(worst[1])),
            "tone": "up" if sum(best[1]) >= 0 else "down",
            "n": len(per),
        })

    # 6. Jak wybiorczy jestem
    f = funnel(sim)
    if f["opened"]:
        ratio = (f["skipped"] + f["blocked"]) / f["opened"]
        out.append({
            "title": "Ile okazji odpuszczam",
            "value": ("%.1f na 1" % ratio).replace(".", ","),
            "text": "%s odrzuconych na 1 zakup." % ("%.1f" % ratio).replace(".", ","),
            "tone": "neutral",
            "n": f["checked"],
        })
    return out


def skipped_reasons(sim: dict, limit: int = 5) -> list[dict]:
    """Najczestsze powody odpuszczenia - do sekcji 'dlaczego nie kupił'."""
    dec = [d for d in _read_decisions() if d.get("decision") in ("skip", "block")]
    cnt = Counter((d.get("code") or "inne") for d in dec)
    titles = {}
    for d in dec:
        titles.setdefault(d.get("code") or "inne", d.get("title") or "Odrzucone")
    return [{"code": c, "title": titles.get(c, c), "count": n}
            for c, n in cnt.most_common(limit)]


def today_actions(sim: dict) -> list[dict]:
    """Os czasu dzisiejszych działań: chronologicznie, max 10 wpisow.

    Pomijamy drobnice (kursy walut, powtarzane "odpuszczam bo brak miejsca"),
    żeby os była czytelna, a nie była sciana tekstu.
    """
    day = store.ny_stamp()[:10]
    keep = {"deposit", "scan", "open", "close", "block", "scan_empty", "news_summary",
            "tax_due", "tax_paid", "error"}
    dec = [d for d in _read_decisions()
           if str(d.get("ts_ny", "")).startswith(day) and d.get("decision") in keep]

    # Odrzucenia zbiorczo po powodzie: 29 razy "cena juz odjechala" to jedna
    # linia z liczba, a nie 29 linii. Inaczej os czasu zamienia sie w sciane.
    from . import plain
    agg: dict[str, dict] = {}
    rest = []
    for d in dec:
        if d.get("decision") == "block":
            code = d.get("code") or "inne"
            slot = agg.setdefault(code, {"code": code, "count": 0, "symbols": [], "time": str(d.get("ts_ny"))})
            slot["count"] += 1
            sym = d.get("symbol")
            if sym and sym not in slot["symbols"]:
                slot["symbols"].append(sym)
            slot["time"] = str(d.get("ts_ny"))
        else:
            rest.append(d)
    blocks = []
    for slot in sorted(agg.values(), key=lambda s: -s["count"])[:2]:
        blocks.append({
            "time": slot["time"][11:16],
            "kind": "block",
            "title": "Odpuściłem %d okazj%s: %s" % (
                slot["count"],
                "e" if slot["count"] == 1 else "i",
                plain.title_for(slot["code"]).lower()),
            "why": "%s Sprawdzone spółki: %s." % (
                plain.meaning_for(slot["code"]),
                ", ".join(slot["symbols"][:5]) if slot["symbols"] else "kilka"),
            "symbol": "",
            "numbers": {"ile": slot["count"], "kod": slot["code"]},
        })
    dec = rest
    dec.sort(key=lambda d: str(d.get("ts_ny")))
    if len(dec) > 8:
        prio = {"deposit": 0, "open": 0, "close": 0, "tax_due": 0, "tax_paid": 0, "error": 0,
                "news_summary": 1, "scan": 2, "scan_empty": 3}
        dec.sort(key=lambda d: (prio.get(d.get("decision"), 9), str(d.get("ts_ny"))))
        dec = dec[:8]
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
    out = out + blocks
    out.sort(key=lambda x: x.get("time") or "")
    return out

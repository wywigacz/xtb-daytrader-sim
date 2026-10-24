"""Warstwa wiadomości: ile bot przeczytal, co z tego wynika, czy zmienilo decyzje.

Zrodlo: narzędzie trader-news że skilla (nagłówki Yahoo Finance + ruchy ceny).
Nie wymyslam wiadomości - biorę to, co realnie wroci z feedu, i zapisuje
zbiorczo na dany dzień w sim/state/news.json, żeby panel miał co pokazać.
"""
from __future__ import annotations

import os

from . import skilltools, store

RISK_TAGS = {
    "earnings": ("wyniki", "Publikacja wyników finansowych"),
    "legal": ("prawo", "Sprawa sadowa lub regulacyjna"),
    "regulatory": ("regulacje", "Decyzja urzedu lub regulatora"),
    "risk": ("ryzyko", "Sygnał ryzyka w spolce"),
    "halt": ("wstrzymanie", "Handel wstrzymany"),
    "capital": ("finansowanie", "Emisja akcji lub zmiana finansowania"),
    "deal": ("transakcja", "Fuzja, przejecie lub duża umowa"),
    "people": ("zarzad", "Zmiana w zarzadzie"),
    "analyst": ("analitycy", "Zmiana rekomendacji"),
    "macro": ("makro", "Tlo gospodarcze"),
}

# Twardy powod odpuszczenia: wstrzymanie handlu albo naglowek o realnym
# wstrzasie. Samo slowo "earnings" NIE wystarcza - w sezonie wynikow takie
# naglowki sa wszedzie i blokowalyby caly handel (sprawdzone: 0 transakcji).
HARD_TAGS = {"halt"}
HARD_TITLE = (
    "halted", "trading halt", "halts trading", "bankruptcy", "chapter 11",
    "sec probe", "sec investigation", "accounting irregularit", "fraud",
    "guidance cut", "cuts guidance", "profit warning", "recall",
    "plunge", "plunges", "crashes", "slumps", "tumbles",
    "downgrade to sell", "suspends", "resigns", "restatement",
)

TAG_PL = {k: v[0] for k, v in RISK_TAGS.items()}


def _classify(item: dict) -> tuple[bool, str, list[str]]:
    tags = [str(t).lower() for t in (item.get("tags") or [])]
    labels = [TAG_PL.get(t, t) for t in tags]
    title = str(item.get("title") or "").lower()
    hard = [t for t in tags if t in HARD_TAGS]
    for w in HARD_TITLE:
        if w in title:
            hard.append(w)
            break
    if not tags:
        for kw, tag in (("earnings", "earnings"), ("lawsuit", "legal"), ("downgrade", "analyst"),
                        ("upgrade", "analyst"), ("offering", "capital"), ("halted", "halt")):
            if kw in title:
                tags.append(tag)
                labels.append(TAG_PL.get(tag, tag))
    return bool(hard), " ".join(sorted(set(labels))) or "informacja", sorted(set(hard))


def fetch(symbols: list[str], hours: float = 24) -> dict:
    """Pobierz nagłówki dla podanych spółek. Pusty wynik = brak wiadomości."""
    symbols = [s.upper() for s in dict.fromkeys(symbols) if s]
    if not symbols:
        return {"items": [], "moves": [], "count": 0, "ok": True, "note": "brak spółek"}
    args = ["--tickers", *symbols[:6], "--hours", str(hours), "--no-sec", "--dry-run"]
    rc, doc, tail = skilltools.json_run("news", args, timeout=150)
    if not isinstance(doc, dict):
        return {"items": [], "moves": [], "count": 0, "ok": False,
                "note": (tail or "brak odpowiedzi feedu")[:200]}
    items = []
    for it in doc.get("items") or []:
        risk, label, hard = _classify(it)
        items.append({
            "ticker": str(it.get("ticker") or "").upper(),
            "title": str(it.get("title") or "").strip(),
            "source": str(it.get("source") or ""),
            "time": str(it.get("time") or ""),
            "link": str(it.get("link") or ""),
            "tags": label,
            "risk": risk,
            "risk_tags": hard,
        })
    return {
        "items": items,
        "moves": doc.get("moves") or [],
        "count": len(items),
        "ok": True,
        "note": "",
        "symbols": symbols,
    }


def record(sim: dict, doc: dict, impact: str = "", symbol: str = "") -> None:
    """Dopisz dzisiejsza lekture do sim/state/news.json (bez duplikatow)."""
    day = store.ny_stamp()[:10]
    db = store.read_json(store.NEWS_STATE) or {"days": {}}
    days = db.setdefault("days", {})
    slot = days.setdefault(day, {"items": [], "runs": 0, "read": 0, "blocked": 0})
    slot["runs"] = int(slot.get("runs") or 0) + 1
    known = {i.get("link") or i.get("title") for i in slot["items"]}
    for it in doc.get("items") or []:
        key = it.get("link") or it.get("title")
        if key in known:
            continue
        known.add(key)
        rec = dict(it)
        if symbol and rec.get("ticker") == symbol.upper():
            rec["impact"] = impact or "nie zmienil decyzji"
        slot["items"].append(rec)
    slot["read"] = len(slot["items"])
    if impact and impact != "nie zmienil decyzji":
        slot["blocked"] = int(slot.get("blocked") or 0) + 1
    # trzymamy 10 dni
    for old in sorted(days)[:-10]:
        days.pop(old, None)
    store.write_json(store.NEWS_STATE, db)


def today() -> dict:
    db = store.read_json(store.NEWS_STATE) or {"days": {}}
    return (db.get("days") or {}).get(store.ny_stamp()[:10]) or {"items": [], "runs": 0, "read": 0, "blocked": 0}


def read_count_today() -> int:
    return int(today().get("read") or 0)

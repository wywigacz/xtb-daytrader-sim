"""Research przed decyzją: co wiem o spółce, ZANIM ją kupię.

Korzysta z narzędzia `trader-analyst` z dołączonego skilla: czyta prawdziwe
raporty spółki ze SEC (przychody, marże, zysk netto, zysk na akcję, wzrost
rok do roku, data ostatniego raportu).

Efekt zapisujemy przy decyzji, żeby panel pokazywał CO ZOSTAŁO SPRAWDZONE,
a nie tylko "kupiłem". To liczby z raportów, nie prognoza i nie porada.
"""
from __future__ import annotations

import os

from . import skilltools

# SEC wymaga nagłówka z nazwą i adresem e-mail (inaczej odmawia: "requires a
# User-Agent with your name and email"). Nie wstawiam tu niczyjego prywatnego
# adresu, bo to publiczne repozytorium.
#
# Chcesz swój kontakt? Ustaw sekret SEC_USER_AGENT w repozytorium GitHub
# (Settings -> Secrets and variables -> Actions). Wtedy silnik uzyje Twojego,
# a w kodzie zostanie neutralny zapas.
# Uwaga: SEC odrzuca domeny typu users.noreply.github.com (HTTP 403).
UA = (os.environ.get("SEC_USER_AGENT") or "").strip() or \
     "xtb-daytrader-sim (symulacja) contact@example.com"

DEFAULTS = {
    "enabled": True,
    "require_profit": True,        # nie kupuję spółki, która ostatnio straciła pieniądze
    "max_revenue_drop_pct": -15.0,  # ...ani takiej, której przychody mocno spadły
    "max_symbols": 3,              # ile spółek badam w jednym dniu
}


def progi(cfg: dict) -> dict:
    out = dict(DEFAULTS)
    out.update(cfg.get("research") or {})
    return out


def facts(symbols: list[str], timeout: int = 200) -> dict[str, dict]:
    """{SYMBOL: {'entity': nazwa, 'last': ostatni kwartał, 'rows': [...]}}.

    Pusta odpowiedź nie jest błędem - SEC bywa niedostępne, a wtedy po prostu
    nie mamy badania i nie udajemy, że je mamy.
    """
    syms = [str(s).upper() for s in symbols if str(s).strip()]
    if not syms:
        return {}
    try:
        _rc, doc, _tail = skilltools.list_run(
            "analyst", syms + ["--user-agent", UA], timeout=timeout)
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, dict] = {}
    for item in (doc or []):
        if not isinstance(item, dict):
            continue
        sym = str(item.get("ticker") or "").upper()
        res = item.get("result") or {}
        rows = [r for r in (res.get("rows") or []) if r.get("revenue") is not None]
        if sym and rows:
            out[sym] = {"entity": res.get("entity") or sym, "last": rows[0], "rows": rows}
    return out


def opis(row: dict) -> tuple[str, dict]:
    """Z ostatniego raportu robi jedno zdanie i liczby dla panelu."""
    rev = row.get("revenue_yoy")
    eps = row.get("eps_yoy")
    nic = row.get("net_income")
    marza = row.get("net_margin")
    czesci = []
    if rev is not None:
        czesci.append("przychody %s%.0f%% r/r" % ("+" if rev >= 0 else "", rev))
    if marza is not None:
        czesci.append("marża zysku %.0f%%" % marza)
    if eps is not None:
        czesci.append("zysk na akcję %s%.0f%% r/r" % ("+" if eps >= 0 else "", eps))
    tekst = ("Ostatni raport (%s): %s." % (row.get("fiscal") or "?", ", ".join(czesci))
             if czesci else "Brak danych o ostatnim raporcie.")
    liczby = {}
    if rev is not None:
        liczby["przychody"] = "%s%.0f%% r/r" % ("+" if rev >= 0 else "", rev)
    if marza is not None:
        liczby["marża zysku"] = "%.0f%%" % marza
    if eps is not None:
        liczby["zysk na akcję"] = "%s%.0f%% r/r" % ("+" if eps >= 0 else "", eps)
    return tekst, liczby


def sprawdz(symbol: str, cfg: dict, cache: dict[str, dict] | None = None) -> dict:
    """Bada jedną spółkę. Zwraca {'dane', 'tekst', 'liczby', 'blokada', 'powod'}."""
    p = progi(cfg)
    if not p["enabled"]:
        return {"dane": {}, "tekst": "", "liczby": {}, "blokada": False, "powod": ""}
    box = cache if cache is not None else {}
    if symbol.upper() not in box:
        box.update(facts([symbol]))
    d = box.get(symbol.upper()) or {}
    if not d:
        return {"dane": {}, "tekst": "Nie udało się pobrać raportów spółki.",
                "liczby": {}, "blokada": False, "powod": ""}
    row = d["last"]
    tekst, liczby = opis(row)
    blokada, powod = False, ""
    nic = row.get("net_income")
    rev = row.get("revenue_yoy")
    if p["require_profit"] and nic is not None and float(nic) < 0:
        blokada, powod = True, "Ostatni kwartał zamknął się stratą."
    elif rev is not None and float(rev) < float(p["max_revenue_drop_pct"]):
        blokada, powod = True, "Przychody spadły o %.0f%% rok do roku." % float(rev)
    return {"dane": d, "tekst": tekst, "liczby": liczby, "blokada": blokada, "powod": powod}

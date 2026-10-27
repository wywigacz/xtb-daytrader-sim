"""Odtworzenie dnia po sesji — ratunek na gubione ticki.

Problem: GitHub nie gwarantuje uruchomień z harmonogramu. W poniedziałek
2026-10-26 w oknie wejść (13:45–15:30 UTC) nie odpalił się ANI JEDEN tick,
a metoda wchodzi rano — więc dzień przepadł bez śladu i wynik byłby zaniżony
nie przez reguły, a przez harmonogram.

Rozwiązanie: po zamknięciu giełdy pobieramy świece 5-minutowe z całego dnia,
znajdujemy te same sygnały, które zobaczyłby tick, i księgujemy te same
transakcje. Pozycje domyka `strategy.manage` na świecach dnia — ta sama logika
co na żywo, więc i wyjścia są identyczne.

Zasady są te same co na żywo: zakres otwarcia z pierwszych 15 minut, stop
w środku zakresu, cel 1×R, ryzyko z configu, limit dźwigni i wolnego depozytu.
Różni się tylko moment zapisu — i panel to pokazuje („odtworzone po sesji").

Ticki zostają jako dodatek: gdy zadziałają w oknie, ich transakcja jest
prawdziwa, a odtworzenie ją pomija (ten sam dzień i ta sama spółka).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import book, market, research, session as ses, skilltools, strategy, store  # noqa: E402

OR_MINUT = 15            # zakres otwarcia: pierwsze 15 minut sesji
SLIP = 0.0005            # poślizg na stronę (jak w ticku)


def zakres_otwarcia(bary: list[dict]) -> tuple[float, float] | None:
    """Szczyt i dół pierwszych 15 minut sesji (3 świece 5-minutowe)."""
    if not bary:
        return None
    start = int(bary[0]["t"])
    or_bary = [b for b in bary if int(b["t"]) < start + OR_MINUT * 60]
    if len(or_bary) < 3:
        return None
    gora = max(float(b["h"]) for b in or_bary)
    dol = min(float(b["l"]) for b in or_bary)
    return (gora, dol) if gora > dol else None


def sygnal(bary: list[dict], okno_od: str = "09:45", okno_do: str = "11:30") -> dict | None:
    """Pierwsza świeca, która zamknęła się NAD szczytem otwarcia, w oknie wejść."""
    zak = zakres_otwarcia(bary)
    if not zak:
        return None
    gora, dol = zak
    od = int(okno_od[:2]) * 60 + int(okno_od[3:5])
    do = int(okno_do[:2]) * 60 + int(okno_do[3:5])
    for i, b in enumerate(bary):
        ny = str(b.get("ny") or "")
        if len(ny) < 16:
            continue
        minuta = int(ny[11:13]) * 60 + int(ny[14:16])
        if minuta < od or minuta > do:
            continue
        if float(b["c"]) > gora:
            return {"idx": i, "cena": float(b["c"]), "godz": ny[11:16], "bar": b,
                    "gora": gora, "dol": dol,
                    "nad_szczytem": round((float(b["c"]) / gora - 1) * 100, 3)}
    return None


def _ile_akcji(sim: dict, cfg: dict, cena: float, r_akcja: float) -> tuple[int, dict]:
    """Ta sama reguła co na żywo: ryzyko z configu, limit dźwigni i wolnego depozytu."""
    rf = cfg["risk_from_equity"]
    mg = cfg.get("margin") or {}
    lev = max(float(mg.get("leverage") or 1.0), 1.0)
    kapital = strategy._kapital(sim)           # gotówka + wartość pozycji
    ryzyko = kapital * float(rf["max_loss_per_trade_pct"]) / 100.0
    limit_dzw = kapital * lev / cena
    wolne = kapital * lev * (1 - float(mg.get("min_free_margin_pct") or 0) / 100.0)
    ile = int(min(ryzyko / r_akcja, limit_dzw, wolne / cena))
    return max(ile, 0), {"kapitał_usd": round(kapital, 2), "ryzyko_usd": round(ryzyko, 2),
                         "sztuk": ile}


def _now(now):
    """Przyjmij datetime albo tekst "YYYY-MM-DD HH:MM" (wygodne w testach i z CLI)."""
    if isinstance(now, str):
        from datetime import datetime
        return datetime.strptime(now[:16], "%Y-%m-%d %H:%M")
    return now


def odtworz(sim: dict, cfg: dict, now=None) -> dict:
    """Odtwórz dzień, jeśli w oknie wejść nie było sprawdzenia rynku."""
    now_dt = ses.now_ny(_now(now))
    dzien = now_dt.date()
    wynik = {"dzien": dzien.isoformat(), "kupione": [], "odrzucone": [],
             "sprawdzone": 0, "stan": "ok"}

    if not ses.is_trading_day(dzien):
        wynik["stan"] = "dzien wolny"
        return wynik
    if ses.is_open(now_dt):
        wynik["stan"] = "sesja jeszcze trwa"
        return wynik
    zrobione = sim.setdefault("odtworzone_dni", [])
    if dzien.isoformat() in zrobione:
        wynik["stan"] = "juz odtworzone"
        return wynik

    okno = (cfg.get("entry") or {}).get("okno_wejsc") or ["09:45", "11:30"]
    granica = int((cfg["risk_from_equity"].get("max_trades_per_day") or 3))

    # 1. Sygnały z całego dnia (świece 5-minutowe).
    kandydaci = []
    for sym in store.spolki_universe():
        try:
            bary = market.bars(sym, "1d", "5m")
        except Exception:  # noqa: BLE001
            continue
        s = sygnal(bary, okno[0], okno[1])
        if s:
            kandydaci.append((sym, s))
    kandydaci.sort(key=lambda x: -x[1]["nad_szczytem"])
    wynik["sprawdzone"] = len(store.spolki_universe())

    if not kandydaci:
        book.decide(sim, "scan",
                    title="Przejrzałem rynek po sesji",
                    why="Żadna spółka nie zamknęła się nad porannym szczytem — nie było czego kupować.",
                    numbers={"sprawdzonych": wynik["sprawdzone"],
                             "sposób": "odtworzone z danych po sesji"})
        zrobione.append(dzien.isoformat())
        return wynik

    book.decide(sim, "scan",
                title="Przejrzałem %d spółek po sesji" % wynik["sprawdzone"],
                why="Ticki nie sprawdziły okna wejść (automat się nie uruchomił), więc szukałem "
                    "sygnałów w danych z całego dnia. Znalazłem %d." % len(kandydaci),
                numbers={"sprawdzonych": wynik["sprawdzone"], "sygnałów": len(kandydaci),
                         "najsilniejszy": kandydaci[0][0],
                         "sposób": "odtworzone z danych po sesji"})

    # 2. Kupno — te same bramki co na żywo.
    cache: dict = {}
    juz = {str(t.get("symbol")) for t in store.read_csv(store.TRADES)
           if str(t.get("open_ts_ny", "")).startswith(dzien.isoformat())}
    for sym, s in kandydaci:
        if len(wynik["kupione"]) >= granica:
            break
        if sym in (sim.get("open") or {}) or sym in juz:
            continue
        czas = _czas(s["bar"], now_dt)
        bad = research.sprawdz(sym, cfg, cache)
        if bad.get("blokada"):
            book.decide(sim, "skip", symbol=sym, code="badanie",
                        title="%s: badanie spółki wypadło słabo" % sym,
                        why="%s %s" % (bad.get("powod"), bad.get("tekst") or ""),
                        numbers=bad.get("liczby") or {})
            wynik["odrzucone"].append(sym)
            continue
        try:
            gate = strategy._news_gate(sim, sym, czas)
        except Exception:  # noqa: BLE001
            gate = {"blocked": False}
        if gate.get("blocked"):
            book.decide(sim, "block", symbol=sym, code="news",
                        title="%s: wiadomości wstrzymały zakup" % sym,
                        why="Wiadomości z tego dnia były ryzykowne — nie kupuję.",
                        numbers={"sprawdzonych": len(kandydaci)})
            wynik["odrzucone"].append(sym)
            continue

        stop = round((s["gora"] + s["dol"]) / 2.0, 4)
        if stop >= s["cena"]:
            book.decide(sim, "skip", symbol=sym, code="plan",
                        title="%s: stop nad ceną" % sym,
                        why="Plan nie miał sensu — stop wypadł nad ceną wejścia.")
            wynik["odrzucone"].append(sym)
            continue
        r_akcja = s["cena"] - stop
        cel = round(s["cena"] + r_akcja, 4)          # cel 1×R, jak na żywo
        ile, liczby = _ile_akcji(sim, cfg, s["cena"], r_akcja)
        if ile < 1:
            book.decide(sim, "block", symbol=sym, code="size",
                        title="%s: za mała pozycja" % sym,
                        why="Przy tym stopie nie da się kupić nawet jednej akcji w limicie straty.",
                        numbers=liczby)
            wynik["odrzucone"].append(sym)
            continue

        fill = round(s["cena"] * (1 + SLIP), 4)
        notional = ile * fill
        plan = {"stop": stop, "target": cel, "risk_per_share": round(r_akcja, 4),
                "setup": "orb", "flat_by": "15:55"}
        # Konto (gotówka + liczba akcji) zapisujemy TYM SAMYM narzędziem, które
        # później księguje sprzedaż - inaczej sprzedaż odmawia („portfolio holds 0").
        rc, out, err = skilltools.run(
            "ticket",
            ["fill", "--symbol", sym, "--side", "buy", "--qty", ile, "--price", fill,
             "--date", dzien.isoformat(), "--now", store.ny_stamp(czas)],
            timeout=60)
        if rc != 0:
            book.decide(sim, "error", symbol=sym,
                        title="Nie udało się zapisać kupna %s" % sym,
                        why="Konto nie przyjęło zapisu kupna — nie księguję pozycji.",
                        error=(err or out).strip()[:180])
            continue
        book.record_open(sim, sym, ile, fill, plan, notional, 0.0,
                         reason="ORB (odtworzone po sesji)", now=czas)
        book.decide(sim, "open", symbol=sym,
                    title="Kupiłem %s %s (po sesji)" % (ile, sym),
                    why="Cena zamknęła się nad porannym szczytem (%+.2f%% nad nim). "
                        "Automat nie sprawdził tego dnia okna wejść, więc kupno zapisuję "
                        "po sesji z danych." % s["nad_szczytem"],
                    numbers={"sztuk": ile, "cena": fill, "stop": stop, "cel": cel,
                             "ryzyko_na_akcję": round(r_akcja, 4),
                             "maks_strata": round(ile * r_akcja, 2),
                             "godzina_sygnału": s["godz"],
                             "badanie": bad.get("liczby") or {}})
        wynik["kupione"].append(sym)

    zrobione.append(dzien.isoformat())
    return wynik


def _czas(bar: dict, domyslnie):
    """Czas świecy (Nowy Jork) jako datetime — do znaczników transakcji."""
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(bar.get("ny") or ""))
    except ValueError:
        return domyslnie

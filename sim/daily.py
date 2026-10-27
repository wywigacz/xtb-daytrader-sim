"""Rozliczenie dzienne: po zamknieciu sesji USA.

  1. Domknij awaryjnie wszystko, co zostało otwarte (po ostatniej cenie).
  2. Zrob wycene i dopisz wiersz do historii kapitału.
  3. Zbuduj dashboard (GitHub Pages) i krótkie podsumowanie do logu.
Uruchamiany przez GitHub Actions po 16:00 ET (ok. 21:00-22:00 UTC).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import book, dashboard, engine, market, odtworz, session as ses, store, strategy


def _cli_now():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--now", help='zamroz zegar, np. "2026-10-23 10:20" (czas Nowego Jorku)')
    a, _rest = ap.parse_known_args()
    if a.now:
        os.environ["SIM_NOW"] = a.now
    return ses.now_ny()


def main() -> int:
    cfg = book.load_cfg()
    sim = engine.ensure_init(book.load_sim(), cfg)
    now = _cli_now()
    today = now.date()
    print("== ROZLICZENIE DZIENNE %s ==" % store.ny_stamp(now))

    if str(today) < str(sim["start_date"]):
        print("Symulacja startuje %s." % sim["start_date"])
        dashboard.build(sim, cfg)
        return 0
    if not ses.is_trading_day(today):
        print("Dzień wolny - tylko odswiezam dashboard.")
        dashboard.build(sim, cfg)
        return 0

    engine.refresh_fx(sim, cfg)
    if engine.maybe_deposit(sim, cfg, today):
        print("Wpłata: razem %.0f PLN" % sim["deposits_pln_total"])

    if sim.get("last_day") != str(today):
        sim["day_count"] = int(sim.get("day_count") or 0) + 1
        sim["last_day"] = str(today)

    # 0b. ODTWORZENIE DNIA — ratunek, gdy ticki nie sprawdzily okna wejsc.
    #     GitHub gubi uruchomienia z harmonogramu (2026-10-26: zero tickow w oknie),
    #     a metoda wchodzi rano. Tutaj szukamy tych samych sygnalow w danych z calego
    #     dnia. Musi byc PRZED krokiem 1: odtworzone pozycje domknie ten krok,
    #     na tych samych swiecach i ta sama logika wyjsc co na zywo.
    try:
        rec = odtworz.odtworz(sim, cfg, now)
        if rec.get("kupione"):
            print("  ODTWORZONE: kupione %s | sprawdzonych %d | odrzucone %s"
                  % (", ".join(rec["kupione"]), rec.get("sprawdzone") or 0,
                     ", ".join(rec["odrzucone"]) or "brak"))
        else:
            print("  Odtworzenie dnia: %s (sprawdzonych %d)"
                  % (rec.get("stan"), rec.get("sprawdzone") or 0))
    except Exception as e:  # noqa: BLE001
        print("  (odtwarzanie dnia przerwane: %s: %s)" % (type(e).__name__, e))
        book.decide(sim, "error", title="Nie udało się odtworzyć dnia",
                    why="Po sesji nie udało się policzyć sygnałów z danych. Nic nie kupiłem.",
                    error="%s: %s" % (type(e).__name__, str(e)[:180]))

    # 1. Domkniecie resztek (blad feedu nie moze przerwac rozliczenia dnia)
    try:
        closed = strategy.manage(sim, now, force_close_all=True)
    except Exception as e:  # noqa: BLE001
        closed = []
        print("  (domykanie resztek przerwane: %s: %s)" % (type(e).__name__, e))
        book.decide(sim, "error", title="Nie udało się domknac resztek",
                    why="Feed nie odpowiedzial. Sprobuje domknac przy następnym uruchomieniu.",
                    error="%s: %s" % (type(e).__name__, str(e)[:180]))
    for t in closed:
        print("  ZAMKNIETE (koniec dnia) %s %s @ %s | P&L %.2f USD (%s)" % (
            t["symbol"], t["qty"], t["exit_usd"], t["pnl_usd"], t["exit_reason"]))

    # 1b. Podsumowanie lektury dnia (ile naglowkow, czy cofnely decyzje)
    try:
        strategy.log_daily_news_summary(sim)
    except Exception as e:  # noqa: BLE001
        print("  (podsumowanie wiadomości pominięte: %s)" % e)

    # 2. Wycena
    m = engine.snapshot(sim, cfg)
    book.save_sim(sim)

    # 3. Podsumowanie
    trades = store.read_csv(store.TRADES)
    wins = [t for t in trades if float(t.get("pnl_usd") or 0) > 0]
    losses = [t for t in trades if float(t.get("pnl_usd") or 0) <= 0]
    dep = float(sim.get("deposits_pln_total") or 0)
    print("Wpłaty: %.0f PLN | Wartość: %.0f PLN | Zysk: %.0f PLN"%(
        dep, m["equity_pln"], m["equity_pln"] - dep))
    print("Transakcje: %d (wygrane %d / przegrane %d) | P&L USD %.2f | podatek do zapłaty %.2f PLN" % (
        len(trades), len(wins), len(losses), float(sim.get("realized_pnl_usd") or 0),
        float(sim.get("tax_reserve_pln") or 0)))
    print("Benchmark %s: %.0f PLN" % (cfg["benchmark"]["label"], float(m.get("bench_pln") or 0)))

    dashboard.build(sim, cfg)
    print("Dashboard: %s" % store.p(store.ROOT, "docs", "index.html"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Rozliczenie dzienne: po zamknieciu sesji USA.

  1. Domknij awaryjnie wszystko, co zostalo otwarte (po ostatniej cenie).
  2. Zrob wycene i dopisz wiersz do historii kapitalu.
  3. Zbuduj dashboard (GitHub Pages) i krotkie podsumowanie do logu.
Uruchamiany przez GitHub Actions po 16:00 ET (ok. 21:00-22:00 UTC).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import book, dashboard, engine, session as ses, store, strategy  # noqa: E402


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
        print("Dzien wolny - tylko odswiezam dashboard.")
        dashboard.build(sim, cfg)
        return 0

    engine.refresh_fx(sim, cfg)
    if engine.maybe_deposit(sim, cfg, today):
        print("Wplata: razem %.0f PLN" % sim["deposits_pln_total"])

    if sim.get("last_day") != str(today):
        sim["day_count"] = int(sim.get("day_count") or 0) + 1
        sim["last_day"] = str(today)

    # 1. Domkniecie resztek
    closed = strategy.manage(sim, now, force_close_all=True)
    for t in closed:
        print("  ZAMKNIETE (koniec dnia) %s %s @ %s | P&L %.2f USD (%s)" % (
            t["symbol"], t["qty"], t["exit_usd"], t["pnl_usd"], t["exit_reason"]))

    # 2. Wycena
    m = engine.snapshot(sim, cfg)
    book.save_sim(sim)

    # 3. Podsumowanie
    trades = store.read_csv(store.TRADES)
    wins = [t for t in trades if float(t.get("pnl_usd") or 0) > 0]
    losses = [t for t in trades if float(t.get("pnl_usd") or 0) <= 0]
    dep = float(sim.get("deposits_pln_total") or 0)
    print("Wplaty: %.0f PLN | Wartosc: %.0f PLN | Zysk: %.0f PLN"%(
        dep, m["equity_pln"], m["equity_pln"] - dep))
    print("Transakcje: %d (wygrane %d / przegrane %d) | P&L USD %.2f | podatek w rezerwie %.2f PLN" % (
        len(trades), len(wins), len(losses), float(sim.get("realized_pnl_usd") or 0),
        float(sim.get("tax_reserve_pln") or 0)))
    print("Benchmark %s: %.0f PLN" % (cfg["benchmark"]["label"], float(m.get("bench_pln") or 0)))

    dashboard.build(sim, cfg)
    print("Dashboard: %s" % store.p(store.ROOT, "docs", "index.html"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

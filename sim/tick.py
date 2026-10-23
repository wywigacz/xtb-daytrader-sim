"""Tick srodzienny: jedno uruchomienie w trakcie sesji USA.

Uruchamiany co ~15 minut przez GitHub Actions. Robi dwie rzeczy:
  1. ZARZADZA otwartymi pozycjami (stop / target / czas flat-by) po swiecach 5m.
  2. Jesli sa wolne miejsca, szuka JEDNEGO nowego wejscia wg metodyki skilla.
Na koniec robi wycene i zapisuje stan.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import book, dashboard, engine, market, session as ses, store, strategy  # noqa: E402


def _cli_now():
    """--now "YYYY-MM-DD HH:MM" (czas NY) zamraza zegar - do testow i odtwarzania."""
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
    print("== TICK %s ==" % store.ny_stamp(now))

    if str(today) > str(sim["end_date"]):
        print("Symulacja zakonczona %s. Nic nie robie." % sim["end_date"])
        return 0
    if str(today) < str(sim["start_date"]):
        print("Symulacja startuje %s. Nic nie robie." % sim["start_date"])
        return 0
    if not ses.is_trading_day(today):
        print("Dzien wolny (weekend/swieto). Nic nie robie.")
        return 0

    engine.refresh_fx(sim, cfg)
    if engine.maybe_deposit(sim, cfg, today):
        print("Wplata wykonana. Wplaty razem: %.0f PLN" % sim["deposits_pln_total"])

    if sim.get("last_day") != str(today):
        sim["day_count"] = int(sim.get("day_count") or 0) + 1
        sim["last_day"] = str(today)

    if not ses.is_open(now):
        print("Sesja zamknieta (%s). Zapisuje tylko stan." % store.ny_stamp(now))
        engine.snapshot(sim, cfg)
        book.save_sim(sim)
        return 0

    print("Sesja otwarta. Minut od otwarcia: %.0f" % ses.minutes_since_open(now))

    closed = strategy.manage(sim, now)
    for t in closed:
        print("  ZAMKNIETE %s %s @ %s | P&L %.2f USD (%s)" % (
            t["symbol"], t["qty"], t["exit_usd"], t["pnl_usd"], t["exit_reason"]))

    opened = strategy.try_enter(sim, now)
    if opened:
        p = opened["plan"]
        print("  OTWARTE %s %s @ %s | stop %s | target %s | ryzyko/akcja %s" % (
            opened["symbol"], opened["qty"], opened["fill"], p.get("stop"),
            p.get("target"), p.get("risk_per_share")))
    elif not closed:
        print("  Brak nowych wejsc (brak sygnalu / limity / brak miejsc).")

    m = engine.snapshot(sim, cfg)
    book.save_sim(sim)
    try:
        dashboard.build(sim, cfg)
    except Exception as e:  # noqa: BLE001 - panel nie moze wywalic symulacji
        print("  (panel sie nie zbudowal: %s)" % e)
    print("Wycena: %.2f USD = %.2f PLN (netto po podatku %.2f PLN)" % (
        m["equity_usd"], m["equity_pln"], m["equity_pln_net"]))
    print(engine.day_line(sim))
    return 0


if __name__ == "__main__":
    sys.exit(main())

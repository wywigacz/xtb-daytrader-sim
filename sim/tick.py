"""Tick srodzienny: jedno uruchomienie w trakcie sesji USA.

Uruchamiany co ~15 minut przez GitHub Actions. Robi dwie rzeczy:
  1. ZARZADZA otwartymi pozycjami (stop / target / czas flat-by) po swiecach 5m.
  2. Jesli są wolne miejsca, szuka JEDNEGO nowego wejścia wg metodyki skilla.
Na koniec robi wycene i zapisuje stan.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import book, dashboard, engine, market, session as ses, store, strategy  # noqa: E402


def _cli_now():
    """--now "YYYY-MM-DD HH:MM" (czas NY) zamraza zegar - do testów i odtwarzania."""
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
        print("Symulacja zakończona %s. Nic nie robie." % sim["end_date"])
        return 0
    if str(today) < str(sim["start_date"]):
        print("Symulacja startuje %s. Nic nie robie." % sim["start_date"])
        return 0
    if not ses.is_trading_day(today):
        print("Dzień wolny (weekend/swieto). Nic nie robie.")
        return 0

    engine.refresh_fx(sim, cfg)
    if engine.maybe_deposit(sim, cfg, today):
        print("Wpłata wykonana. Wpłaty razem: %.0f PLN" % sim["deposits_pln_total"])

    if sim.get("last_day") != str(today):
        sim["day_count"] = int(sim.get("day_count") or 0) + 1
        sim["last_day"] = str(today)

    if not ses.is_open(now):
        print("Sesja zamknięta (%s). Zapisuje tylko stan." % store.ny_stamp(now))
        engine.snapshot(sim, cfg)
        book.save_sim(sim)
        return 0

    print("Sesja otwarta. Minut od otwarcia: %.0f" % ses.minutes_since_open(now))

    # Kazdy blad sieci czy feedu jest niekrytyczny: zapisujemy co sie udalo
    # i konczymy tick bez wywalania calego uruchomienia (stan i tak zostanie
    # zapisany nizej). Bez tego jeden timeout Yahoo przerywal dzien.
    try:
        closed = strategy.manage(sim, now)
    except Exception as e:  # noqa: BLE001
        closed = []
        print("  (zarzadzanie pozycjami przerwane: %s: %s)" % (type(e).__name__, e))
    for t in closed:
        print("  ZAMKNIETE %s %s @ %s | P&L %.2f USD (%s)" % (
            t["symbol"], t["qty"], t["exit_usd"], t["pnl_usd"], t["exit_reason"]))

    try:
        opened = strategy.try_enter(sim, now)
    except Exception as e:  # noqa: BLE001
        opened = None
        print("  (szukanie wejsc przerwane: %s: %s)" % (type(e).__name__, e))
        book.decide(sim, "error",
                    title="Nie udało się sprawdzić rynku",
                    why="Yahoo albo feed wiadomości nie odpowiedzial. Nic nie kupiłem; "
                        "sprobuje przy następnym uruchomieniu (za kilka minut).",
                    error="%s: %s" % (type(e).__name__, str(e)[:180]))
    if opened:
        p = opened["plan"]
        print("  OTWARTE %s %s @ %s | stop %s | target %s | ryzyko/akcja %s" % (
            opened["symbol"], opened["qty"], opened["fill"], p.get("stop"),
            p.get("target"), p.get("risk_per_share")))
    elif not closed:
        print("  Brak nowych wejsc (brak sygnału / limity / brak miejsc).")

    m = engine.snapshot(sim, cfg)
    book.save_sim(sim)
    try:
        dashboard.build(sim, cfg)
    except Exception as e:  # noqa: BLE001 - panel nie moze wywalic symulacji
        print("  (panel się nie zbudowal: %s)" % e)
    print("Wycena: %.2f USD = %.2f PLN (netto po podatku %.2f PLN)" % (
        m["equity_usd"], m["equity_pln"], m["equity_pln_net"]))
    print(engine.day_line(sim))
    return 0


if __name__ == "__main__":
    sys.exit(main())

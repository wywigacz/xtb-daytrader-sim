"""Zacznij symulacje od nowa.

Kasuje stan (konto, historie, decyzje) i otwiera konto na nowo: wpłaca
kapitał startowy od razu, żeby portfel nie zaczynał od zera.

    python -m sim.reset --yes            # tylko gdy symulacja nie ma historii
    python -m sim.reset --yes --force    # nawet gdy ma (kasuje historie!)
"""
from __future__ import annotations

import argparse
import os

from . import book, engine, store


def _remove(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Zacznij symulacje od nowa.")
    ap.add_argument("--yes", action="store_true", help="potwierdzam, ze chce zaczac od nowa")
    ap.add_argument("--force", action="store_true", help="kasuj takze rozegrana historie")
    a = ap.parse_args()
    if not a.yes:
        print("Nic nie zmieniam. Dodaj --yes, jesli naprawde chcesz zaczac od nowa.")
        return 1

    sim = book.load_sim()
    trades = store.read_csv(store.TRADES)
    deposits = sim.get("deposits") or []
    if (trades or len(deposits) > 1) and not a.force:
        print("Ta symulacja ma juz historie: %d transakcji, %d wplat." % (len(trades), len(deposits)))
        print("Jesli naprawde chcesz ja skasowac, dodaj --force.")
        return 1

    paths = [store.SIM_JSON, store.EQUITY, store.TRADES, store.DECISIONS,
             store.LEDGER, store.NEWS_STATE, store.PORTFOLIO,
             # resztki planu i zlecen z poprzedniego konta — bez nich start jest
             # naprawdę czysty (inaczej panel potrafi pokazac stara spółkę)
             store.PLAN, store.ENTRY, store.ORDERS]
    removed = [os.path.basename(p) for p in paths if _remove(p)]

    cfg = book.load_cfg()
    os.environ["SIM_NOW"] = str(cfg["simulation"]["start_date"]) + " 09:00"
    fresh = engine.ensure_init({}, cfg)
    m = engine.snapshot(fresh, cfg, prices={})

    print("Usunieto: %s" % (", ".join(removed) if removed else "nic"))
    print("Konto otwarte %s" % cfg["simulation"]["start_date"])
    print("  wpłacone:        %10s zl" % ("{:,.0f}".format(float(fresh.get("deposits_pln_total") or 0)).replace(",", " ")))
    print("  w portfelu:      %10s zl (po koszcie wymiany waluty)"
          % ("{:,.0f}".format(float(m.get("equity_pln") or 0)).replace(",", " ")))
    print("  gotówka w USD:   %10s" % ("{:,.2f}".format(float(m.get("cash_usd") or 0))))
    print("  pozycje:         %10s" % (len(fresh.get("open") or {})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

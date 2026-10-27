"""Silnik symulacji - czesc wspolna dla ticku srodziennego i rozliczenia dziennego."""
from __future__ import annotations

import os
import sys

if __package__ in (None, ""):  # uruchamiane jako skrypt: python sim/tick.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta  # noqa: E402

from sim import book, market, session as ses, store, strategy  # noqa: E402

EQUITY_COLS = [
    "date", "equity_usd", "equity_pln", "equity_pln_net", "cash_usd",
    "positions_usd", "deposits_pln_total", "rate", "bench_pln", "bench_units",
    "tax_owed_pln", "tax_paid_pln", "loss_carry_pln",
]


def ensure_init(sim: dict, cfg: dict) -> dict:
    """Zainicjuj stan i ZROB WPLATE STARTOWA od razu.

    Wpłata startowa nie czeka na pierwszy dzień handlowy: konto ma mieć
    10 000 zl w portfelu od samego poczatku, a nie zero.
    """
    sc = cfg["simulation"]
    if not sim.get("start_date"):
        sim["start_date"] = sc["start_date"]
        # Data konca = dzien, w ktorym licznik dojdzie do "days" DNI SESYJNYCH.
        # Wczesniej bylo "+300 dni kalendarzowych", a licznik liczy dni sesyjne -
        # czyli symulacja konczylaby sie w polowie (ok. 210 z 300) i panel nigdy
        # nie dobrowalby do konca.
        d = datetime.strptime(sc["start_date"], "%Y-%m-%d").date()
        n, ostatni = 0, d
        while n < int(sc["days"]):
            if ses.is_trading_day(d):
                n += 1
                ostatni = d
            d += timedelta(days=1)
        sim["end_date"] = ostatni.isoformat()
        sim["open"] = {}
        sim["deposits"] = []
        sim["realized_pnl_usd"] = 0.0
        sim["tax_reserve_pln"] = 0.0
        sim["year_result_pln"] = {}      # wynik per rok podatkowy (PLN)
        sim["tax_settled"] = []          # rozliczone lata (PIT-38)
        sim["tax_paid_pln"] = 0.0        # podatek faktycznie zaplacony
        sim["loss_carry_pln"] = 0.0      # strata do odliczenia (max 5 lat)
        sim["fx"] = {"rate": float(cfg.get("fx_fallback", 3.65)), "as_of": store.ny_stamp()}
        sim["day_count"] = 0
        book.save_sim(sim)
        # wpłata startowa od razu - portfel nie zaczyna od zera
        day0 = sc["start_date"]
        try:
            rate = market.fx_usdpln()
        except Exception:  # noqa: BLE001
            rate = float(cfg.get("fx_fallback", 3.65))
        sim["fx"] = {"rate": round(float(rate), 4), "as_of": day0 + " 09:00"}
        book.deposit(sim, float(sc["start_capital_pln"]), float(rate), day0)
        book.decide(sim, "start", title="Otwarcie konta",
                    why="Wpłata startowa %s zł, wymieniona na dolary."
                        % ("{:,.0f}".format(float(sc["start_capital_pln"])).replace(",", " ")),
                    numbers={"pln": float(sc["start_capital_pln"]), "rate": round(float(rate), 4)})
        book.save_sim(sim)
    return sim


def refresh_fx(sim: dict, cfg: dict) -> float:
    try:
        rate = market.fx_usdpln()
    except Exception:  # noqa: BLE001
        rate = float(sim.get("fx", {}).get("rate") or cfg.get("fx_fallback", 3.65))
    prev = float((sim.get("fx") or {}).get("rate") or 0)
    if prev and abs(rate - prev) / prev > 0.0015:
        book.decide(sim, "fx", title="Kurs USD/PLN się zmienił",
                    why="Przelicznik walutowy zmienił się o %.2f%%, więc wartość portfela w złotówkach też."
                        % ((rate / prev - 1) * 100),
                    numbers={"rate": round(rate, 4), "was": round(prev, 4)})
    sim["fx"] = {"rate": round(rate, 4), "as_of": store.ny_stamp()}
    return rate


def maybe_deposit(sim: dict, cfg: dict, today) -> bool:
    """Wpłata startowa (przy pierwszym uruchomieniu) + miesięczna 10 000 PLN
    w pierwszym dniu handlowym miesiąca."""
    sc = cfg["simulation"]
    if str(today) < str(sim["start_date"]):
        return False
    if not sim.get("deposits"):
        first = True
    elif first_trading_day_of_month(today) and book.month_needs_deposit(sim, today):
        first = False
    else:
        return False
    pln = float(sc["start_capital_pln"] if first else sc["monthly_deposit_pln"])
    rate = float(sim.get("fx", {}).get("rate") or cfg.get("fx_fallback", 3.65))
    rec = book.deposit(sim, pln, rate, ses.iso_day(today))
    book.decide(
        sim, "deposit",
        title="Wpłata %s zl" % ("{:,.0f}".format(pln).replace(",", " ")),
        why=("Pierwsza wpłata startowa, przewalutowana na dolary po kursie %.4f." % rate) if first
            else ("Kolejna wpłata miesięczna, przewalutowana na dolary po kursie %.4f." % rate),
        numbers={"pln": pln, "rate": round(rate, 4), "usd": rec["usd"],
                 "fee": rec.get("fx_fee_usd"), "first": first},
    )
    return True


def first_trading_day_of_month(d) -> bool:
    """Czy dzisiaj jest pierwszy dzień handlowy tego miesiąca?"""
    probe = d.replace(day=1)
    while probe <= d:
        if ses.is_trading_day(probe):
            return probe == d
        probe = probe + timedelta(days=1)
    return False


def snapshot(sim: dict, cfg: dict, prices: dict[str, float] | None = None) -> dict:
    """Wycena + wiersz historii kapitału (+ benchmark)."""
    if prices is None:
        syms = list(book.holdings().keys())
        prices = {s: p for s, (p, _t) in strategy.quotes_for(syms).items()}
    # polski podatek: raz w roku po zamknieciu roku podatkowego, zaplata do 30.04
    try:
        book.settle_taxes(sim, ses.now_ny())
    except Exception as ex:  # noqa: BLE001 - podatek nie moze przewrocic dnia
        book.decide(sim, "error", title="Nie udało się rozliczyć podatku", why=str(ex))
    m = book.mark(sim, prices)
    rate = float(sim.get("fx", {}).get("rate") or 3.65)
    b = sim.get("benchmark") or {}
    bench_pln = ""
    try:
        lvl = market.last_price(b.get("symbol", "^GSPC"))[0]
        bench_pln = round(float(b.get("units", 0.0)) * lvl * rate, 2)
    except Exception:  # noqa: BLE001
        pass
    row = {
        "date": ses.iso_day(ses.now_ny()),
        "equity_usd": m["equity_usd"],
        "equity_pln": m["equity_pln"],
        "equity_pln_net": m["equity_pln_net"],
        "cash_usd": m["cash_usd"],
        "positions_usd": m["positions_usd"],
        "deposits_pln_total": round(float(sim.get("deposits_pln_total") or 0), 2),
        "rate": rate,
        "bench_pln": bench_pln,
        "bench_units": b.get("units", ""),
        # podatek w wierszu historii: stopka panelu pokazuje stan z ostatniej wyceny
        "tax_owed_pln": m.get("tax_owed_pln", 0),
        "tax_paid_pln": m.get("tax_paid_pln", 0),
        "loss_carry_pln": m.get("loss_carry_pln", 0),
    }
    # jedna linia na dzien (nadpisz dzisiejsza, jesli juz jest)
    rows = [r for r in store.read_csv(store.EQUITY) if r.get("date") != row["date"]]
    rows.append({k: str(v) for k, v in row.items()})
    _rewrite_csv(store.EQUITY, rows, EQUITY_COLS)
    m["date"] = row["date"]
    m["bench_pln"] = bench_pln
    return m


def _rewrite_csv(path: str, rows: list[dict], cols: list[str]) -> None:
    import csv
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def day_line(sim: dict) -> str:
    d = sim.get("deposits_pln_total") or 0
    return "dzień %s/%s | otwarte: %d | wpłaty: %.0f PLN" % (
        sim.get("day_count", 0), book.load_cfg()["simulation"]["days"],
        len(sim.get("open") or {}), d)

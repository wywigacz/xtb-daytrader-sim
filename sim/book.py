"""Papierowy broker symulacji: wpłaty PLN, wymiana na USD, kupno/sprzedaż,
wycena portfela, polski podatek roczny (PIT-38), dziennik zdarzeń.

Konto handlowe w USD (plik trader/portfolio.json w formacie skilla, aktualizowany
przez ticket.py skilla - dzieki temu trader-risk widzi prawdziwe saldo i pozycje).
Ksiegowosc na poziomie PLN trzymamy we własnym pliku sim/state/sim.json.
"""
from __future__ import annotations

import json

from . import market, session as ses, skilltools, store, xtb


class BookError(RuntimeError):
    pass


# --------------------------------------------------------------- stan symulacji
def load_cfg() -> dict:
    cfg = store.read_json(store.SIM_CONFIG)
    if not cfg:
        raise BookError("brak sim/config.json")
    return cfg


def load_sim() -> dict:
    return store.read_json(store.SIM_JSON) or {}


def save_sim(sim: dict) -> None:
    store.write_json(store.SIM_JSON, sim)


def portfolio() -> dict:
    return store.read_json(store.PORTFOLIO) or {"cash": 0.0, "positions": []}


def cash_usd() -> float:
    return float(portfolio().get("cash") or 0.0)


def holdings() -> dict[str, float]:
    out = {}
    for pos in portfolio().get("positions", []):
        t = str(pos.get("ticker") or pos.get("symbol") or "").upper()
        n = float(pos.get("shares") or 0)
        if t and n > 1e-9:
            out[t] = out.get(t, 0.0) + n
    return out


def cost_basis(symbol: str) -> float:
    for pos in portfolio().get("positions", []):
        if str(pos.get("ticker") or "").upper() == symbol.upper():
            return round(sum(float(l.get("cost") or 0) for l in pos.get("lots", [])), 2)
    return 0.0


def position_value(prices: dict[str, float]) -> float:
    total = 0.0
    for t, n in holdings().items():
        px = prices.get(t)
        total += (px if px else 0.0) * n
    return round(total, 2)


# --------------------------------------------------------------- narzedzia
def _log(sim: dict, event: str, **kw) -> None:
    row = {
        "ts_ny": store.ny_stamp(),
        "event": event,
        "symbol": kw.get("symbol", ""),
        "qty": kw.get("qty", ""),
        "price_usd": kw.get("price_usd", ""),
        "notional_usd": kw.get("notional_usd", ""),
        "fee_usd": kw.get("fee_usd", ""),
        "cash_usd_after": round(cash_usd(), 2),
        "equity_usd": kw.get("equity_usd", ""),
        "note": kw.get("note", ""),
    }
    store.append_csv(store.LEDGER, row, store.LEDGER_COLS)


def decide(sim: dict, decision: str, **kw) -> None:
    """Dziennik decyzji: co agent zrobil i dlaczego."""
    rec = {"ts_ny": store.ny_stamp(), "decision": decision}
    rec.update(kw)
    store.append_jsonl(store.DECISIONS, rec)


def num0(x) -> str:
    """1234.5 -> '1 235' (polski zapis kwoty)."""
    try:
        return "{:,.0f}".format(abs(float(x))).replace(",", " ")
    except (TypeError, ValueError):
        return str(x)


def _pl_date(iso: str) -> str:
    """'2027-04-30' -> '30.04.2027' (polski zapis daty)."""
    try:
        y, m, d = str(iso)[:10].split("-")
        return "%s.%s.%s" % (d, m, y)
    except ValueError:
        return str(iso)


def _cash_add(usd: float) -> None:
    """Zmienia saldo gotówki w USD (np. zaplata podatku)."""
    pf = portfolio()
    pf["cash"] = round(float(pf.get("cash") or 0) + usd, 2)
    store.write_json(store.PORTFOLIO, pf)


# --------------------------------------------------------------- podatek (PL)
def cash_move(usd: float) -> None:
    """Ruch gotówki w USD: dodatni = wpływ, ujemny = kupno/wypłata."""
    _cash_add(usd)


def tax_state(sim: dict) -> dict:
    """Stan podatku po polsku: zaplacony, do zaplaty, naliczony, strata do odliczenia."""
    pct = float(load_cfg()["costs"]["tax_on_gains_pct"])
    settled = sim.get("tax_settled") or []
    paid = round(sum(float(s.get("tax_pln") or 0) for s in settled if s.get("paid")), 2)
    unpaid = round(sum(float(s.get("tax_pln") or 0) for s in settled if not s.get("paid")), 2)
    done = {s.get("year") for s in settled}
    open_year = None
    for y in sorted(sim.get("year_result_pln") or {}):
        if y not in done:
            open_year = y
    accrued = 0.0
    if open_year:
        accrued = xtb.accrued_tax_year((sim.get("year_result_pln") or {}).get(open_year),
                                       sim.get("loss_carry_pln") or 0, pct)
    return {"paid_pln": paid, "unpaid_pln": unpaid, "accrued_pln": accrued,
            "owed_pln": round(unpaid + accrued, 2),
            "loss_carry_pln": round(float(sim.get("loss_carry_pln") or 0), 2),
            "settled": settled, "open_year": open_year}


def settle_taxes(sim: dict, now) -> list[dict]:
    """Rozlicza podatek po polsku.

    1) rok podatkowy, ktory sie skonczyl -> liczymy podatek (19% od dochodu,
       po odjeciu max 50% straty z lat ubieglych),
    2) podatek placony jest do 30 kwietnia roku nastepnego - wtedy schodzi
       z konta (z kosztem wymiany USD->PLN).
    """
    cfg = load_cfg()
    pct = float(cfg["costs"]["tax_on_gains_pct"])
    rate = float(sim.get("fx", {}).get("rate") or 3.65)
    today = store.ny_stamp(now)[:10]
    out = []
    yr = sim.get("year_result_pln") or {}
    settled = sim.setdefault("tax_settled", [])
    for year in sorted(yr):
        if any(s.get("year") == year for s in settled):
            continue
        if today <= "%s-12-31" % year:
            continue
        res = float(yr.get(year) or 0)
        tax, deducted, carry = xtb.settle_tax_year(res, sim.get("loss_carry_pln") or 0, pct)
        sim["loss_carry_pln"] = carry
        rec = {"year": year, "result_pln": round(res, 2), "tax_pln": tax,
               "deducted_pln": deducted, "pay_by": "%s-04-30" % (int(year) + 1), "paid": False}
        settled.append(rec)
        out.append(rec)
        _log(sim, "TAX_DUE", notional_usd=round(tax / rate, 2),
             note="rozliczenie roku %s: wynik %.0f PLN, podatek %.0f PLN (zaplace do %s)"
                  % (year, res, tax, rec["pay_by"]))
        decide(sim, "tax_due", title="Rozliczenie roku %s" % year,
               why=(("Wynik roku %s zł, podatek %s zł do %s."
                     % (num0(res), num0(tax), _pl_date(rec["pay_by"]))) if tax else
                    ("Wynik roku %s zł. Podatku nie ma." % num0(res))),
               numbers={"rok": year, "wynik_pln": round(res, 2), "podatek_pln": tax})
    fx = float(cfg["costs"]["fx_cost_pct"]) / 100.0
    for s in settled:
        if s.get("paid") or float(s.get("tax_pln") or 0) <= 0:
            continue
        if today >= str(s.get("pay_by")):
            _cash_add(-round(float(s["tax_pln"]) * (1 + fx) / rate, 2))
            s["paid"] = True
            s["paid_date"] = today
            sim["tax_paid_pln"] = round(float(sim.get("tax_paid_pln") or 0) + float(s["tax_pln"]), 2)
            _log(sim, "TAX_PAID", notional_usd=round(float(s["tax_pln"]) / rate, 2),
                 note="zaplacony podatek za %s: %.0f PLN" % (s["year"], float(s["tax_pln"])))
            decide(sim, "tax_paid", title="Zapłacony podatek za %s" % s["year"],
                   why="Zeszło z konta %s." % num0(s["tax_pln"]),
                   numbers={"rok": s["year"], "podatek_pln": float(s["tax_pln"])})
    if out:
        save_sim(sim)
    return out


# --------------------------------------------------------------- wplaty / FX
def deposit(sim: dict, pln: float, rate: float, date_label: str) -> dict:
    cfg = load_cfg()
    usd, fee = xtb.fx_pln_to_usd(pln, rate, float(cfg["costs"]["fx_cost_pct"]))
    pf = portfolio()
    pf["cash"] = round(float(pf.get("cash") or 0) + usd, 2)
    store.write_json(store.PORTFOLIO, pf)
    rec = {"date": date_label, "pln": round(pln, 2), "rate": round(rate, 4),
           "usd": usd, "fx_fee_usd": fee}
    sim.setdefault("deposits", []).append(rec)
    sim["deposits_pln_total"] = round(sum(d["pln"] for d in sim["deposits"]), 2)
    # benchmark: ta sama wplata w indeks S&P 500 (poziom indeksu)
    try:
        lvl = market.last_price(cfg["benchmark"]["symbol"])[0]
        b = sim.setdefault("benchmark", {"symbol": cfg["benchmark"]["symbol"], "units": 0.0, "spent_usd": 0.0})
        b["units"] = round(float(b.get("units", 0.0)) + usd / lvl, 6)
        b["spent_usd"] = round(float(b.get("spent_usd", 0.0)) + usd, 2)
        rec["benchmark_level"] = lvl
    except Exception as e:  # noqa: BLE001
        rec["benchmark_error"] = str(e)
    _log(sim, "DEPOSIT", notional_usd=usd, fee_usd=fee,
         note="wpłata %.0f PLN @ %.4f -> %.2f USD" % (pln, rate, usd))
    return rec


def month_needs_deposit(sim: dict, today) -> bool:
    """Czy w tym miesiacu była już wpłata?"""
    mk = today.strftime("%Y-%m")
    for d in sim.get("deposits", []):
        if str(d["date"]).startswith(mk):
            return False
    return True


# --------------------------------------------------------------- transakcje
def record_open(sim: dict, symbol: str, qty: float, price: float, plan: dict,
                notional: float, fee: float, reason: str, now=None) -> None:
    """Zapisz otwarcie pozycji w stanie symulacji.

    Uwaga: portfolio.json (konto USD) jest już zaktualizowane przez
    `ticket.py result --status placed --filled-qty ...`. Tutaj NIE wolno
    powtarzac fillu - inaczej kupno policzy się dwa razy.
    """
    sim.setdefault("open", {})[symbol.upper()] = {
        "symbol": symbol.upper(),
        "qty": qty,
        "entry": price,
        "stop": float(plan.get("stop") or 0),
        "target": float(plan.get("target") or 0),
        "risk_per_share": float(plan.get("risk_per_share") or 0),
        "setup": plan.get("setup") or "orb",
        "opened_at": store.ny_stamp(now),
        "opened_day": ses.iso_day(ses.now_ny(now)),
        "flat_by": plan.get("flat_by") or "15:55",
        "order_notional": round(notional, 2),
    }
    _log(sim, "BUY", symbol=symbol, qty=qty, price_usd=price, notional_usd=round(notional, 2),
         fee_usd=fee, note=reason)


def close_position(sim: dict, symbol: str, qty: float, price: float, fee: float,
                   exit_reason: str, now=None) -> dict:
    symbol = symbol.upper()
    op = (sim.get("open") or {}).get(symbol) or {}
    entry = float(op.get("entry") or price)
    rc, out, err = skilltools.run(
        "ticket",
        ["fill", "--symbol", symbol, "--side", "sell", "--qty", qty,
         "--price", price, "--date", ses.iso_day(ses.now_ny(now)),
         "--now", store.ny_stamp(now)],
    )
    if rc != 0:
        raise BookError("ticket.py fill (sprzedaż) nieudane: %s" % (err or out).strip())
    gross = qty * (price - entry)
    pnl = round(gross - fee, 2)
    sim["realized_pnl_usd"] = round(float(sim.get("realized_pnl_usd") or 0) + pnl, 2)
    sim.get("open", {}).pop(symbol, None)
    risk = float(op.get("entry") or 0) - float(op.get("stop") or 0)
    if risk <= 0:
        risk = float(op.get("risk_per_share") or 0)
    rmult = round((price - entry) / risk, 2) if risk > 0 else None
    hold = 0
    try:
        from datetime import datetime
        a = datetime.strptime(op.get("opened_at", ""), "%Y-%m-%d %H:%M")
        b = datetime.strptime(store.ny_stamp(now), "%Y-%m-%d %H:%M")
        hold = int((b - a).total_seconds() // 60)
    except Exception:  # noqa: BLE001
        hold = 0
    trade = {
        "open_ts_ny": op.get("opened_at", ""), "close_ts_ny": store.ny_stamp(now),
        "symbol": symbol, "qty": qty, "entry_usd": round(entry, 4), "exit_usd": round(price, 4),
        "pnl_usd": pnl, "ret_pct": round((price / entry - 1) * 100, 3) if entry else 0,
        "r_multiple": rmult if rmult is not None else "", "exit_reason": exit_reason,
        "setup": op.get("setup", ""), "hold_min": hold,
    }
    store.append_csv(store.TRADES, trade, store.TRADE_COLS)
    # Polski podatek: NIE placimy go od pojedynczej transakcji. Wynik zapisujemy
    # per rok podatkowy w PLN, a podatek liczymy i placimy raz w roku (PIT-38,
    # do 30 kwietnia roku nastepnego). Szczegoly: settle_taxes() i sim/xtb.py.
    rate = float(sim.get("fx", {}).get("rate") or 3.65)
    year = str(store.ny_stamp(now))[:4]
    yr = sim.setdefault("year_result_pln", {})
    yr[year] = round(float(yr.get(year) or 0) + pnl * rate, 2)
    _log(sim, "SELL", symbol=symbol, qty=qty, price_usd=price, notional_usd=round(qty * price, 2),
         fee_usd=fee, note="%s | P&L %.2f USD" % (exit_reason, pnl))
    return trade


def mark(sim: dict, prices: dict[str, float]) -> dict:
    """Wycena portfela: USD i PLN po kursie, plus stan podatku.

    Uwaga na polskie realia: podatek placimy dopiero do 30 kwietnia roku
    nastepnego, wiec pieniadze na podatek do tego dnia pracuja na koncie.
    Dlatego 'ile mam na koncie' (equity_pln) i 'ile zostanie po podatku'
    (equity_pln_net) to dwie rozne liczby - panel pokazuje obie.
    """
    rate = float(sim.get("fx", {}).get("rate") or 3.65)
    cash = cash_usd()
    pos_val = position_value(prices)
    equity_usd = round(cash + pos_val, 2)
    equity_pln = xtb.usd_to_pln(equity_usd, rate)
    t = tax_state(sim)
    return {
        "equity_usd": equity_usd,
        "cash_usd": cash,
        "positions_usd": pos_val,
        "equity_pln": equity_pln,
        "tax_reserve_pln": t["owed_pln"],
        "tax_owed_pln": t["owed_pln"],
        "tax_paid_pln": t["paid_pln"],
        "tax_unpaid_pln": t["unpaid_pln"],
        "tax_accrued_pln": t["accrued_pln"],
        "loss_carry_pln": t["loss_carry_pln"],
        "equity_pln_net": round(equity_pln - t["owed_pln"], 2),
        "rate": rate,
    }

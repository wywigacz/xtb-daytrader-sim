"""Generator PRZYKLADOWEGO panelu (do dokumentacji i podglądu).

Tworzy w katalogu tymczasowym kompletne, ale WYMYŚLONE dane: rok podatkowy
2026 -> 2027, wpłaty co miesiąc, kilkanaście transakcji, badania spółek,
rozliczenie podatku. Na tej podstawie buduje panel i obrazek
`docs/przyklad-panelu.png`.

    python tools/przyklad.py

Nic nie dotyka prawdziwego stanu symulacji (`sim/state/`) — wszystko idzie do
katalogu tymczasowego.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC)

RATE = 4.05
START, END = date(2026, 11, 3), date(2027, 7, 20)

# (symbol, szt, kupno, sprzedaz, wynik USD, x ryzyko, sposob wyjscia)
PLAN = {
    "2026-11": [("AVGO", 1, 323.07, 327.22, 4.15, 1.58, "target"),
                ("MSFT", 1, 523.50, 521.10, -2.40, -1.00, "stop"),
                ("BAC", 14, 50.77, 51.40, 8.82, 1.42, "target"),
                ("AAL", 61, 12.12, 11.98, -8.54, -0.62, "flat_by")],
    "2026-12": [("GOOGL", 1, 323.16, 328.90, 5.74, 2.10, "target"),
                ("NVDA", 3, 213.00, 216.40, 10.20, 1.21, "target"),
                ("CVX", 3, 233.33, 231.90, -4.29, -1.00, "stop"),
                ("META", 1, 644.00, 655.80, 11.80, 1.30, "target")],
    "2027-01": [("TSLA", 2, 402.10, 398.20, -7.80, -1.00, "stop"),
                ("AMD", 4, 175.20, 180.60, 21.60, 1.44, "target")],
    "2027-02": [("AAPL", 3, 268.40, 272.10, 11.10, 1.12, "target"),
                ("INTC", 22, 36.10, 35.40, -15.40, -1.00, "stop")],
    "2027-03": [("JPM", 2, 298.50, 297.10, -2.80, -1.00, "stop"),
                ("XOM", 5, 118.30, 122.40, 20.50, 1.68, "target"),
                ("F", 60, 12.80, 13.10, 18.00, 1.05, "target")],
    "2027-04": [("KO", 8, 71.20, 70.40, -6.40, -1.00, "stop")],
    "2027-05": [("WMT", 5, 96.40, 99.80, 17.00, 1.42, "target"),
                ("PFE", 30, 26.10, 25.70, -12.00, -1.00, "stop")],
    "2027-06": [("MU", 2, 148.60, 154.20, 11.20, 1.55, "target")],
    "2027-07": [("GS", 1, 588.00, 597.40, 9.40, 1.60, "target"),
                ("T", 40, 28.60, 27.90, -28.00, -1.00, "stop")],
}
SCALE = 6  # konto z wplatami 10 000 zl: wynik jednej transakcji to ok. +/-25 USD

BADANIE = {
    "GS": {"przychody": "+13% r/r", "marża zysku": "28%", "zysk na akcję": "+22% r/r"},
    "T": {"przychody": "+1% r/r", "marża zysku": "14%", "zysk na akcję": "+6% r/r"},
    "AAPL": {"przychody": "+16% r/r", "marża zysku": "27%", "zysk na akcję": "+29% r/r"},
}


def main() -> int:
    out_dir = os.path.join(tempfile.gettempdir(), "hermes-przyklad")
    shutil.rmtree(out_dir, ignore_errors=True)
    for sub in ("sim/state", "docs", "trader", "data"):
        os.makedirs(os.path.join(out_dir, sub), exist_ok=True)

    from sim import book, dashboard, engine, store

    store.ROOT = out_dir
    store.STATE = os.path.join(out_dir, "sim", "state")
    store.DECISIONS = os.path.join(store.STATE, "decisions.jsonl")
    store.SIM_JSON = os.path.join(store.STATE, "sim.json")
    store.EQUITY = os.path.join(store.STATE, "equity.csv")
    store.TRADES = os.path.join(store.STATE, "trades.csv")
    store.NEWS_STATE = os.path.join(store.STATE, "news.json")
    store.PORTFOLIO = os.path.join(out_dir, "trader", "portfolio.json")
    store.UNIVERSE = os.path.join(out_dir, "universe.txt")
    store.SPOLKI = os.path.join(out_dir, "data", "spolki.csv")
    shutil.copyfile(os.path.join(SRC, "data", "spolki.csv"), store.SPOLKI)
    shutil.copyfile(os.path.join(SRC, "universe.txt"), store.UNIVERSE)

    days, d = [], START
    while d <= END:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    dep_days, seen = [], set()
    for day in days:
        if day[:7] not in seen:
            seen.add(day[:7])
            dep_days.append(day)

    plan = {k: [(s, q * SCALE, en, ex, round(p * SCALE, 2), r, w)
                for (s, q, en, ex, p, r, w) in v] for k, v in PLAN.items()}
    tr = ["open_ts_ny,close_ts_ny,symbol,qty,entry_usd,exit_usd,pnl_usd,ret_pct,"
          "r_multiple,exit_reason,setup,hold_min"]
    dec, rok = [], {}
    for ym, rows in sorted(plan.items()):
        day = days[-1] if ym == "2027-07" else [x for x in days if x.startswith(ym)][3]
        for k, (sym, q, en, ex, pnl, r, why) in enumerate(rows):
            tr.append("%s %02d:20,%s 15:%02d,%s,%d,%.2f,%.2f,%.2f,%.2f,%.2f,%s,orb,%d" % (
                day, 10 + k, day, 30 + k * 5, sym, q, en, ex, pnl,
                (ex / en - 1) * 100, r, why, 55 + k * 30))
            rok[day[:4]] = round(rok.get(day[:4], 0.0) + pnl * RATE, 2)
        dec.append({"ts_ny": day + " 10:18", "decision": "scan",
                    "title": "Przejrzałem 48 spółek",
                    "why": "Szukałem ceny, która wyszła nad szczyt pierwszych 15 minut.",
                    "numbers": {"scanned": 48, "hits": 11, "top": [r[0] for r in rows[:2]]}})
        for sym, q, en, ex, pnl, r, why in rows[:2]:
            num = {"qty": q, "entry": en, "stop": round(en * 0.992, 2),
                   "target": round(en * 1.008, 2), "max_loss": round(q * en * 0.008, 2)}
            if sym in BADANIE:
                num["badanie"] = BADANIE[sym]
            dec.append({"ts_ny": day + " 10:22", "decision": "open", "symbol": sym,
                        "title": "Kupiłem %d %s" % (q, sym),
                        "why": ("Cena przebiła szczyt pierwszych 15 minut i zamknęła się nad nim. "
                                "Stop i cel są tak samo daleko."),
                        "numbers": num})
            dec.append({"ts_ny": day + " 15:30", "decision": "close", "symbol": sym,
                        "title": "%s: %s" % (sym, "cel osiągnięty" if why == "target" else
                                             ("stop zadziałał" if why == "stop"
                                              else "zamknięte na koniec dnia")),
                        "why": ("Cena doszła do celu. Sprzedane z zyskiem." if why == "target" else
                                ("Cena spadła do poziomu, który chronił pieniądze. Sprzedane ze stratą."
                                 if why == "stop" else "Zamknięte przed końcem giełdy.")),
                        "numbers": {"entry": en, "exit": ex, "pnl": pnl, "r": r}})
    dec.append({"ts_ny": days[-1] + " 10:21", "decision": "skip", "symbol": "MRNA", "code": "badanie",
                "title": "MRNA: badanie spółki wypadło słabo",
                "why": ("Ostatni kwartał zamknął się stratą. Ostatni raport: przychody +2% r/r, "
                        "marża zysku -539%."),
                "numbers": {"przychody": "+2% r/r", "marża zysku": "-539%"}})
    dec.append({"ts_ny": dep_days[0] + " 15:45", "decision": "deposit", "title": "Wpłata 10 000 zł",
                "why": "Wpłata miesięczna, wymieniona na dolary.",
                "numbers": {"pln": 10000, "rate": RATE, "usd": 2469.14}})
    open(store.TRADES, "w", encoding="utf-8").write("\n".join(tr) + "\n")
    with open(store.DECISIONS, "w", encoding="utf-8") as fh:
        for x in sorted(dec, key=lambda z: z["ts_ny"]):
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")

    eq = ["date,equity_usd,equity_pln,equity_pln_net,cash_usd,positions_usd,"
          "deposits_pln_total,rate,bench_pln,bench_units,tax_owed_pln,tax_paid_pln,loss_carry_pln"]
    val, dep_total, bu = 0.0, 0.0, 0.0
    drift = [0.8, 1.3, -0.5, 0.2, 1.6, -1.0, 0.4, 1.1, -0.3, 0.6, 1.4, -0.8, 0.3, 1.0]
    for i, day in enumerate(days):
        if day in dep_days:
            dep_total += 10000.0
            val += 10000 / RATE * 0.995
            bu += 10000 / RATE * 0.995
        val *= 1 + drift[i % len(drift)] / 100 * 0.55
        bu *= 1 + drift[i % len(drift)] / 100
        eq.append("%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.0f,%.4f,%.2f,%.4f,0,0,0" % (
            day, val, val * RATE, val * RATE, val * 0.02, val * 0.98, dep_total, RATE,
            bu * RATE, bu))
    open(store.EQUITY, "w", encoding="utf-8").write("\n".join(eq) + "\n")

    json.dump({"days": {days[-1]: {"runs": 5, "read": 38, "blocked": 1, "items": [
        {"ticker": "T", "title": "AT&T falls after analyst downgrade on wireless margins",
         "source": "Yahoo", "time": days[-1] + "T13:12:00+00:00", "tags": "informacja",
         "risk": False, "impact": ""},
        {"ticker": "GS", "title": "Goldman Sachs rises as trading revenue beats forecasts",
         "source": "Yahoo", "time": days[-1] + "T12:05:00+00:00", "tags": "wyniki",
         "risk": False, "impact": ""},
        {"ticker": "WMT", "title": "Walmart lifts outlook, shares steady",
         "source": "Yahoo", "time": days[-1] + "T09:50:00+00:00", "tags": "informacja",
         "risk": False, "impact": ""}]}}},
        open(store.NEWS_STATE, "w", encoding="utf-8"))

    cfg = json.load(open(os.path.join(SRC, "sim", "config.json"), encoding="utf-8"))
    store.write_json(store.PORTFOLIO, {"cash": 2400.0, "positions": []})
    sim = {"start_date": days[0], "end_date": "2027-08-28", "day_count": len(days),
           "deposits_pln_total": dep_total, "fx": {"rate": RATE}, "open": {},
           "deposits": [{"date": x, "pln": 10000, "rate": RATE, "usd": round(10000 / RATE, 2),
                         "fx_fee_usd": round(10000 / RATE * 0.005, 2)} for x in dep_days],
           "year_result_pln": rok, "tax_settled": [], "tax_paid_pln": 0.0, "loss_carry_pln": 0.0,
           "realized_pnl_usd": round(sum(r[4] for v in plan.values() for r in v), 2)}
    os.environ["SIM_NOW"] = days[-1] + " 16:20"
    book.settle_taxes(sim, datetime(2027, 7, 20, 16, 0))
    store.write_json(store.SIM_JSON, sim)
    m = book.mark(sim, {})
    rows = store.read_csv(store.EQUITY)
    if rows:
        rows[-1]["tax_owed_pln"] = m.get("tax_owed_pln", 0)
        rows[-1]["tax_paid_pln"] = m.get("tax_paid_pln", 0)
        rows[-1]["loss_carry_pln"] = m.get("loss_carry_pln", 0)
        engine._rewrite_csv(store.EQUITY, rows, engine.EQUITY_COLS)

    html = open(dashboard.build(sim, cfg), encoding="utf-8").read()
    open(os.path.join(out_dir, "docs", "panel-bez-banera.html"), "w", encoding="utf-8").write(html)
    banner = ('<div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;'
              'background:#26214D;border-left:3px solid #A389F4;padding:10px 14px;margin:0 0 22px;'
              'font-size:14px;color:#D8D6E6;line-height:1.45;border-radius:10px">'
              '<span style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;'
              'color:#A389F4;font-weight:700">Przykład</span>'
              '<span>Dane przykładowe: rok podatkowy 2026 i połowa 2027.</span></div>')
    demo = os.path.join(out_dir, "docs", "przyklad.html")
    open(demo, "w", encoding="utf-8").write(html.replace('<div class="topbar">', banner + '<div class="topbar">', 1))

    png = os.path.join(out_dir, "docs", "przyklad-panelu.png")
    pr = subprocess.run([sys.executable, os.path.join(SRC, "sim", "render.py"),
                         "--html", demo, "--out", png, "--width", "1080"],
                        capture_output=True, text=True)
    print((pr.stdout or pr.stderr).strip() or "(brak wyjscia z render.py)")
    print("wynik 2026: %.2f zl | 2027: %.2f zl" % (rok.get("2026", 0), rok.get("2027", 0)))
    if os.path.exists(png):
        tgt = os.path.join(SRC, "docs", "przyklad-panelu.png")
        shutil.copyfile(png, tgt)
        from PIL import Image
        print("przyklad -> %s (%s, %.0f kB)" % (tgt, Image.open(tgt).size, os.path.getsize(tgt) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

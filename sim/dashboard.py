"""Budowa dashboardu (docs/index.html) - samodzielny plik HTML.

Wszystkie dane sa wklejone w strone (bez pobierania z sieci), wiec dziala
zarowno na GitHub Pages, jak i lokalnie z dysku.
"""
from __future__ import annotations

import json

from . import store

CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mut:#8b949e;
--up:#3fb950;--down:#f85149;--acc:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 70px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:17px;margin:34px 0 12px;color:var(--acc)}
.sub{color:var(--mut);margin:0 0 22px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.4px}
.kpi .v{font-size:22px;font-weight:600;margin-top:6px}
.kpi .n{color:var(--mut);font-size:12px;margin-top:3px}
.up{color:var(--up)}.down{color:var(--down)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:500;font-size:12px;text-transform:uppercase}
tr:hover td{background:#1c2230}
.scroll{overflow-x:auto}
.warn{background:#1f1a12;border:1px solid #6b5320;border-radius:10px;padding:14px;
color:#e3c07a;font-size:13.5px;margin-top:14px}
.muted{color:var(--mut);font-size:13px}
code{background:#1c2230;padding:1px 5px;border-radius:4px;font-size:12.5px}
footer{color:var(--mut);font-size:12.5px;margin-top:40px;border-top:1px solid var(--line);padding-top:16px}
"""


def _pln(x) -> str:
    try:
        return "{:,.0f}".format(float(x)).replace(",", " ") + " zł"
    except Exception:  # noqa: BLE001
        return "—"


def _usd(x) -> str:
    try:
        return "${:,.2f}".format(float(x)).replace(",", " ")
    except Exception:  # noqa: BLE001
        return "—"


def _pct(x) -> str:
    try:
        return "{:+.1f}%".format(float(x))
    except Exception:  # noqa: BLE001
        return "—"


def build(sim: dict, cfg: dict) -> str:
    equity = store.read_csv(store.EQUITY)
    trades = store.read_csv(store.TRADES)
    decisions = [json.loads(l) for l in _read_lines(store.DECISIONS)][-60:]
    sc = cfg["simulation"]

    # --- KPI
    dep = float(sim.get("deposits_pln_total") or 0)
    last = equity[-1] if equity else {}
    val = float(last.get("equity_pln") or 0)
    val_net = float(last.get("equity_pln_net") or 0)
    bench = float(last.get("bench_pln") or 0) if last.get("bench_pln") else None
    gain = val - dep
    gain_pct = (gain / dep * 100.0) if dep else 0.0
    bench_gain = (bench - dep) if bench else None

    # --- statystyki transakcji
    pnls = [float(t.get("pnl_usd") or 0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(pnls) * 100.0) if pnls else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    avg_hold = 0.0
    if trades:
        holds = [float(t.get("hold_min") or 0) for t in trades]
        avg_hold = sum(holds) / len(holds)

    # --- max drawdown na wartosci portfela (PLN)
    mdd = 0.0
    peak = None
    for r in equity:
        v = float(r.get("equity_pln") or 0)
        peak = v if peak is None else max(peak, v)
        if peak:
            mdd = min(mdd, (v - peak) / peak * 100.0)

    labels = [r.get("date") for r in equity]
    series_eq = [float(r.get("equity_pln") or 0) for r in equity]
    series_dep = [float(r.get("deposits_pln_total") or 0) for r in equity]
    series_bench = [float(r["bench_pln"]) if r.get("bench_pln") else None for r in equity]

    positions = sim.get("open") or {}
    pos_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            p.get("symbol"), p.get("qty"), _usd(p.get("entry")), _usd(p.get("stop")),
            _usd(p.get("target")), p.get("opened_at", "")[:16])
        for p in positions.values()) or "<tr><td colspan=6 class=muted>brak otwartych pozycji</td></tr>"

    trade_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class=%s>%s</td><td>%s</td><td>%s</td></tr>" % (
            t.get("symbol"), str(t.get("open_ts_ny", ""))[11:16], str(t.get("close_ts_ny", ""))[5:16],
            t.get("qty"), _usd(t.get("entry_usd")), "up" if float(t.get("pnl_usd") or 0) > 0 else "down",
            _usd(t.get("pnl_usd")), t.get("r_multiple") or "—", t.get("exit_reason"))
        for t in reversed(trades[-40:])) or "<tr><td colspan=8 class=muted>jeszcze brak transakcji</td></tr>"

    dec_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td class=muted>%s</td></tr>" % (
            d.get("ts_ny", ""), d.get("decision", ""), d.get("symbol", ""),
            json.dumps({k: v for k, v in d.items() if k not in ("ts_ny", "decision", "symbol")},
                       ensure_ascii=False)[:220])
        for d in reversed(decisions)) or "<tr><td colspan=4 class=muted>brak decyzji</td></tr>"

    dep_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            d.get("date"), _pln(d.get("pln")), d.get("rate"), _usd(d.get("usd")),
            _usd(d.get("fx_fee_usd")))
        for d in (sim.get("deposits") or [])) or "<tr><td colspan=5 class=muted>brak wplat</td></tr>"

    bench_kpi = ""
    if bench:
        bench_kpi = ('<div class="kpi"><div class="l">%s (te same wplaty)</div>'
                     '<div class="v">%s</div><div class="n %s">%s vs wplaty</div></div>' % (
                         cfg["benchmark"]["label"], _pln(bench),
                         "up" if (bench_gain or 0) > 0 else "down", _pln(bench_gain or 0)))

    html = """<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<style>%(css)s</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head><body><div class="wrap">
<h1>%(title)s</h1>
<p class="sub">Symulacja day-tradingu (metodyka <b>day-trader-skill</b>) na akcjach USA,
rachunek XTB w PLN. Start %(start)s, koniec %(end)s (%(days)s dni).
Aktualizacja: <b>%(updated)s</b> &nbsp;|&nbsp; dzien %(dayno)s z %(days)s.</p>

<div class="kpis">
  <div class="kpi"><div class="l">Wplacone</div><div class="v">%(dep)s</div><div class="n">%(ndep)s wplat</div></div>
  <div class="kpi"><div class="l">Wartosc portfela</div><div class="v">%(val)s</div><div class="n">netto po podatku: %(valnet)s</div></div>
  <div class="kpi"><div class="l">Zysk / strata</div><div class="v %(gaincls)s">%(gain)s</div><div class="n">%(gainpct)s od wplat</div></div>
  %(benchkpi)s
  <div class="kpi"><div class="l">Gotowka</div><div class="v">%(cash)s</div></div>
  <div class="kpi"><div class="l">Otwarte pozycje</div><div class="v">%(npos)s</div></div>
  <div class="kpi"><div class="l">Transakcje</div><div class="v">%(ntr)s</div><div class="n">skutecznosc %(wr).0f%%</div></div>
  <div class="kpi"><div class="l">Max obsuniecie</div><div class="v down">%(mdd).1f%%</div></div>
  <div class="kpi"><div class="l">Podatek w rezerwie</div><div class="v">%(tax)s</div><div class="n">19%% Belki od zyskow</div></div>
</div>

<h2>Kapital w czasie (PLN)</h2>
<div class="card"><canvas id="eq" height="110"></canvas></div>

<h2>Otwarte pozycje</h2>
<div class="card scroll"><table>
<tr><th>Spolka</th><th>Akcje</th><th>Wejscie</th><th>Stop</th><th>Target</th><th>Otwarte</th></tr>
%(posrows)s</table></div>

<h2>Historia transakcji (ostatnie 40)</h2>
<div class="card scroll"><table>
<tr><th>Spolka</th><th>Wejscie</th><th>Wyjscie</th><th>Akcje</th><th>Cena wej.</th><th>P&amp;L</th><th>R</th><th>Powod wyjscia</th></tr>
%(traderows)s</table></div>

<h2>Wplaty</h2>
<div class="card scroll"><table>
<tr><th>Data</th><th>PLN</th><th>Kurs USD/PLN</th><th>USD po przewalutowaniu</th><th>Koszt przewalutowania</th></tr>
%(deprows)s</table></div>

<h2>Dziennik decyzji (ostatnie 60)</h2>
<div class="card scroll"><table>
<tr><th>Czas (ET)</th><th>Decyzja</th><th>Spolka</th><th>Szczegoly</th></tr>
%(decrows)s</table></div>

<div class="warn"><b>Zastrzezenia.</b> To jest symulacja edukacyjna, nie porada inwestycyjna i nie
obietnica zysku. Dane cenowe pochodza z darmowego, nieoficjalnego Yahoo i moga byc opoznione.
Wykonanie zlecen jest symulowane (poslizg + koszt przewalutowania + podatek Belki), a nie prawdziwe.
Wiekszosc osob handlujacych srodziennie traci pieniadze. Kwoty sa w PLN; wartosci USD przeliczane
kursem USD/PLN. Szczegoly zalozen: <code>docs/XTB-ZALOZENIA.md</code>.</div>

<footer>Repo: xtb-daytrader-sim &nbsp;|&nbsp; silnik: Python (biblioteka standardowa)
&nbsp;|&nbsp; uruchamiane automatycznie przez GitHub Actions (co 15 min w sesji USA + raz dziennie po zamknieciu).
Statystyki: transakcji %(ntr)s, wygranych %(nwin)s, przegranych %(nloss)s,
profit factor %(pf)s, sredni czas trzymania %(hold).0f min.</footer>
</div>
<script>
const D=%(data)s;
new Chart(document.getElementById('eq'),{type:'line',data:{labels:D.dates,
 datasets:[
  {label:'Wartosc portfela',data:D.eq,borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,.12)',fill:true,tension:.25,pointRadius:0,borderWidth:2},
  {label:'Wplacone',data:D.dep,borderColor:'#8b949e',borderDash:[5,4],pointRadius:0,borderWidth:1.5},
  {label:D.bench,data:D.benchv,borderColor:'#3fb950',pointRadius:0,borderWidth:1.5}
 ]},
 options:{responsive:true,interaction:{mode:'index',intersect:false},
  plugins:{legend:{labels:{color:'#8b949e'}}},
  scales:{x:{ticks:{color:'#8b949e',maxTicksLimit:10},grid:{color:'#21262d'}},
          y:{ticks:{color:'#8b949e'},grid:{color:'#21262d'}}}}});
</script>
</body></html>""" % {
        "title": sc.get("name", "XTB Day Trader Sim"),
        "css": CSS,
        "start": sim.get("start_date", "—"),
        "end": sim.get("end_date", "—"),
        "days": sc.get("days", ""),
        "updated": store.ny_stamp(),
        "dayno": sim.get("day_count", 0),
        "dep": _pln(dep), "ndep": len(sim.get("deposits") or []),
        "val": _pln(val), "valnet": _pln(val_net),
        "gain": _pln(gain), "gaincls": "up" if gain > 0 else "down", "gainpct": _pct(gain_pct),
        "benchkpi": bench_kpi,
        "cash": _usd(last.get("cash_usd") if last else 0),
        "npos": len(positions), "ntr": len(trades), "wr": win_rate,
        "mdd": mdd, "tax": _pln(sim.get("tax_reserve_pln") or 0),
        "posrows": pos_rows, "traderows": trade_rows, "deprows": dep_rows, "decrows": dec_rows,
        "nwin": len(wins), "nloss": len(losses),
        "pf": ("%.2f" % pf) if pf else "—", "hold": avg_hold,
        "data": json.dumps({"dates": labels, "eq": series_eq, "dep": series_dep,
                            "bench": cfg["benchmark"]["label"], "benchv": series_bench}),
    }

    out = store.p(store.ROOT, "docs", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def _read_lines(path: str) -> list[str]:
    import os
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [l for l in f.read().splitlines() if l.strip()]


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sim import book, engine
    cfg = book.load_cfg()
    sim = engine.ensure_init(book.load_sim(), cfg)
    print(build(sim, cfg))

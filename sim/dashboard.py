"""Panel: jedna strona, ktora tlumaczy co sie stalo i dlaczego.

Zasady projektowe:
  * kazde wyjasnienie to najwyzej dwa krotkie zdania,
  * liczba zawsze obok slowa, ktore ja tlumaczy,
  * brak zargonu bez definicji (stopka + slowniczek),
  * zero zewnetrznych bibliotek (SVG + CSS), zeby dzialalo offline i na zrzucie PNG.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sim import insights, market, news, plain, store, ui
    from sim.ui import esc, num, pct, pln, usd
else:
    from . import insights, market, news, plain, store, ui
    from .ui import esc, num, pct, pln, usd

# ------------------------------------------------------------------ style
CSS = """
:root{
  --paper:#FAF9F6; --ink:#101418; --muted:#6A7079; --line:#E3E0D8;
  --up:#0E6B4F; --down:#A32017; --acc:#1D3F8F; --sand:#F1EEE6; --card:#FFFFFF;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:15px;line-height:1.55;font-feature-settings:"tnum" 0;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:36px 30px 90px}
.serif{font-family:Georgia,"Iowan Old Style","Times New Roman",serif;letter-spacing:-0.01em}
.mono{font-variant-numeric:tabular-nums}
a{color:var(--acc);text-decoration:none}
a:hover{text-decoration:underline}

/* --- masthead --- */
.mast{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;
  border-bottom:2px solid var(--ink);padding-bottom:14px}
.kicker{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.mast h1{font-size:31px;margin:0;line-height:1.1}
.mast .right{text-align:right;font-size:12.5px;color:var(--muted);white-space:nowrap}
.pill{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11px;
  letter-spacing:.08em;text-transform:uppercase;border:1px solid var(--line);background:#fff}
.pill.open{border-color:#BFE0D2;background:#EAF6F0;color:var(--up)}
.pill.shut{color:var(--muted)}

/* --- kpi --- */
.kpis{display:grid;grid-template-columns:1.35fr 1fr 1fr 1fr;gap:0;margin:26px 0 8px;
  border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.kpi{padding:18px 20px 18px 0;border-right:1px solid var(--line)}
.kpi:last-child{border-right:0;padding-right:0}
.kpi .l{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.kpi .v{font-size:30px;line-height:1.15;margin-top:6px;font-weight:400}
.kpi .v.big{font-size:38px}
.kpi .n{font-size:12.5px;color:var(--muted);margin-top:4px}
.up{color:var(--up)}.down{color:var(--down)}

/* --- sekcje --- */
section{margin-top:44px}
.sec-h{display:flex;align-items:baseline;gap:12px;margin-bottom:16px}
.sec-h .idx{font-size:11px;letter-spacing:.14em;color:var(--muted);padding-top:3px}
.sec-h h2{font-size:20px;margin:0;font-weight:600;letter-spacing:-0.01em}
.sec-h .sub{font-size:13px;color:var(--muted);margin-left:auto;text-align:right;max-width:46%}

/* --- karty --- */
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}

/* --- os czasu --- */
.tl{list-style:none;margin:0;padding:0}
.tl li{position:relative;padding:0 0 18px 26px;border-left:1px solid var(--line)}
.tl li:last-child{border-left-color:transparent;padding-bottom:0}
.tl li:before{content:"";position:absolute;left:-5px;top:5px;width:9px;height:9px;
  border-radius:50%;background:#fff;border:2px solid var(--muted)}
.tl li.open:before{border-color:var(--up);background:var(--up)}
.tl li.close:before{border-color:var(--acc);background:var(--acc)}
.tl li.skip:before,.tl li.block:before{border-color:#C9C5BA;background:#fff}
.tl li.deposit:before{border-color:var(--ink);background:var(--ink)}
.tl .t{font-size:12px;color:var(--muted)}
.tl .a{font-weight:600;font-size:14.5px}
.tl .w{font-size:13.5px;color:#3A3F45;margin-top:2px}

/* --- pozycje --- */
.pos{display:flex;flex-direction:column;gap:10px}
.pos .top{display:flex;justify-content:space-between;align-items:baseline}
.pos .sym{font-size:19px;font-weight:600;letter-spacing:-.01em}
.pos .qty{font-size:12.5px;color:var(--muted)}
.pos .row{display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted)}
.pos .row b{color:var(--ink);font-weight:600}
.pos .rng{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:-4px}

/* --- tabela --- */
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
  text-align:left;font-weight:500;padding:0 10px 8px 0;border-bottom:1px solid var(--line)}
td{padding:9px 10px 9px 0;border-bottom:1px solid #F0EDE6;vertical-align:top}
tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;padding-right:0}

/* --- lejek --- */
.fn{display:flex;flex-direction:column;gap:7px}
.fn-row{display:grid;grid-template-columns:1fr 240px;gap:14px;align-items:center}
.fn-bar{background:#1A4731;color:#fff;border-radius:7px;
  padding:9px 14px;display:flex;align-items:baseline;gap:10px;min-width:150px}
.fn-val{font-size:19px;font-weight:600}
.fn-lab{font-size:12.5px;opacity:.9}
.fn-note{font-size:12.5px;color:var(--muted)}

/* --- obserwacje --- */
.obs .v{font-size:26px;font-weight:400;margin:2px 0 6px}
.obs .t{font-size:13.5px;color:#3A3F45}
.obs .cap{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.obs .n{font-size:11px;color:var(--muted);margin-top:8px}

/* --- wiadomosci --- */
.news-item{display:grid;grid-template-columns:52px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid #F0EDE6}
.news-item:last-child{border-bottom:0}
.news-item .tm{font-size:12px;color:var(--muted)}
.news-item .ti{font-size:13.5px;line-height:1.4}
.news-item .mt{font-size:11.5px;color:var(--muted);margin-top:3px}
.tag{display:inline-block;font-size:10.5px;letter-spacing:.04em;padding:1px 7px;border-radius:999px;
  background:var(--sand);color:#4A4F56;margin-right:5px}
.tag.risk{background:#FBEAE8;color:var(--down)}

/* --- kroki --- */
.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;counter-reset:s}
.step{border-top:2px solid var(--ink);padding-top:10px}
.step .n{font-size:11px;color:var(--muted);letter-spacing:.1em}
.step .h{font-weight:600;font-size:14px;margin:4px 0 3px}
.step .d{font-size:12.5px;color:#3A3F45;line-height:1.45}

/* --- slowniczek --- */
.gloss{display:grid;grid-template-columns:1fr 1fr;gap:10px 28px}
.gloss div{font-size:12.5px;line-height:1.45}
.gloss b{font-size:12.5px}
.gloss span{color:#3A3F45}

/* --- stopka --- */
footer{margin-top:52px;border-top:1px solid var(--line);padding-top:18px;
  font-size:12px;color:var(--muted);line-height:1.6}
.empty{color:var(--muted);font-size:13.5px;padding:14px 0}
.ax{font-size:10px;fill:#8A9099}
.lg{font-size:11px;fill:#6A7079}
.lastv{font-size:12px;fill:#101418;font-weight:600}
.ring{display:flex;align-items:center;gap:10px}
.ring-v{font-size:15px;font-weight:600;fill:#101418}
.ring-s{font-size:11.5px;color:var(--muted);line-height:1.35}
.bignum{font-size:24px;font-weight:600}
.tag2{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;padding:2px 8px;
  border-radius:4px;border:1px solid var(--line);color:var(--muted)}
.tag2.buy{border-color:#BFE0D2;background:#EAF6F0;color:var(--up)}
.tag2.sell{border-color:#CBD6F0;background:#EDF1FB;color:var(--acc)}
.tag2.no{background:var(--sand)}
.tag2.cash{border-color:#DAD5C8;background:#F7F5EF;color:#4A4F56}
.nums{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;padding-top:12px;border-top:1px solid #F0EDE6}
.nums div{font-size:11px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.nums b{display:block;font-size:14px;color:var(--ink);letter-spacing:0;text-transform:none;font-weight:600}
@media (max-width:860px){
  .kpis{grid-template-columns:1fr 1fr}
  .kpi{border-bottom:1px solid var(--line)}
  .grid2,.grid3,.grid4,.gloss,.steps{grid-template-columns:1fr}
  .fn-row{grid-template-columns:1fr}
  .wrap{padding:22px 16px 60px}
}
"""


# ------------------------------------------------------------------ pomocnicze
def _f(x, d: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def _load_decisions() -> list[dict]:
    if not os.path.exists(store.DECISIONS):
        return []
    out = []
    with open(store.DECISIONS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def _today_row(equity: list[dict]) -> dict:
    if not equity:
        return {}
    return equity[-1]


def _et_hhmm(iso) -> str:
    """ISO UTC z feedu -> godzina w Nowym Jorku (tak jak reszta panelu)."""
    try:
        from datetime import timezone
        from . import session as ses
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ses.NY).strftime("%H:%M")
    except Exception:  # noqa: BLE001
        return str(iso)[11:16]


def _price(sym: str) -> float | None:
    try:
        return market.last_price(sym)[0]
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ sekcje
def _masthead(sim: dict, cfg: dict, equity: list[dict]) -> str:
    now = datetime.now()
    is_open = False
    try:
        from . import session as ses
        is_open = ses.is_open()
    except Exception:  # noqa: BLE001
        pass
    day = int(sim.get("day_count") or 0)
    total = int(cfg["simulation"]["days"])
    pill = ('<span class="pill open">rynek otwarty</span>' if is_open
            else '<span class="pill shut">rynek zamkniety</span>')
    last = (_today_row(equity) or {}).get("date") or "—"
    return f'''<div class="mast">
  <div>
    <div class="kicker">Dziennik symulacji &middot; rachunek XTB w zlotowkach</div>
    <h1 class="serif">XTB Day Trader</h1>
  </div>
  <div class="right">
    {pill}<br>
    dzien <b>{day}</b> z {total}<br>
    dane na: {esc(last)}
  </div>
</div>'''


def _kpis(sim: dict, cfg: dict, equity: list[dict], trades: list[dict]) -> str:
    dep = _f(sim.get("deposits_pln_total"))
    last = _today_row(equity)
    val = _f(last.get("equity_pln"))
    val_net = _f(last.get("equity_pln_net"))
    bench = _f(last.get("bench_pln")) if last.get("bench_pln") not in (None, "") else None
    gain = val - dep if dep else 0.0
    gain_pct = (gain / dep * 100) if dep else 0.0
    cls = "up" if gain > 0 else ("down" if gain < 0 else "")
    bench_txt = pln(bench) if bench else "—"
    bench_sub = (pct((bench - dep) / dep * 100 if dep else 0) + " od wplat") if bench and dep else "brak danych"
    n_tr = len(trades)
    return f'''<div class="kpis">
  <div class="kpi">
    <div class="l">Wartosc portfela</div>
    <div class="v big serif">{pln(val) if dep else "—"}</div>
    <div class="n">po odlozeniu podatku: {pln(val_net) if dep else "—"}</div>
  </div>
  <div class="kpi">
    <div class="l">Zysk / strata</div>
    <div class="v serif {cls}">{pct(gain_pct) if dep else "—"}</div>
    <div class="n">{pln(gain) if dep else "—"} od wplat</div>
  </div>
  <div class="kpi">
    <div class="l">Wplacilem</div>
    <div class="v serif">{pln(dep) if dep else "0 zl"}</div>
    <div class="n">{len(sim.get("deposits") or [])} wplat &middot; {n_tr} transakcji</div>
  </div>
  <div class="kpi">
    <div class="l">{esc(cfg["benchmark"]["label"])} zamiast tego</div>
    <div class="v serif">{bench_txt}</div>
    <div class="n">{bench_sub}</div>
  </div>
</div>'''


def _today_balance(decisions: list[dict], trades: list[dict]) -> str:
    day = store.ny_stamp()[:10]
    td = [d for d in decisions if str(d.get("ts_ny", "")).startswith(day)]
    opened = [d for d in td if d.get("decision") == "open"]
    closed = [d for d in td if d.get("decision") == "close"]
    skipped = [d for d in td if d.get("decision") in ("skip", "block")]
    scanned = max([int(d.get("numbers", {}).get("scanned") or 0) for d in td
                   if d.get("decision") == "scan"] or [0])
    read = max([int(d.get("read") or 0) for d in td if d.get("decision") == "news_summary"] or [0])
    read = max(read, int((news.today() or {}).get("read") or 0))
    pnl = sum(_f(d.get("numbers", {}).get("pnl")) for d in closed)
    items = [
        ("Sprawdzil spolek", str(scanned) if scanned else "—", "na liscie XTB"),
        ("Przeczytal naglowkow", str(read) if read else "0", "wiadomosci z rynku"),
        ("Kupil", str(len(opened)), "nowych pozycji"),
        ("Sprzedal", str(len(closed)), "zamknietych"),
        ("Odpuscil", str(len(skipped)), "okazji odrzuconych"),
        ("Wynik dnia", (usd(pnl) if closed else "—"), "na zamknietych"),
    ]
    cells = "".join(f'''<div class="kpi" style="border-right:0;padding:10px 0">
      <div class="l">{esc(l)}</div>
      <div class="v" style="font-size:22px">{esc(v)}</div>
      <div class="n">{esc(s)}</div></div>''' for l, v, s in items)
    return f'<div class="grid3" style="gap:0 26px">{cells}</div>'


def _timeline(actions: list[dict]) -> str:
    if not actions:
        return ('<div class="empty">Dzis bot nie podjal jeszcze zadnej decyzji. '
                'Pierwsze wpisy pojawia sie po otwarciu sesji w USA (15:30 czasu polskiego).</div>')
    li = []
    for a in actions:
        kind = a.get("kind") or ""
        title = a.get("title") or ""
        why = a.get("why") or ""
        if not title:
            continue
        li.append(f'''<li class="{esc(kind)}">
  <div class="t">{esc(a.get("time") or "")}</div>
  <div class="a">{esc(title)}</div>
  {f'<div class="w">{esc(why)}</div>' if why else ''}
</li>''')
    return '<ul class="tl">' + "".join(li) + "</ul>"


def _positions(sim: dict) -> str:
    open_pos = sim.get("open") or {}
    if not open_pos:
        return ('<div class="card"><div class="empty">Zadnej otwartej pozycji. '
                'Bot konczy dzien zawsze na zero — nic nie zostaje na noc.</div></div>')
    cards = []
    for p in open_pos.values():
        sym = str(p.get("symbol"))
        qty = _f(p.get("qty"))
        entry = _f(p.get("entry"))
        stop = _f(p.get("stop"))
        target = _f(p.get("target"))
        px = _price(sym)
        cur = px if px else entry
        upl = (cur - entry) * qty
        upl_cls = "up" if upl > 0 else ("down" if upl < 0 else "")
        cur_txt = usd(cur) if px else "brak ceny"
        cards.append(f'''<div class="card pos">
  <div class="top">
    <div><span class="sym">{esc(sym)}</span>
      <span class="qty">&nbsp;{num(qty)} szt. &middot; od {esc(str(p.get("opened_at"))[11:16])}</span></div>
    <div class="{upl_cls}" style="font-weight:600">{usd(upl)}</div>
  </div>
  <div class="row"><span>kupione po</span><b>{usd(entry)}</b></div>
  <div class="row"><span>teraz</span><b>{cur_txt}</b></div>
  {ui.r_gauge(stop, entry, target, cur)}
  <div class="rng"><span>stop {usd(stop)}</span><span>cel {usd(target)}</span></div>
  <div class="row" style="border-top:1px solid #F0EDE6;padding-top:8px">
    <span>gdy spadnie do stopu trace</span><b class="down">{usd((stop - entry) * qty)}</b></div>
  <div class="row"><span>gdy dojdzie do celu zyskam</span><b class="up">{usd((target - entry) * qty)}</b></div>
</div>''')
    return '<div class="grid2">' + "".join(cards) + "</div>"


def _closed_today(trades: list[dict]) -> str:
    day = store.ny_stamp()[:10]
    today = [t for t in trades if str(t.get("close_ts_ny") or "").startswith(day)]
    if not today:
        return ""
    rows = []
    for t in today:
        pnl = _f(t.get("pnl_usd"))
        cls = "up" if pnl > 0 else ("down" if pnl < 0 else "")
        r = t.get("r_multiple")
        rows.append(
            f'<tr><td><b>{esc(t.get("symbol"))}</b></td>'
            f'<td>{esc(str(t.get("open_ts_ny"))[11:16])} → {esc(str(t.get("close_ts_ny"))[11:16])}</td>'
            f'<td>{usd(t.get("entry_usd"))} → {usd(t.get("exit_usd"))}</td>'
            f'<td>{num(t.get("qty"))}</td>'
            f'<td class="{cls}"><b>{usd(pnl)}</b></td>'
            f'<td>{(("%+.2f R" % _f(r)).replace(".", ",") if r not in (None, "") else "—")}</td>'
            f'<td>{esc(plain.exit_short(t.get("exit_reason")))}</td></tr>')
    total = sum(_f(t.get("pnl_usd")) for t in today)
    tcls = "up" if total > 0 else ("down" if total < 0 else "")
    return f'''<div class="card" style="margin-top:16px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px">
    <div style="font-weight:600">Zamkniete dzisiaj <span style="color:var(--muted);font-weight:400">({len(today)})</span></div>
    <div class="{tcls}" style="font-weight:600">{usd(total)}</div>
  </div>
  <table>
    <tr><th>Spolka</th><th>Czas</th><th>Cena</th><th>Szt.</th><th class="r">Wynik</th><th class="r">R</th><th>Powod wyjscia</th></tr>
    {''.join(rows)}
  </table>
</div>'''


def _decision_card(d: dict) -> str:
    kind = d.get("decision")
    badge = {"open": ("buy", "kupno"), "close": ("sell", "sprzedaz"),
             "deposit": ("cash", "wplata")}.get(kind, ("no", "odpuszczono"))
    n = d.get("numbers") or {}
    rows = []
    if kind == "open":
        rows = [("wejscie", usd(n.get("entry"))), ("stop", usd(n.get("stop"))),
                ("cel", usd(n.get("target"))), ("max strata", usd(n.get("max_loss")))]
    elif kind == "close":
        r = n.get("r")
        rows = [("wejscie", usd(n.get("entry"))), ("wyjscie", usd(n.get("exit"))),
                ("wynik", usd(n.get("pnl"))), ("w jednostkach R", ("%+.2f R" % _f(r)).replace(".", ",") if r not in (None, "") else "—")]
    elif kind == "deposit":
        rows = [("wplacone", pln(n.get("pln"))), ("kurs USD/PLN", num(n.get("rate"), 4)),
                ("otrzymane", usd(n.get("usd")))]
    else:
        return ""
    nums = "".join(f'<div>{esc(l)}<b>{esc(v)}</b></div>' for l, v in rows)
    return f'''<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
    <span class="tag2 {badge[0]}">{badge[1]}</span>
    <span style="font-size:11.5px;color:var(--muted)">{esc(str(d.get("ts_ny"))[11:16])}</span>
  </div>
  <div style="font-weight:600;font-size:16px;margin:10px 0 4px">{esc(d.get("title") or "")}</div>
  <div style="font-size:13.5px;color:#3A3F45;line-height:1.5">{esc(d.get("why") or "")}</div>
  <div class="nums">{nums}</div>
</div>'''


def _decisions(decisions: list[dict]) -> str:
    day = store.ny_stamp()[:10]
    td = [d for d in decisions if str(d.get("ts_ny", "")).startswith(day)]
    picks = [d for d in td if d.get("decision") in ("open", "close", "deposit")]
    if not picks:
        picks = [d for d in td if d.get("decision") == "block"][:2]
    if not picks:
        picks = [d for d in reversed(decisions) if d.get("decision") in ("open", "close", "deposit")][:2]
    if not picks:
        return ('<div class="card"><div class="empty">Jeszcze nic nie kupilem ani nie sprzedalem. '
                'Gdy pojawi sie pierwsza decyzja, zobaczysz tu powod w jednym zdaniu.</div></div>')
    cards = [c for c in (_decision_card(d) for d in picks[:4]) if c]
    return '<div class="grid2">' + "".join(cards) + "</div>"


def _funnel_section(sim: dict, cfg: dict) -> str:
    f = insights.funnel(sim)
    steps = [
        ("5 943", "spolek w USA", "tyle widzi skaner skilla - caly rynek akcji USA"),
        (num(f["watched"]), "na mojej liscie", "tylko te dostepne w XTB jako akcje realne"),
        (num(f["signals_total"]), "sygnalow lacznie", "cena przebila poranny szczyt i zamknela sie nad nim"),
        (num(f["checked"]), "sprawdzonych", "z wiadomosciami, stopem i limitem straty"),
        (num(f["trades"]), "transakcji", "tyle przeszlo wszystkie filtry"),
    ]
    note = ""
    if f["trades"]:
        note = (f'<div style="margin-top:14px;font-size:13px;color:var(--muted)">'
                f'Na kazda transakcje przypadalo {f["skipped"] + f["blocked"]} odrzuconych okazji. '
                f'To nie awaria — to jest metoda.</div>')
    return ui.funnel(steps) + note


def _lessons(sim: dict) -> str:
    obs = insights.observations(sim)
    if not obs:
        return ('<div class="card"><div class="empty">Za malo transakcji, zeby wyciagac wnioski. '
                'Obserwacje pojawia sie po kilku rozegranych dniach — nie zmyslam ich na zapas.</div></div>')
    cards = []
    for o in obs[:6]:
        tone = o.get("tone")
        cls = "up" if tone == "up" else ("down" if tone == "down" else "")
        cards.append(f'''<div class="card obs">
  <div class="cap">{esc(o["title"])}</div>
  <div class="v {cls}">{esc(o["value"])}</div>
  <div class="t">{esc(o["text"])}</div>
  <div class="n">na podstawie {o["n"]} obserwacji</div>
</div>''')
    return '<div class="grid3">' + "".join(cards) + "</div>"


def _news_section() -> str:
    t = news.today()
    items = list(t.get("items") or [])
    if not items:
        return ('<div class="card"><div class="empty">Dzis bot nie czytal jeszcze wiadomosci. '
                'Czyta je dopiero, gdy ma kandydata do kupna — nie czyta dla samego czytania.</div></div>')
    items = sorted(items, key=lambda i: str(i.get("time") or ""), reverse=True)[:10]
    rows = []
    for it in items:
        tags = []
        if it.get("tags"):
            for tg in str(it["tags"]).split():
                tags.append(f'<span class="tag{" risk" if it.get("risk") else ""}">{esc(tg)}</span>')
        impact = it.get("impact") or ""
        imp = (f' &middot; <b>{esc(impact)}</b>' if impact and impact != "nie zmienil decyzji"
               else (' &middot; bez wplywu na decyzje' if impact else ""))
        rows.append(f'''<div class="news-item">
  <div class="tm">{esc(_et_hhmm(it.get("time")))}</div>
  <div>
    <div class="ti"><b>{esc(it.get("ticker") or "")}</b> {esc(it.get("title") or "")}</div>
    <div class="mt">{''.join(tags)} {esc(it.get("source") or "")}{imp}</div>
  </div>
</div>''')
    head = (f'<div style="font-size:13px;color:var(--muted);margin-bottom:4px">'
            f'Dzis przeczytalem <b>{len(t.get("items") or [])}</b> naglowkow.'
            f'{" " + str(t.get("blocked")) + " z nich wstrzymalo zakup." if t.get("blocked") else ""}</div>')
    return '<div class="card">' + head + "".join(rows) + "</div>"


def _how_it_works() -> str:
    steps = [
        ("01", "Skan", "Przegladam liste spolek i szukam ceny, ktora przebila maksimum pierwszych 15 minut sesji."),
        ("02", "Wiadomosci", "Czytam naglowki o kandydacie. Cos groznego = odpuszczam, zanim zaryzykuje."),
        ("03", "Plan", "Przed wejsciem ustalam stop (gdzie sie mylilem) i cel (kiedy biore zysk)."),
        ("04", "Wielkosc", "Licze, ile akcji kupic, zeby max strata to 1% kapitalu. Nie na oko."),
        ("05", "Koniec dnia", "Zamykam wszystko przed 16:00 w Nowym Jorku. Zero trzymania na noc."),
    ]
    cells = "".join(f'''<div class="step"><div class="n">{n}</div>
      <div class="h">{esc(h)}</div><div class="d">{esc(d)}</div></div>''' for n, h, d in steps)
    return f'<div class="steps">{cells}</div>'


def _glossary() -> str:
    cells = "".join(f'<div><b>{esc(k)}</b> <span>— {esc(v)}</span></div>' for k, v in plain.GLOSSARY)
    return f'<div class="card"><div class="gloss">{cells}</div></div>'


def _footer(sim: dict, cfg: dict) -> str:
    return f'''<footer>
  <b>Jak to policzone.</b> Start {pln(cfg["simulation"]["start_capital_pln"])},
  potem {pln(cfg["simulation"]["monthly_deposit_pln"])} w pierwszym dniu handlowym kazdego miesiaca
  przez {cfg["simulation"]["days"]} dni. Koszty: przewalutowanie {num(cfg["costs"]["fx_cost_pct"], 1)}%,
  poslizg {num(cfg["costs"]["slippage_bps"], 0)} pb na transakcje, podatek Belki
  {num(cfg["costs"]["tax_on_gains_pct"], 0)}% od zysku (odkladany w rezerwie).
  Ceny: darmowe, nieoficjalne Yahoo, opoznione o kilkadziesiat sekund.
  Zlecenia sa <b>symulowane</b> — nic nie idzie do XTB.
  <br><br>
  <b>To nie jest porada inwestycyjna.</b> Symulacja pokazuje metode, nie obiecuje wyniku.
  Wiekszosc osob handlujacych w ciagu dnia traci pieniadze.
  Zalozenia: <code>docs/XTB-ZALOZENIA.md</code> &middot; dziennik decyzji: <code>sim/state/decisions.jsonl</code>
  &middot; transakcje: <code>sim/state/trades.csv</code>
</footer>'''


def _empty_intro(cfg: dict) -> str:
    sc = cfg["simulation"]
    return f'''<div class="card" style="margin-top:26px;background:#FCFBF7">
  <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">Zanim ruszy</div>
  <div class="serif" style="font-size:22px;margin:8px 0 6px">Symulacja startuje {sc["start_date"]}</div>
  <div style="font-size:13.5px;color:#3A3F45;max-width:620px">
    Pierwszego dnia handlowego bot wplaci {pln(sc["start_capital_pln"])}, przewalutuje je na dolary
    i zacznie skanowac rynek. Pierwsze decyzje zobaczysz po 15:30 czasu polskiego.
    Do tego czasu panel jest celowo pusty — nic tu nie jest zmyslane.
  </div>
</div>'''


# ------------------------------------------------------------------ build
def build(sim: dict, cfg: dict) -> str:
    equity = store.read_csv(store.EQUITY)
    trades = store.read_csv(store.TRADES)
    decisions = _load_decisions()
    actions = insights.today_actions(sim)
    dep = _f(sim.get("deposits_pln_total"))

    body = []
    body.append(_masthead(sim, cfg, equity))
    body.append(_kpis(sim, cfg, equity, trades))
    if not dep and not trades:
        body.append(_empty_intro(cfg))

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">01</span><h2>Dzis w skrocie</h2>
    <span class="sub">Co bot zrobil i dlaczego — po kolei, bez zargonu</span></div>
  <div class="grid2" style="grid-template-columns:1.5fr 1fr;gap:16px">
    <div class="card">{_timeline(actions)}</div>
    <div class="card">{_today_balance(decisions, trades)}</div>
  </div>
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">02</span><h2>Kapital w czasie</h2>
    <span class="sub">Zielona linia to Twoje pieniadze. Przerywana — ile wplaciles</span></div>
  <div class="card" style="padding:14px 10px 6px">{ui.line_chart(equity)}</div>
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">03</span><h2>Pozycje</h2>
    <span class="sub">Kropka na pasku pokazuje, gdzie cena jest miedzy stopem a celem</span></div>
  {_positions(sim)}
  {_closed_today(trades)}
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">04</span><h2>Dlaczego podjal te decyzje</h2>
    <span class="sub">Kazda decyzja z powodem i liczbami</span></div>
  {_decisions(decisions)}
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">05</span><h2>Lejek decyzji</h2>
    <span class="sub">Z tysiecy spolek zostaje kilka transakcji — i to jest celowe</span></div>
  {_funnel_section(sim, cfg)}
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">06</span><h2>Czego sie nauczyl</h2>
    <span class="sub">Wnioski z jego wlasnych transakcji, nie z obietnic</span></div>
  {_lessons(sim)}
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">07</span><h2>Co czytal</h2>
    <span class="sub">Naglowki, ktore widzial przed decyzja — i czy cos zmienily (godziny czasu Nowego Jorku)</span></div>
  {_news_section()}
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">08</span><h2>Jak to dziala</h2>
    <span class="sub">Ta sama petla kazdego dnia handlowego</span></div>
  {_how_it_works()}
</section>''')

    body.append(f'''<section>
  <div class="sec-h"><span class="idx">09</span><h2>Slowniczek</h2>
    <span class="sub">Kazde pojecie jednym zdaniem</span></div>
  {_glossary()}
</section>''')

    body.append(_footer(sim, cfg))

    html = f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>XTB Day Trader — dziennik symulacji</title>
<style>{CSS}</style></head>
<body><div class="wrap">
{''.join(body)}
</div></body></html>'''

    out = store.p(store.ROOT, "docs", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sim import book, engine

    _cfg = book.load_cfg()
    _sim = engine.ensure_init(book.load_sim(), _cfg)
    print(build(_sim, _cfg))

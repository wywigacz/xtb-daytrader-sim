"""Panel: jedna strona, która tłumaczy co się stalo i dlaczego.

Projekt oparty na zmierzonych regulach, nie na wyczuciu:
  * SKALA TYPOGRAFII: dokładnie 6 rozmiarów (12/14/16/20/28/44 px).
    Wczesniej było ich 11, w tym 12,5 px uzywane 53 razy.
  * JEDEN EKRAN NA PODSUMOWANIE: najważniejsze liczby, wykres i dzisiejsze
    decyzje mieszcza się nad zgieciem (zasada "tell a story on one screen").
    Szczegóły są nizej, w dwoch kolumnach.
  * NAJWAZNIEJSZE NAJWIEKSZE: jedna liczba dominuje (44 px), pozostale są
    wyraźnie mniejsze - inaczej oko nie wie, na co patrzec.
  * LICZBY: duże wartości skracane ("110,4 tys. zl"), dokładne w drugiej linii.
  * KONTRAST: tekst pomocniczy 6,5:1 (WCAG AA wymaga 4,5:1).
  * TELEFON: brak przewijania w bok (tabele przewijaja się we własnym
    pojemniku), linki nawigacji maja 44 px wysokości.
  * ZERO zewnetrznych bibliotek: SVG + CSS, działa offline i na zrzucie PNG.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from sim import insights, market, news, plain, session as ses, store, ui
    from sim.ui import esc, num, pct, pln, pln_short, usd
else:
    from . import insights, market, news, plain, session as ses, store, ui
    from .ui import esc, num, pct, pln, pln_short, usd

CSS = """
:root{
  --paper:#FAF9F6; --ink:#0C1116; --muted:#55606E; --faint:#5F6875;
  --line:#E2DED5; --soft:#F3F1EB; --card:#FFFFFF;
  --up:#0B6B4A; --down:#A32017; --acc:#1D3F8F;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px 72px}
a{color:var(--acc);text-decoration:none}
a:hover{text-decoration:underline}
.serif{font-family:Georgia,"Iowan Old Style","Times New Roman",serif}

/* ---- skala typografii: 12 / 14 / 16 / 20 / 28 / 44 ---- */
.t-xs{font-size:12px}
.t-sm{font-size:14px}
.t-md{font-size:16px}
.t-lg{font-size:20px}
.t-xl{font-size:28px}
.t-2xl{font-size:44px}
.up{color:var(--up)}.down{color:var(--down)}.mut{color:var(--muted)}.faint{color:var(--faint)}
.lab{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}

/* ---- pasek nawigacji ---- */
.toc{position:sticky;top:0;z-index:30;background:rgba(250,249,246,.96);
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  border-bottom:1px solid var(--line);display:flex;gap:18px;align-items:center;
  overflow-x:auto;padding:0 20px;margin:0 -20px 8px;scrollbar-width:none}
.toc::-webkit-scrollbar{display:none}
.toc a{font-size:14px;color:var(--muted);white-space:nowrap;
  display:flex;align-items:center;min-height:44px;padding:0 2px}
.toc a:first-child{color:var(--ink);font-weight:600}
.toc a:hover{color:var(--ink)}

/* ---- nagłówek ---- */
.mast{display:flex;flex-wrap:wrap;gap:6px 20px;align-items:flex-end;
  justify-content:space-between;border-bottom:1px solid var(--ink);padding:12px 0 12px}
.mast h1{margin:0;font-size:20px;line-height:1.2;letter-spacing:-.01em}
.mast .right{font-size:14px;color:var(--muted);line-height:1.5}
.stat{display:inline-flex;align-items:center;gap:7px;font-size:12px;letter-spacing:.06em;
  text-transform:uppercase;font-weight:600;color:var(--muted)}
.stat i{width:8px;height:8px;border-radius:50%;background:#B9B3A6;display:block}
.stat.open i{background:var(--up);box-shadow:0 0 0 3px rgba(11,107,74,.16)}
/* pasek postępu symulacji - jedyna metryka z progiem */
.prog{height:4px;background:var(--soft);border-radius:3px;margin-top:7px;overflow:hidden}
.prog i{display:block;height:100%;background:var(--acc);border-radius:3px}

/* ---- podsumowanie: jeden ekran ---- */
section{margin-top:32px;scroll-margin-top:60px}
[id]{scroll-margin-top:60px}
.sum{margin-top:12px}
.hero{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:0;
  background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:0 22px;margin-top:20px}
.hero > div{padding:12px 16px 12px 0;border-right:1px solid var(--line)}
.hero > div:last-child{border-right:0;padding-right:0}
.hero .v{line-height:1.08;margin-top:3px}
.hero .n{font-size:14px;color:var(--muted);margin-top:6px}
.chart-card{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:12px 14px 4px;margin-top:12px}
.duo{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;margin-top:12px}
.duo .card{padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;
  min-width:0}   /* bez tego tabela z min-width rozpycha cała karte (pulapka grid min-width:auto) */
.grid2 > *{min-width:0}
.card h3{margin:0 0 10px;font-size:20px;font-weight:600}
.card h4{margin:0 0 10px;font-size:14px;font-weight:600;color:var(--muted);
  letter-spacing:.06em;text-transform:uppercase}

/* ---- os czasu ---- */
.tl{list-style:none;margin:0;padding:0}
.tl li{position:relative;padding:0 0 12px 22px;border-left:1px solid var(--line)}
.tl li:last-child{border-left-color:transparent;padding-bottom:0}
.tl li:before{content:"";position:absolute;left:-5.5px;top:5px;width:11px;height:11px;
  border-radius:50%;background:#fff;border:2px solid var(--faint)}
.tl li.open:before{border-color:var(--up);background:var(--up)}
.tl li.close:before{border-color:var(--acc);background:var(--acc)}
.tl li.deposit:before{border-color:var(--ink);background:var(--ink)}
.tl .t{font-size:12px;color:var(--faint)}
.tl .a{font-size:16px;font-weight:600}
.tl .w{font-size:14px;color:var(--muted);margin-top:2px}

/* ---- mini statystyki dnia ---- */
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:10px 16px}
.mini div .v{font-size:20px;font-weight:600;margin-top:2px}

/* ---- pozycje ---- */
.pos{display:flex;flex-direction:column;gap:8px}
.pos + .pos{margin-top:16px;padding-top:16px;border-top:1px solid var(--soft)}
.pos .top{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.pos .sym{font-size:20px;font-weight:600}
.pos .row{display:flex;justify-content:space-between;font-size:14px;color:var(--muted)}
.pos .row b{color:var(--ink);font-weight:600}
/* pasek stop-wejście-cel: HTML/CSS, żeby nic się nie rozciagalo na telefonie */
.rg{position:relative;height:28px;margin:4px 0 2px}
.rg-track{position:absolute;left:2%;right:2%;top:9px;height:5px;background:var(--line);border-radius:3px}
.rg-seg{position:absolute;top:9px;height:5px}
.rg-dot{position:absolute;top:6px;width:10px;height:10px;border-radius:50%;transform:translateX(-50%)}
.rg-entry{position:absolute;top:5px;width:13px;height:13px;border-radius:50%;background:#fff;
  border:2px solid var(--muted);transform:translateX(-50%)}
.rg-price{position:absolute;top:3px;width:17px;height:17px;border-radius:50%;border:2px solid #fff;
  transform:translateX(-50%)}
.rg-lab{position:absolute;top:17px;font-size:12px;color:var(--faint);transform:translateX(-50%);white-space:nowrap}

/* ---- tabele ---- */
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -4px;max-width:100%}
table{width:100%;border-collapse:collapse;font-size:14px;min-width:520px}
th{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
  text-align:left;font-weight:600;padding:0 12px 8px 0;border-bottom:1px solid var(--line)}
td{padding:10px 12px 10px 0;border-bottom:1px solid var(--soft);white-space:nowrap}
tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;padding-right:0;padding-left:18px}

/* ---- lejek ---- */
.fn{display:flex;flex-direction:column;gap:10px}
.fn-bar{background:#1A4731;color:#fff;border-radius:8px;padding:10px 14px;
  display:flex;align-items:baseline;gap:10px;min-width:140px}
.fn-val{font-size:20px;font-weight:600}
.fn-lab{font-size:14px;opacity:.92}
.fn-note{font-size:14px;color:var(--muted);margin-top:5px}

/* ---- karty decyzji ---- */
.dec{border:1px solid var(--line);border-radius:12px;padding:16px;background:var(--card)}
.dec + .dec{margin-top:12px}
.dec .hd{display:flex;justify-content:space-between;align-items:center;gap:10px}
.dec .ttl{font-size:16px;font-weight:600;margin:10px 0 4px}
.dec .why{font-size:14px;color:var(--muted)}
.nums{display:flex;flex-wrap:wrap;gap:16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--soft)}
.nums div{font-size:12px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.nums b{display:block;font-size:16px;color:var(--ink);letter-spacing:0;text-transform:none;margin-top:2px}
.tag{font-size:12px;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;
  border-radius:6px;border:1px solid var(--line);color:var(--muted)}
.tag.buy{border-color:#BEDFCE;background:#EAF6F0;color:var(--up)}
.tag.sell{border-color:#CBD6F0;background:#EDF1FB;color:var(--acc)}

/* ---- obserwacje ---- */
.obs{border-left:3px solid var(--line);padding-left:14px;margin-bottom:18px}
.obs .v{font-size:28px;font-weight:600;line-height:1.15}
.obs .t{font-size:14px;color:var(--muted);margin-top:4px}

/* ---- nagłówki ---- */
.news-item{display:grid;grid-template-columns:44px 1fr;gap:12px;padding:11px 0;
  border-bottom:1px solid var(--soft)}
.news-item:last-child{border-bottom:0}
.news-item .ti{font-size:14px;line-height:1.45}
.news-item .mt{font-size:12px;color:var(--faint);margin-top:3px}
.chip{display:inline-block;font-size:12px;padding:2px 8px;border-radius:999px;
  background:var(--soft);color:var(--muted);margin-right:6px}
.chip.risk{background:#FBEAE8;color:var(--down)}

/* ---- kroki ---- */
.steps{display:grid;grid-template-columns:repeat(2,1fr);gap:20px 28px}
.step .n{font-size:12px;color:var(--faint);letter-spacing:.08em}
.step .h{font-size:16px;font-weight:600;margin:4px 0 3px}
.step .d{font-size:14px;color:var(--muted)}

/* ---- słowniczek ---- */
.gloss{display:grid;grid-template-columns:1fr 1fr;gap:12px 28px}
.gloss b{font-size:14px}
.gloss span{font-size:14px;color:var(--muted)}

/* ---- wspolne ---- */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
/* wykres rysowany w dwoch szerokosciach: każda w naturalnym rozmiarze,
   wiec tekst na osi nigdy nie jest rozciagany ani pomniejszany */
.chart-narrow{display:none}
.empty{color:var(--muted);font-size:14px}
footer{margin-top:48px;border-top:1px solid var(--line);padding-top:18px;
  font-size:14px;color:var(--muted);line-height:1.6}
.ax{font-size:12px;fill:#5F6875}
.sv{font-size:12px}
.lastv{font-size:14px;fill:#0C1116;font-weight:600}
.gx{font-size:12px;fill:#5F6875}
code{background:var(--soft);padding:1px 6px;border-radius:4px;font-size:14px}
a.lnk{display:inline-block;padding:6px 0;min-height:26px}
.warn{background:#FFF8EC;border:1px solid #EBD9B4;border-radius:12px;
  padding:16px;font-size:14px;color:#5A4413;margin-top:18px}

@media (max-width:760px){
  .hero{grid-template-columns:1fr 1fr}
  .hero > div{border-right:0;border-bottom:1px solid var(--line);padding:14px 0}
  .hero > div:nth-last-child(-n+2){border-bottom:0}
  .duo,.grid2,.steps,.gloss{grid-template-columns:1fr}
  .mini{grid-template-columns:1fr 1fr}
  .chart-wide{display:none}
  .chart-narrow{display:block}
  .wrap{padding:0 20px 56px}
  .toc{margin:0 -20px 8px;padding:0 20px}
  .card{padding:18px}
}
"""

TOC = [
    ("podsumowanie", "Podsumowanie"),
    ("s1", "Pozycje"),
    ("s2", "Dlaczego"),
    ("s3", "Lejek"),
    ("s4", "Nauka"),
    ("s5", "Nagłówki"),
    ("s6", "Jak działa"),
    ("s7", "Słowniczek"),
]


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


def _last_row(equity: list[dict]) -> dict:
    return equity[-1] if equity else {}


def _et_hhmm(iso) -> str:
    try:
        from datetime import timezone
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ses.NY).strftime("%H:%M")
    except Exception:  # noqa: BLE001
        return str(iso)[11:16]


def _price(sym: str):
    try:
        return market.last_price(sym)[0]
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ naglowek
def _toc() -> str:
    return ('<nav class="toc">' + "".join('<a href="#%s">%s</a>' % (i, esc(t)) for i, t in TOC)
            + "</nav>")


def _masthead(sim: dict, cfg: dict, equity: list[dict]) -> str:
    now = ses.now_ny()
    is_open = ses.is_open(now)
    day = int(sim.get("day_count") or 0)
    total = int(cfg["simulation"]["days"])
    last = str(_last_row(equity).get("date") or "")
    pretty = (last[8:10] + "." + last[5:7] + "." + last[0:4]) if len(last) >= 10 else "—"
    pill = ('<span class="stat open"><i></i>rynek otwarty</span>' if is_open
            else '<span class="stat"><i></i>rynek zamknięty</span>')
    # postep symulacji: jedyna metryka z progiem, wiec dostaje pasek
    prog = max(min(day / max(total, 1) * 100, 100), 0.5)
    return f'''<div class="mast">
  <div>
    <div class="lab">Dziennik symulacji &middot; rachunek XTB w złotówkach</div>
    <h1 class="serif">XTB Day Trader</h1>
  </div>
  <div class="right">
    {pill} &nbsp; <b class="t-sm" style="color:var(--ink)">dzień {day} z {total}</b><br>
    dane na {esc(pretty)} &middot; zaktualizowano {esc(now.strftime('%d.%m.%Y %H:%M'))} (czas Nowego Jorku)
  </div>
</div>
<div class="prog" role="img" aria-label="Postep symulacji: dzień {day} z {total}">
  <i style="width:{prog:.1f}%"></i>
</div>'''


# ------------------------------------------------------------------ podsumowanie
def _hero(sim: dict, cfg: dict, equity: list[dict], trades: list[dict]) -> str:
    dep = _f(sim.get("deposits_pln_total"))
    last = _last_row(equity)
    val = _f(last.get("equity_pln"))
    val_net = _f(last.get("equity_pln_net"))
    bench = _f(last.get("bench_pln")) if last.get("bench_pln") not in (None, "") else None
    gain = val - dep if dep else 0.0
    gain_pct = (gain / dep * 100) if dep else 0.0
    cls = "up" if gain > 0 else ("down" if gain < 0 else "")
    short, exact = pln_short(val) if dep else ("—", "—")
    # gdy kwota jest mala, skrot rowna sie wartosci dokladnej - nie powtarzamy jej
    exact_line = exact if (exact != short) else ""
    tax = _f(sim.get("tax_reserve_pln"))
    # w karcie ma byc JEDNA liczba - podatek pokazujemy w stopce, nie tutaj
    sub_text = exact_line if exact_line else "tyle jest na rachunku"
    bench_short, bench_exact = (pln_short(bench) if bench else ("—", "—"))
    bench_delta = (pct((bench - dep) / dep * 100) if bench and dep else "—")
    n_pos = len(sim.get("open") or {})
    # Wszystko policzone przed f-stringiem: w Pythonie 3.11 zlozone wyrazenia
    # w nawiasach klamrowych potrafia sie nie sparsowac.
    h_val = esc(short)
    h_sub = esc(sub_text)
    h_gain = esc(pct(gain_pct)) if dep else "—"
    h_gain_pln = esc(pln(gain)) if dep else "—"
    h_dep = esc(pln_short(dep)[0]) if dep else "0 zł"
    h_bench_lab = esc(cfg["benchmark"]["label"])
    h_bench = esc(bench_short)
    h_bench_sub = esc(bench_exact + " · " + bench_delta) if bench_exact != bench_short else esc(bench_delta)
    n_dep = len(sim.get("deposits") or [])
    h_counts = "%d %s &middot; %d %s &middot; %d %s" % (
        n_dep, ui.pl_plural(n_dep, "wpłata", "wpłaty", "wpłat"),
        len(trades), ui.pl_plural(len(trades), "transakcja", "transakcje", "transakcji"),
        n_pos, ui.pl_plural(n_pos, "otwarta", "otwarte", "otwartych"))
    return f'''<div class="hero">
  <div>
    <div class="lab">Wartość portfela</div>
    <div class="v t-2xl serif">{h_val}</div>
    <div class="n">{h_sub}</div>
  </div>
  <div>
    <div class="lab">Zysk / strata</div>
    <div class="v t-xl {cls}">{h_gain}</div>
    <div class="n">{h_gain_pln} od wpłat</div>
  </div>
  <div>
    <div class="lab">Wpłacone</div>
    <div class="v t-xl">{h_dep}</div>
    <div class="n">{h_counts}</div>
  </div>
  <div>
    <div class="lab">{h_bench_lab} dla porównania</div>
    <div class="v t-xl">{h_bench}</div>
    <div class="n">{h_bench_sub}</div>
  </div>
</div>'''


def _day_mini(decisions: list[dict], trades: list[dict]) -> str:
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
        ("Sprawdzone spółki", str(scanned) if scanned else "—"),
        ("Przeczytane nagłówki", str(read) if read else "0"),
        ("Kupione", str(len(opened))),
        ("Sprzedane", str(len(closed))),
        ("Odpuszczone okazje", str(len(skipped))),
        ("Wynik dnia", usd(pnl) if closed else "—"),
    ]
    cells = "".join(f'<div><div class="lab">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
                    for l, v in items)
    return f'<div class="mini">{cells}</div>'


def _timeline(actions: list[dict], limit: int = 3) -> str:
    if not actions:
        return ('<div class="empty">Dziś bot nie podjął jeszcze żadnej decyzji. Pierwsze wpisy '
                'pojawiają się po otwarciu sesji w USA (15:30 czasu polskiego).</div>')
    li = []
    for a in actions[:limit]:
        if not a.get("title"):
            continue
        li.append(f'''<li class="{esc(a.get("kind") or "")}">
  <div class="t">{esc(a.get("time") or "")}</div>
  <div class="a">{esc(a.get("title"))}</div>
  {f'<div class="w">{esc(a.get("why"))}</div>' if a.get("why") else ''}
</li>''')
    more = ""
    if len(actions) > limit:
        more = ('<div class="empty" style="margin-top:10px">...i %d więcej zdarzeń dzisiaj '
                '(pelna oś czasu ponizej).</div>' % (len(actions) - limit))
    return '<ul class="tl">' + "".join(li) + "</ul>" + more


def _summary(sim: dict, cfg: dict, equity: list[dict], trades: list[dict],
             decisions: list[dict]) -> str:
    actions = insights.today_actions(sim)
    return f'''<section id="podsumowanie" class="sum">
  {_hero(sim, cfg, equity, trades)}
  <div class="chart-card">
    <div class="lab" style="margin:0 0 6px 2px">Wartość w złotych</div>
    <div class="chart-wide">{ui.line_chart(equity)}</div>
    <div class="chart-narrow">{ui.line_chart(equity, width=390, height=250, narrow=True)}</div>
  </div>
  <div class="duo">
    <div class="card">
      <h3>Dziś w skrócie</h3>
      {_timeline(actions)}
    </div>
    <div class="card">
      <h3>Bilans dnia</h3>
      {_day_mini(decisions, trades)}
    </div>
  </div>
</section>'''


# ------------------------------------------------------------------ szczegoly
def _positions(sim: dict, trades: list[dict]) -> str:
    open_pos = sim.get("open") or {}
    if open_pos:
        blocks = []
        for p in open_pos.values():
            sym = str(p.get("symbol"))
            qty = _f(p.get("qty"))
            entry, stop, target = _f(p.get("entry")), _f(p.get("stop")), _f(p.get("target"))
            px = _price(sym)
            cur = px if px else entry
            upl = (cur - entry) * qty
            cls = "up" if upl > 0 else ("down" if upl < 0 else "")
            blocks.append(f'''<div class="pos">
  <div class="top"><span class="sym">{esc(sym)}</span>
    <span class="{cls} t-md" style="font-weight:600">{usd(upl)}</span></div>
  <div class="row"><span>{num(qty)} szt. &middot; kupione po {usd(entry)}</span>
    <b>{usd(cur) if px else "brak ceny"}</b></div>
  {ui.r_gauge(stop, entry, target, cur)}
  <div class="row"><span>gdy spadnie do stopu</span><b class="down">{usd((stop - entry) * qty)}</b></div>
  <div class="row"><span>gdy dojdzie do celu</span><b class="up">{usd((target - entry) * qty)}</b></div>
</div>''')
        body = "".join(blocks)
    else:
        body = ('<div class="empty">Żadnej otwartej pozycji. Bot kończy dzień zawsze na zero — '
                'nic nie zostaje na noc.</div>')

    day = store.ny_stamp()[:10]
    today = [t for t in trades if str(t.get("close_ts_ny") or "").startswith(day)]
    if not today:
        return body
    rows = []
    for t in today:
        pnl = _f(t.get("pnl_usd"))
        cls = "up" if pnl > 0 else ("down" if pnl < 0 else "")
        r = t.get("r_multiple")
        rows.append(
            f'<tr><td><b>{esc(t.get("symbol"))}</b></td>'
            f'<td>{esc(str(t.get("open_ts_ny"))[11:16])}→{esc(str(t.get("close_ts_ny"))[11:16])}</td>'
            f'<td>{usd(t.get("entry_usd"))}→{usd(t.get("exit_usd"))}</td>'
            f'<td>{num(t.get("qty"))}</td>'
            f'<td class="r {cls}"><b>{usd(pnl)}</b></td>'
            f'<td class="r">{(("%+.2f" % _f(r)).replace(".", ",") + " R") if r not in (None, "") else "—"}</td>'
            f'<td>{esc(plain.exit_short(t.get("exit_reason")))}</td></tr>')
    total = sum(_f(t.get("pnl_usd")) for t in today)
    tcls = "up" if total > 0 else ("down" if total < 0 else "")
    return body + f'''<h4 style="margin-top:22px">Zamknięte dzisiaj &nbsp;<span class="{tcls}">{usd(total)}</span></h4>
<div class="scroll"><table>
  <tr><th>Spółka</th><th>Czas</th><th>Cena</th><th>Szt.</th><th class="r">Wynik</th><th class="r">Zysk w R</th><th>Wyjście</th></tr>
  {''.join(rows)}
</table></div>'''


def _decision_card(d: dict) -> str:
    kind = d.get("decision")
    badge = {"open": ("buy", "kupno"), "close": ("sell", "sprzedaż"),
             "deposit": ("", "wpłata")}.get(kind, ("", "odpuszczono"))
    n = d.get("numbers") or {}
    rows = []
    if kind == "open":
        rows = [("wejście", usd(n.get("entry"))), ("stop", usd(n.get("stop"))),
                ("cel", usd(n.get("target"))), ("max strata", usd(n.get("max_loss")))]
    elif kind == "close":
        # cena wejscia i wyjscia sa w tabeli wyzej - tutaj tylko wynik i R
        r = n.get("r")
        rows = [("wynik", usd(n.get("pnl"))),
                ("w jedn. R", (("%+.2f" % _f(r)).replace(".", ",")) if r not in (None, "") else "—")]
    elif kind == "deposit":
        rows = [("wpłacone", pln(n.get("pln"))), ("kurs USD/PLN", num(n.get("rate"), 4)),
                ("otrzymane", usd(n.get("usd")))]
    else:
        return ""
    nums = "".join(f'<div>{esc(l)}<b>{esc(v)}</b></div>' for l, v in rows)
    return f'''<div class="dec">
  <div class="hd"><span class="tag {badge[0]}">{esc(badge[1])}</span>
    <span class="t-xs faint">{esc(str(d.get("ts_ny"))[11:16])}</span></div>
  <div class="ttl">{esc(d.get("title") or "")}</div>
  <div class="why">{esc(d.get("why") or "")}</div>
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
        return ('<div class="empty">Jeszcze nic nie kupiono ani nie sprzedano. Pierwsza decyzja '
                'pojawi się tu z powodem w jednym zdaniu.</div>')
    return "".join(c for c in (_decision_card(d) for d in picks[:4]) if c)


def _funnel(sim: dict) -> str:
    f = insights.funnel(sim)
    steps = [
        (num(5943), "spółek w USA", "tyle widzi skaner skilla - cały rynek akcji USA"),
        (num(f["watched"]), "na liście", "tylko te dostępne w XTB jako akcje realne"),
        (num(f["signals_total"]), "sygnałów łącznie", "cena przebiła poranny szczyt i zamknęła się nad nim"),
        (num(f["checked"]), "sprawdzonych", "z nagłówkami, stopem i limitem straty"),
        (num(f["trades"]), "transakcji", "tyle przeszło wszystkie filtry"),
    ]
    out = ui.funnel(steps)
    if f["trades"]:
        out += (f'<div class="empty" style="margin-top:14px">Na każda transakcje przypadało '
                f'{f["skipped"] + f["blocked"]} odrzuconych okazji. To nie awaria — to metoda.</div>')
    return out


def _lessons(sim: dict) -> str:
    obs = insights.observations(sim)
    if not obs:
        return ('<div class="empty">Za mało transakcji, żeby wyciągać wnioski. Obserwacje pojawia '
                'się po kilku rozegranych dniach — nie są zmyślane na zapas.</div>')
    cards = []
    for o in obs[:5]:
        tone = o.get("tone")
        cls = "up" if tone == "up" else ("down" if tone == "down" else "")
        cards.append(f'''<div class="obs">
  <div class="lab">{esc(o["title"])}</div>
  <div class="v {cls}">{esc(o["value"])}</div>
  <div class="t">{esc(o["text"])}</div>
  <div class="t-xs faint" style="margin-top:4px">na podstawie {o["n"]} obserwacji</div>
</div>''')
    return "".join(cards)


def _news() -> str:
    t = news.today()
    items = list(t.get("items") or [])
    if not items:
        return ('<div class="empty">Dziś bot nie czytał jeszcze nagłówków. Czyta je dopiero, gdy ma '
                'kandydata do kupna — nie czyta dla samego czytania.</div>')
    items = sorted(items, key=lambda i: str(i.get("time") or ""), reverse=True)[:6]
    rows = []
    for it in items:
        tags = "".join(f'<span class="chip{" risk" if it.get("risk") else ""}">{esc(tg)}</span>'
                       for tg in str(it.get("tags") or "").split())
        impact = it.get("impact") or ""
        imp = (f' &middot; <b>{esc(impact)}</b>' if impact and impact != "nie zmienil decyzji"
               else (' &middot; bez wpływu na decyzje' if impact else ""))
        rows.append(f'''<div class="news-item">
  <div class="t-sm faint">{esc(_et_hhmm(it.get("time")))}</div>
  <div>
    <div class="ti"><b>{esc(it.get("ticker") or "")}</b> {esc(it.get("title") or "")}</div>
    <div class="mt">{tags}{esc(it.get("source") or "")}{imp}</div>
  </div>
</div>''')
    head = (f'<div class="t-sm mut" style="margin-bottom:6px">Przeczytane dzisiaj: '
            f'<b>{len(t.get("items") or [])}</b> nagłówków'
            + (f', {t.get("blocked")} wstrzymalo zakup' if t.get("blocked") else "") + ".</div>")
    return head + "".join(rows)


def _how() -> str:
    steps = [
        ("01", "Skan", "Przeglądam listę spółek i szukam ceny, która przebiła maksimum pierwszych 15 minut sesji."),
        ("02", "Nagłówki", "Czytam wiadomości o kandydacie. Realny wstrząs = odpuszczam, zanim zaryzykuję."),
        ("03", "Plan", "Przed wejściem ustalam stop (gdzie się myliłem) i cel (kiedy biorę zysk)."),
        ("04", "Wielkość", "Liczę, ile akcji kupić, żeby maksymalna strata to 1% kapitału. Nie na oko."),
        ("05", "Koniec dnia", "Zamykam wszystko przed 16:00 w Nowym Jorku. Zero trzymania na noc."),
    ]
    cells = "".join(f'''<div class="step"><div class="n">{n}</div>
      <div class="h">{esc(h)}</div><div class="d">{esc(d)}</div></div>''' for n, h, d in steps)
    return f'<div class="steps">{cells}</div>'


def _glossary() -> str:
    return ('<div class="gloss">'
            + "".join(f'<div><b>{esc(k)}</b><br><span>{esc(v)}</span></div>' for k, v in plain.GLOSSARY)
            + "</div>")


def _footer(sim: dict, cfg: dict) -> str:
    c = cfg["costs"]
    s = cfg["simulation"]
    return f'''<footer>
  <b>Jak to policzone.</b> Kapitał startowy {pln(s["start_capital_pln"])}, potem
  {pln(s["monthly_deposit_pln"])} w pierwszym dniu handlowym każdego miesiąca przez {s["days"]} dni.
  Koszty: przewalutowanie {num(c["fx_cost_pct"], 1)}%, poślizg {num(c["slippage_bps"], 0)} pb
  na transakcję, podatek Belki {num(c["tax_on_gains_pct"], 0)}% od zysku.
  {("Odłożone na podatek: <b>" + pln(sim.get("tax_reserve_pln")) + "</b>. ") if _f(sim.get("tax_reserve_pln")) > 0.5 else ""}
  Ceny: darmowe, nieoficjalne Yahoo, opóźnione o kilkadziesiąt sekund.
  Zlecenia są <b>symulowane</b> — nic nie idzie do brokera.
  <br><br>
  <b>To nie jest porada inwestycyjna.</b> Symulacja pokazuje metodę, nie obiecuję wyniku.
  Większość osób handlujących w ciągu dnia traci pieniądze.
  Zalozenia: <code>docs/XTB-ZALOZENIA.md</code> &middot; decyzje:
  <code>sim/state/decisions.jsonl</code> &middot; transakcje: <code>sim/state/trades.csv</code>
</footer>'''


def _empty_intro(cfg: dict) -> str:
    s = cfg["simulation"]
    return f'''<div class="card" style="margin-top:18px;background:#FCFBF7">
  <div class="lab">Zanim ruszy</div>
  <div class="serif t-xl" style="margin:6px 0 6px">Symulacja startuje {esc(s["start_date"])}</div>
  <div class="t-sm mut">
    Pierwszego dnia handlowego bot wpłaci {pln(s["start_capital_pln"])}, przewalutuje je na
    dolary i zacznie skanować rynek. Pierwsze decyzje pojawiają się po 15:30 czasu polskiego —
    do tego czasu panel jest celowo pusty, nic tu nie jest zmyślane.
    Jak wygląda po rozegranym dniu: <a class="lnk" href="przyklad-panelu.png">przykład-panelu.png</a>.
  </div>
</div>'''


# ------------------------------------------------------------------ build
def build(sim: dict, cfg: dict) -> str:
    equity = store.read_csv(store.EQUITY)
    trades = store.read_csv(store.TRADES)
    decisions = _load_decisions()
    dep = _f(sim.get("deposits_pln_total"))

    body = [_toc(), _masthead(sim, cfg, equity), _summary(sim, cfg, equity, trades, decisions)]
    if not dep and not trades:
        body.append(_empty_intro(cfg))

    detail = [
        ("s1", "Pozycje", "Co bot trzyma teraz i co zamknął dzisiaj", _positions(sim, trades)),
        ("s2", "Dlaczego podjął te decyzje", "Każda decyzja z powodem i liczbami", _decisions(decisions)),
        ("s3", "Lejek decyzji", "Z tysięcy spółek zostaje kilka transakcji", _funnel(sim)),
        ("s4", "Czego się nauczył", "Wnioski z własnych transakcji", _lessons(sim)),
        ("s5", "Co czytał", "Nagłówki i ich wpływ na decyzje", _news()),
        ("s6", "Jak działa", "Ta sama pętla każdego dnia handlowego", _how()),
        ("s7", "Słowniczek", "Każde pojęcie jednym zdaniem", _glossary()),
    ]
    body.append('<section><div class="lab" style="margin-bottom:14px">Szczegóły</div>'
                '<div class="grid2">')
    for i, (sid, title, sub, content) in enumerate(detail):
        span = ' style="grid-column:1/-1"' if sid in ("s7", "s6") else ""
        body.append(f'''<div class="card" id="{sid}"{span}>
  <h3>{esc(title)}</h3>
  <div class="t-sm mut" style="margin:-6px 0 14px">{esc(sub)}</div>
  {content}
</div>''')
    body.append("</div></section>")
    body.append(_footer(sim, cfg))

    html = f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Dziennik symulacji inwestowania: co bot zrobil i dlaczego.">
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
    from sim import book, engine

    _cfg = book.load_cfg()
    _sim = engine.ensure_init(book.load_sim(), _cfg)
    print(build(_sim, _cfg))

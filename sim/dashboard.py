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
    from sim import insights, market, news, plain, session as ses, spolki, store, ui
    from sim.ui import esc, num, pct, pln, pln_short, usd
else:
    from . import insights, market, news, plain, session as ses, spolki, store, ui
    from .ui import esc, num, pct, pln, pln_short, usd

CSS = """/* Paleta i styl wzorowane na darmowym pliku Figma
   "Free Crypto Dashboard - RecehTok Dark": ciemny granatowo-fioletowy motyw,
   karty z promieniem 12 px i miekkim cieniem, akcenty ograniczone do trzech
   kolorow. Wartosci kolorow pobrane z pikseli wzorca. */
:root{
  --bg:#141231; --bg2:#18163C; --card:#201D47; --card2:#26214D;
  --line:#33305A; --grid:#3A365B; --soft:#2A2750;
  --ink:#FFFFFF; --ink2:#E7E5F2; --muted:#B4B1C7; --faint:#8E8BA3;
  --up:#38D9A9; --down:#F06595; --acc:#A389F4;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
a{color:var(--up);text-decoration:none}
a:hover{text-decoration:underline}
.serif{font-family:Georgia,"Iowan Old Style","Times New Roman",serif}
.up{color:var(--up)}.down{color:var(--down)}.mut{color:var(--muted)}.faint{color:var(--faint)}

/* ---- skala typografii: 12 / 14 / 16 / 20 / 28 / 44 ---- */
.t-xs{font-size:12px}.t-sm{font-size:14px}.t-md{font-size:16px}
.t-lg{font-size:20px}.t-xl{font-size:28px}.t-2xl{font-size:44px}
.lab{font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.kpi .v{font-weight:700;letter-spacing:-.02em}
.kpi .n{font-weight:400;color:var(--muted)}

/* ---- szkielet: panel boczny + tresc ---- */
.app{display:grid;grid-template-columns:210px minmax(0,1fr);min-height:100vh}
.side{background:var(--bg2);border-right:1px solid var(--line);padding:20px 14px;
  position:sticky;top:0;height:100vh;overflow-y:auto;display:flex;flex-direction:column;gap:4px}
.side .brand{font-size:16px;font-weight:700;color:var(--ink);padding:6px 12px 14px;letter-spacing:-.01em}
.side .brand span{display:block;font-size:12px;font-weight:400;color:var(--faint);
  letter-spacing:.06em;text-transform:uppercase;margin-top:3px}
.side nav{display:flex;flex-direction:column;gap:2px}
.side nav a{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 12px;
  border-radius:10px;color:var(--faint);font-size:14px}
.side nav a svg{flex:0 0 auto;color:var(--acc);opacity:.75}
.side nav a:hover svg,.side nav a.on svg{opacity:1;color:var(--up)}
.side .brand:before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;
  background:var(--up);margin-right:8px;box-shadow:0 0 10px rgba(56,217,169,.8)}
.side nav a:hover{background:var(--card);color:var(--ink2);text-decoration:none}
.side nav a.on{background:var(--card2);color:var(--ink);font-weight:600}
.side .foot{margin-top:auto;padding:12px;font-size:12px;color:var(--faint);line-height:1.5}
.main{padding:30px 38px 72px;max-width:1200px;min-width:0}

/* ---- gorny pasek ---- */
.topbar{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:flex-start;
  justify-content:space-between;margin-bottom:20px}
.topbar h1{margin:4px 0 0;font-size:28px;font-weight:700;line-height:1.15;letter-spacing:-.015em}
.topbar .right{font-size:14px;color:var(--muted);line-height:1.6;text-align:right}
.stat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;
  letter-spacing:.07em;text-transform:uppercase;color:var(--faint)}
.stat i{width:8px;height:8px;border-radius:50%;background:var(--faint);display:block}
.stat.shut i{background:var(--down);box-shadow:0 0 0 3px rgba(240,101,149,.18)}
.stat.shut{color:var(--down)}
.stat.open i{background:var(--up);box-shadow:0 0 0 3px rgba(56,217,169,.18)}
.prog{height:4px;background:var(--soft);border-radius:3px;margin-bottom:18px;overflow:hidden}
.prog i{display:block;height:100%;background:var(--acc);border-radius:3px}

/* ---- karty metryk (osobne karty, jak we wzorcu) ---- */
.kpis{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:16px}
.kpi{background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,0) 62%),
    var(--card);
  border:1px solid rgba(163,137,244,.14);border-radius:12px;padding:16px;
  min-width:0;
  /* na ciemnym tle czarny cien jest niewidoczny - glebie daje jasny gorny przeblysk
     i delikatny ciemny cien pod karta */
  box-shadow:0 12px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.07)}
.kpi.lead .v{text-shadow:0 0 22px rgba(56,217,169,.42)}
.kpi.lead{background:linear-gradient(168deg,rgba(56,217,169,.62),rgba(56,217,169,.10) 40%,
  rgba(163,137,244,.10) 58%,rgba(30,27,66,.98) 84%);border-color:rgba(56,217,169,.42);
  box-shadow:0 12px 28px rgba(0,0,0,.45), 0 0 0 1px rgba(56,217,169,.22),
    0 0 34px rgba(56,217,169,.12), inset 0 1px 0 rgba(255,255,255,.10)}
.kpi .n + svg, .kpi svg[role="img"]{margin-top:6px}
.kpi .n{color:var(--muted)}
.kpi .v{margin-top:6px;line-height:1.08;font-weight:700}
.kpi .n{font-size:14px;color:var(--muted);margin-top:7px}

/* ---- sekcje ---- */
section{margin-top:30px;scroll-margin-top:18px}
[id]{scroll-margin-top:18px}
.sec-h{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;
  box-shadow:0 12px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06);min-width:0}
.grid2 > *{min-width:0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card h3{margin:0 0 4px;font-size:20px;font-weight:600;letter-spacing:-.01em}
.card .sub{font-size:14px;color:var(--muted);margin:0 0 14px}
.chart-card{background:var(--card);border:1px solid var(--line);border-radius:12px;
  box-shadow:0 12px 28px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06);
  padding:14px 14px 6px;margin-top:14px;box-shadow:0 8px 20px rgba(0,0,0,.20)}
.chart-card svg{display:block}
.chart-narrow{display:none}
.duo{display:grid;grid-template-columns:1.45fr 1fr;gap:16px;margin-top:16px}
.duo .card{padding:18px}

/* ---- os czasu ---- */
.tl{list-style:none;margin:0;padding:0}
.tl li{position:relative;padding:0 0 13px 22px;border-left:1px solid var(--line)}
.tl li:last-child{border-left-color:transparent;padding-bottom:0}
.tl li:before{content:"";position:absolute;left:-5.5px;top:5px;width:11px;height:11px;
  border-radius:50%;background:var(--bg);border:2px solid var(--faint)}
.tl li.open:before{border-color:var(--up);background:var(--up)}
.tl li.close:before{border-color:var(--acc);background:var(--acc)}
.tl li.deposit:before{border-color:var(--ink);background:var(--ink)}
.tl .t{font-size:12px;color:var(--faint)}
.tl .a{font-size:16px;font-weight:600}
.tl .w{font-size:14px;color:var(--muted);margin-top:2px}

/* ---- mini statystyki ---- */
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:12px 16px}
.mini .v{font-size:20px;font-weight:600;margin-top:3px}

/* ---- pozycje ---- */
.pos + .pos{margin-top:16px;padding-top:16px;border-top:1px solid var(--soft)}
.pos .top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.pos .sym{font-size:20px;font-weight:600}
.pos .row{display:flex;justify-content:space-between;gap:10px;font-size:14px;color:var(--muted)}
.pos .row b{color:var(--ink2);font-weight:600}
.rg{position:relative;height:28px;margin:6px 0 2px}
.rg-track{position:absolute;left:2%;right:2%;top:9px;height:5px;background:var(--soft);border-radius:3px}
.rg-seg{position:absolute;top:9px;height:5px;opacity:.55}
.rg-dot{position:absolute;top:6px;width:10px;height:10px;border-radius:50%;transform:translateX(-50%)}
.rg-entry{position:absolute;top:5px;width:13px;height:13px;border-radius:50%;background:var(--card);
  border:2px solid var(--faint);transform:translateX(-50%)}
.rg-price{position:absolute;top:3px;width:17px;height:17px;border-radius:50%;border:2px solid var(--bg);
  transform:translateX(-50%)}
.rg-lab{position:absolute;top:18px;font-size:12px;color:var(--faint);transform:translateX(-50%);white-space:nowrap}

/* ---- tabele ---- */
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}
table{width:100%;border-collapse:collapse;font-size:14px;min-width:520px}
th{font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--faint);
  text-align:left;padding:0 12px 10px 0;border-bottom:1px solid var(--line)}
td{padding:11px 12px 11px 0;border-bottom:1px solid var(--soft);white-space:nowrap;color:var(--ink2)}
tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;padding-right:0;padding-left:18px}

/* ---- lejek ---- */
.fn{display:flex;flex-direction:column;gap:10px}
.fn-bar{background:rgba(56,217,169,.14);border:1px solid rgba(56,217,169,.32);
  border-radius:9px;padding:10px 14px;display:flex;align-items:baseline;gap:10px;
  min-width:150px;font-weight:600;color:#EAFBF5}
.fn-val{font-size:20px;font-weight:700;color:#FFFFFF}
.fn-lab{font-size:14px;color:#A7E8D2}
.fn-note{font-size:14px;color:var(--muted);margin-top:5px}

/* ---- karty decyzji ---- */
.dec{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:16px}
.dec + .dec{margin-top:12px}
.dec .hd{display:flex;justify-content:space-between;align-items:center;gap:10px}
.dec .ttl{font-size:16px;font-weight:600;margin:10px 0 4px}
.dec .why{font-size:14px;color:var(--muted)}
.nums{display:flex;flex-wrap:wrap;gap:16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--soft)}
.nums div{font-size:12px;color:var(--faint);letter-spacing:.05em;text-transform:uppercase}
.nums b{display:block;font-size:16px;color:var(--ink);letter-spacing:0;text-transform:none;margin-top:3px}
.tag{font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;padding:4px 10px;
  border-radius:7px;border:1px solid var(--line);color:var(--faint)}
.tag.buy{border-color:rgba(56,217,169,.35);background:rgba(56,217,169,.12);color:var(--up)}
.tag.sell{border-color:rgba(163,137,244,.35);background:rgba(163,137,244,.14);color:var(--acc)}

/* ---- obserwacje ---- */
.obs{border-left:3px solid var(--soft);padding-left:14px;margin-bottom:18px}
.obs .v{font-size:28px;font-weight:700;line-height:1.15}
.obs .t{font-size:14px;color:var(--muted);margin-top:4px}

/* ---- naglowki z prasy ---- */
.news-item{display:grid;grid-template-columns:46px 1fr;gap:12px;padding:11px 0;
  border-bottom:1px solid var(--soft)}
.news-item:last-child{border-bottom:0}
.news-item .ti{font-size:14px;line-height:1.45;color:var(--ink2);max-width:62ch}
.news-item .mt{font-size:12px;color:var(--faint);margin-top:3px}
.chip{display:inline-block;font-size:12px;padding:2px 9px;border-radius:999px;
  background:var(--soft);color:var(--muted);margin-right:6px}
.chip.risk{background:rgba(240,101,149,.16);color:var(--down)}

/* ---- kroki ---- */
.steps{display:grid;grid-template-columns:repeat(2,1fr);gap:18px 26px}
.step .n{font-size:12px;color:var(--acc);letter-spacing:.09em;font-weight:700}
.step .h{font-size:16px;font-weight:600;margin:4px 0 3px}
.step .d{font-size:14px;color:var(--muted)}

/* ---- slowniczek ---- */
.gloss{display:grid;grid-template-columns:1fr 1fr;gap:12px 28px}
.gloss b{font-size:14px;color:var(--ink)}
.gloss span{font-size:14px;color:var(--muted)}

/* ---- wspolne ---- */
.empty{color:var(--muted);font-size:14px}
.costs{display:grid;grid-template-columns:repeat(6,1fr);gap:16px;margin-bottom:16px}
.kats{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.kat-h{font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  color:var(--faint);margin-bottom:8px}
.kat-h span{color:var(--acc);font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-flex;gap:6px;align-items:baseline;font-size:12px;padding:4px 9px;
  border-radius:8px;background:var(--card2);border:1px solid var(--line);color:var(--muted);
  white-space:nowrap}
.chip b{color:var(--ink2);font-weight:700}
.chip.kupiona{background:rgba(56,217,169,.16);border-color:rgba(56,217,169,.45);color:#D8FBF1}
.chip.sprzedana{background:rgba(56,217,169,.10);border-color:rgba(56,217,169,.28)}
.chip.odrzucona{background:rgba(240,101,149,.14);border-color:rgba(240,101,149,.40);color:#FBD9E5}
.chip.sprawdzona{background:rgba(163,137,244,.16);border-color:rgba(163,137,244,.45);color:#E4DBFB}
.costs div{min-width:0}
.costs span{display:block;font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--faint)}
.costs b{display:block;font-size:16px;font-weight:600;margin-top:3px;color:var(--ink2)}
.fine{font-size:14px;color:var(--muted);margin:6px 0 0;max-width:64ch}
footer{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);
  font-size:14px;color:var(--muted);line-height:1.65}
code{background:var(--soft);padding:1px 6px;border-radius:5px;font-size:14px;color:var(--ink2)}
a.lnk{display:inline-block;padding:6px 0;min-height:26px;font-weight:600}
.ax{font-size:12px;fill:var(--faint)}
.sv{font-size:12px;font-weight:600}
.lastv{font-size:14px;fill:#FFFFFF;font-weight:700}
/* poswiata linii portfela - we wzorcu linie swieca, nie sa tylko kreskami */
.glow{filter:drop-shadow(0 0 5px rgba(56,217,169,.55))}
.hero-note{background:var(--card2);border:1px solid var(--line);border-radius:12px;
  padding:16px;margin-top:16px}

@media (max-width:900px){
  .app{grid-template-columns:1fr}
  .side{position:sticky;top:0;z-index:30;height:auto;flex-direction:row;align-items:center;
    gap:6px;padding:8px 12px;overflow-x:auto;border-right:0;border-bottom:1px solid var(--line)}
  .side .brand,.side .foot{display:none}
  .side nav{flex-direction:row;gap:4px}
  .side nav a{white-space:nowrap;padding:0 12px}
  .main{padding:20px 18px 56px}
  .topbar .right{text-align:left}
  .kpis{grid-template-columns:1fr 1fr;gap:12px}
  .kpi.lead{grid-column:1/-1}
  .duo,.grid2,.steps,.gloss{grid-template-columns:1fr}
  .mini{grid-template-columns:1fr 1fr}
  .card{padding:16px}
  .chart-wide{display:none}
  .chart-narrow{display:block}
  .costs{grid-template-columns:1fr 1fr}
  .kats{grid-template-columns:1fr}
}
"""

# (id, etykieta, ikona) - ikony rysowane linia, w stylu wzorca
_ICONS = {
    "pulse": '<path d="M3 12h5l2.5 6L15 5l2 7h4"/>',
    "layers": '<path d="M4 18V10M10 18V5M16 18v-6M22 18H2"/>',
    "bulb": '<circle cx="12" cy="12" r="9"/><path d="M9.4 9.2a2.6 2.6 0 1 1 3.4 2.5V13"/><circle cx="12" cy="16.4" r=".7"/>',
    "funnel": '<path d="M3 4h18l-7 8v6l-4-2v-4z"/>',
    "book": '<path d="M4 5h6.5a2 2 0 0 1 2 2v12a2 2 0 0 0-2-2H4z"/><path d="M20 5h-5.5a2 2 0 0 0-2 2v12a2 2 0 0 1 2-2H20z"/>',
    "lines": '<path d="M4 6h16M4 11h16M4 16h10"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l6 3.5-6 3.5z"/>',
    "abc": '<path d="M5 4h8l3 3v13H5z"/><path d="M8 9h5M8 13h5"/>',
    "grid": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
}

TOC = [
    ("podsumowanie", "Podsumowanie", "pulse"),
    ("s1", "Co mam teraz", "layers"),
    ("s2", "Spółki, które obserwuję", "grid"),
    ("s3", "Dlaczego kupił", "bulb"),
    ("s4", "Od czego do czego", "funnel"),
    ("s5", "Czego się nauczył", "book"),
    ("s6", "Co czytał", "lines"),
    ("s7", "Jak działa", "play"),
    ("s8", "Słowniczek", "abc"),
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
def _sidebar() -> str:
    """Panel boczny jak we wzorcu: marka + lista sekcji, na telefonie pasek poziomy."""
    def _icon(name):
        return ('<svg viewBox="0 0 24 24" width="15" height="15" fill="none" '
                'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
                'stroke-linejoin="round" aria-hidden="true">%s</svg>' % _ICONS[name])

    links = "".join('<a href="#%s">%s<span>%s</span></a>' % (i, _icon(ic), esc(t))
                    for i, t, ic in TOC)
    return (f'<aside class="side">'
            f'<div class="brand">XTB Day Trader<span>dziennik symulacji</span></div>'
            f'<nav>{links}</nav>'
            f'<div class="foot">Symulacja na danych historycznych.<br>'
            f'Nic nie idzie do brokera.</div>'
            f'</aside>')


def _masthead(sim: dict, cfg: dict, equity: list[dict]) -> str:
    now = ses.now_ny()
    is_open = ses.is_open(now)
    day = int(sim.get("day_count") or 0)
    total = int(cfg["simulation"]["days"])
    last = str(_last_row(equity).get("date") or "")
    pretty = (last[8:10] + "." + last[5:7] + "." + last[0:4]) if len(last) >= 10 else "—"
    pill = ('<span class="stat open"><i></i>rynek otwarty</span>' if is_open
            else '<span class="stat shut"><i></i>rynek zamknięty</span>')
    # postep symulacji: jedyna metryka z progiem, wiec dostaje pasek
    prog = max(min(day / max(total, 1) * 100, 100), 0.5)
    return f'''<div class="topbar">
  <div>
    <div class="lab">Podsumowanie</div>
    <h1>Wyniki symulacji</h1>
  </div>
  <div class="right">
    {pill} &nbsp; <b style="color:var(--ink2)">dzień {day} z {total}</b><br>
    dane z {esc(pretty)} &middot; {esc(now.strftime('%H:%M'))} czasu Nowego Jorku
  </div>
</div>
<div class="prog" role="img" aria-label="Postęp symulacji: dzień {day} z {total}">
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
    sub_text = exact_line if exact_line else ""
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
    # polski podatek: ile zostanie po jego zaplaceniu (jest naliczony, ale jeszcze nie zaplacony)
    tax_owed = (_f(last.get("tax_owed_pln")) if last.get("tax_owed_pln") not in (None, "")
                else _f(sim.get("tax_reserve_pln")))
    h_tax_line = ("po podatku " + pln(gain - tax_owed)) if (dep and tax_owed > 0.5) else ""
    # mini-wykresy na kartach (we wzorcu kazda karta ma swoj)
    sp_eq = ui.sparkline([_f(r.get("equity_pln")) for r in equity], ui.UP, gid="sp-eq")
    sp_dep = ui.sparkline([_f(r.get("deposits_pln_total")) for r in equity], ui.FAINT, gid="sp-dep")
    sp_ben = ui.sparkline([_f(r.get("bench_pln")) for r in equity], ui.ACCENT, gid="sp-ben")
    h_bench = esc(bench_short)
    h_bench_sub = esc(bench_exact + " · " + bench_delta) if bench_exact != bench_short else esc(bench_delta)
    n_dep = len(sim.get("deposits") or [])
    h_counts = "%d %s &middot; %d %s &middot; %d %s" % (
        n_dep, ui.pl_plural(n_dep, "wpłata", "wpłaty", "wpłat"),
        len(trades), ui.pl_plural(len(trades), "transakcja", "transakcje", "transakcji"),
        n_pos, ui.pl_plural(n_pos, "otwarta", "otwarte", "otwartych"))
    return f'''<div class="kpis">
  <div class="kpi lead">
    <div class="lab">Wartość portfela</div>
    <div class="v t-2xl">{h_val}</div>
    <div class="n">{h_sub}</div>
    {sp_eq}
  </div>
  <div class="kpi">
    <div class="lab">Zysk / strata</div>
    <div class="v t-xl {cls}">{h_gain}</div>
    <div class="n">{h_gain_pln} od wpłat</div>
    {f'<div class="n">{esc(h_tax_line)}</div>' if h_tax_line else ''}
  </div>
  <div class="kpi">
    <div class="lab">Wpłacone</div>
    <div class="n">{h_dep}</div>
    {sp_dep}
    <div class="n">{h_counts}</div>
  </div>
  <div class="kpi">
    <div class="lab">{h_bench_lab} — wzorzec</div>
    <div class="v t-xl">{h_bench}</div>
    <div class="n">{h_bench_sub}</div>
    {sp_ben}
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
        ("Sprawdzone", str(scanned) if scanned else "—"),
        ("Nagłówki", str(read) if read else "0"),
        ("Kupione", str(len(opened))),
        ("Sprzedane", str(len(closed))),
        ("Odpuszczone", str(len(skipped))),
        ("Wynik", usd(pnl) if closed else "—"),
    ]
    cells = "".join(f'<div><div class="lab">{esc(l)}</div><div class="v">{esc(v)}</div></div>'
                    for l, v in items)
    return f'<div class="mini">{cells}</div>'


def _timeline(actions: list[dict], limit: int = 3) -> str:
    if not actions:
        return ('<div class="empty">Dziś nic jeszcze. Pierwsze decyzje po 15:30 czasu polskiego.</div>')
    li = []
    for a in actions[:limit]:
        if not a.get("title"):
            continue
        # powody kupna i sprzedazy sa w kartach nizej - tutaj nie powtarzamy
        skip_why = (a.get("kind") or "") in ("open", "close", "deposit")
        li.append(f'''<li class="{esc(a.get("kind") or "")}">
  <div class="t">{esc(a.get("time") or "")}</div>
  <div class="a">{esc(a.get("title"))}</div>
  {f'<div class="w">{esc(a.get("why"))}</div>' if (a.get("why") and not skip_why) else ''}
</li>''')
    more = ""
    if len(actions) > limit:
        more = ('<div class="empty" style="margin-top:8px">…i %d więcej poniżej.</div>'
                % (len(actions) - limit))
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
      <div class="lab" style="margin-bottom:10px">Dziś w skrócie</div>
      {_timeline(actions)}
    </div>
    <div class="card">
      <div class="lab" style="margin-bottom:10px">Bilans dnia</div>
      {_day_mini(decisions, trades)}
    </div>
  </div>
</section>'''


# ------------------------------------------------------------------ szczegoly
def _positions(sim: dict, trades: list[dict], equity: list[dict] | None = None) -> str:
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
        # Pytanie "skoro nic nie kupiono, skad strata 50 zl?" jest naturalne.
        # Pokazujemy, GDZIE sa pieniadze i skad bierze sie koszt wejscia.
        last = _last_row(equity or [])
        rate = _f(sim.get("fx", {}).get("rate")) or 1.0
        cash_usd = _f(last.get("cash_usd"))
        fee_usd = sum(_f(x.get("fx_fee_usd")) for x in (sim.get("deposits") or []))
        fee_pln = fee_usd * rate
        rowsx = [
            ("Gotówka w dolarach", ("%s USD" % num(cash_usd, 2)) if cash_usd else "—"),
            ("To samo w złotówkach", pln(cash_usd * rate) if cash_usd else "—"),
            ("Akcje", "0"),
        ]
        if fee_pln > 0.5:
            rowsx.append(("Koszt wejścia (wymiana zł na $)", "&minus;" + pln(abs(fee_pln))))
        cells = "".join(f'<div><span>{esc(k)}</span><b>{v}</b></div>' for k, v in rowsx)
        body = ('<div class="costs" style="grid-template-columns:repeat(4,1fr);margin-bottom:12px">'
                + cells + '</div>'
                + '<div class="empty">Nie mam żadnych akcji. Cała kwota czeka w dolarach na sygnał.'
                  ' Dzień zawsze kończę bez akcji.</div>')

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
            f'<td class="r">{("%+.2f" % _f(r)).replace(".", ",") if r not in (None, "") else "—"}</td>' 
            f'<td>{esc(plain.exit_short(t.get("exit_reason")))}</td></tr>')
    total = sum(_f(t.get("pnl_usd")) for t in today)
    tcls = "up" if total > 0 else ("down" if total < 0 else "")
    return body + f'''<h4 style="margin-top:22px">Zamknięte dzisiaj &nbsp;<span class="{tcls}">{usd(total)}</span></h4>
<div class="scroll"><table>
  <tr><th>Spółka</th><th>Czas</th><th>Cena</th><th>Szt.</th><th class="r">Wynik</th><th class="r">× ryzyko</th><th>Wyjście</th></tr>
  {''.join(rows)}
</table></div>'''


def _decision_card(d: dict) -> str:
    kind = d.get("decision")
    badge = {"open": ("buy", "kupno"), "close": ("sell", "sprzedaż"),
             "deposit": ("", "wpłata")}.get(kind, ("", "odpuszczono"))
    n = d.get("numbers") or {}
    rows = []
    if kind == "open":
        rows = [("kupno", usd(n.get("entry"))), ("stop", usd(n.get("stop"))),
                ("cel", usd(n.get("target"))), ("maks. strata", usd(n.get("max_loss")))]
        # wyniki badania spółki (raporty ze SEC) - po to, zeby widac bylo DLACZEGO
        for k, v in (n.get("badanie") or {}).items():
            rows.append((k, v))
    elif kind == "close":
        # cena wejscia i wyjscia sa w tabeli wyzej - tutaj tylko wynik i R
        r = n.get("r")
        rows = [("wynik", usd(n.get("pnl"))),
                ("× ryzyko", (("%+.2f" % _f(r)).replace(".", ",")) if r not in (None, "") else "—")]
    elif kind == "deposit":
        rows = [("wpłacone", pln(n.get("pln"))), ("kurs dolara", num(n.get("rate"), 4)),
                ("kupiono akcji za", usd(n.get("usd")))]
    else:
        # odrzucenie (skip/block): to tez decyzja i tez ma powod.
        # Bylo tu "return ''" - karty odrzucen znikaly bez sladu.
        badge = ("", "odpuszczono")
        rows = [(k, v) for k, v in n.items() if k not in ("ile", "kod", "top")]
    nums = "".join(f'<div>{esc(l)}<b>{esc(v)}</b></div>' for l, v in rows[:6])
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
        return '<div class="empty">Jeszcze nic tu nie ma.</div>'
    # obok kupna pokazujemy tez dzisiejsze odrzucenie: "dlaczego NIE kupilem"
    # bywa wazniejsze niz "dlaczego kupilem".
    odrzucone = [d for d in td if d.get("decision") in ("skip", "block") and d.get("symbol")]
    if odrzucone:
        picks = picks[:3] + odrzucone[:1]   # max 4 karty razem
    return "".join(c for c in (_decision_card(d) for d in picks[:4]) if c)


def _spolki(decisions: list[dict], sim: dict) -> str:
    """Co bot obserwuje: nazwy spółek, kategorie i dzisiejszy status.

    Status bierze się z dziennika decyzji, więc nie jest ozdobnikiem:
    "kupiona" = faktycznie kupiona dzisiaj, "odrzucona" = sprawdzona i odpuszczona.
    """
    kat = spolki

    watch = kat.watchlist()
    if not watch:
        return '<div class="empty">Brak listy spółek (universe.txt).</div>'
    day = store.ny_stamp()[:10]
    today = [x for x in decisions if str(x.get("ts_ny", "")).startswith(day)]
    kupione, sprzedane, odrzucone, sygnal = set(), set(), {}, set()
    for x in today:
        sym = str(x.get("symbol") or "").upper()
        dec = x.get("decision")
        if dec == "open" and sym:
            kupione.add(sym)
        elif dec == "close" and sym:
            sprzedane.add(sym)
        elif dec in ("skip", "block") and sym:
            odrzucone.setdefault(sym, x)
        elif dec == "scan":
            for s in (x.get("numbers") or {}).get("top") or []:
                sygnal.add(str(s).upper())

    def status(sym: str) -> tuple[str, str]:
        if sym in kupione:
            return "kupiona", "kupiona dziś"
        if sym in sprzedane:
            return "sprzedana", "sprzedana dziś"
        if sym in odrzucone:
            return "odrzucona", plain.title_for(odrzucone[sym].get("code") or "inne").lower()
        if sym in sygnal:
            return "sprawdzona", "miała sygnał — sprawdzałem"
        return "", "czekam na sygnał"

    ich = len([s for s in watch if s in kupione])
    their = len([s for s in watch if s in sygnal])
    heads = (f'{len(watch)} spółek w {len(kat.grupy(watch))} kategoriach. '
             f'Dziś kupione: {ich}, ze sygnałem: {their}, sprawdzone i odrzucone: '
             f'{len([s for s in watch if s in odrzucone])}.')
    blocks = []
    for name, syms in kat.grupy(watch):
        chips = []
        for s in syms:
            cls, why = status(s)
            cls_attr = f' class="chip {cls}"' if cls else ' class="chip"'
            chips.append(f'<span{cls_attr} title="{esc(kat.nazwa(s))} — {esc(why)}">'
                         f'<b>{esc(s)}</b>{esc(kat.nazwa(s))}</span>')
        blocks.append(f'<div><div class="kat-h">{esc(name)} <span>{len(syms)}</span></div>'
                      f'<div class="chips">{"".join(chips)}</div></div>')
    legend = ('<div class="empty" style="margin-top:12px">'
              'Zielona = kupiona dzisiaj · fioletowa = miała sygnał i sprawdzałem · '
              'różowa = sprawdzona i odrzucona · szara = czekam na sygnał.</div>')
    return (f'<div class="t-sm mut" style="margin-bottom:14px">{heads}</div>'
            f'<div class="kats">{"".join(blocks)}</div>{legend}')


def _funnel(sim: dict) -> str:
    f = insights.funnel(sim)
    steps = [
        (num(5943), "spółek w USA", ""),
        (num(f["watched"]), "na mojej liście", ""),
        (num(f["signals_total"]), "wyszło nad szczyt", ""),
        (num(f["checked"]), "z planem wyjścia", ""),
        (num(f["trades"]), "kupionych", ""),
    ]
    out = ui.funnel(steps)
    if f["trades"]:
        out += (f'<div class="empty" style="margin-top:12px">{f["skipped"] + f["blocked"]} '
                f'odrzuconych na 1 zakup.</div>')
    return out


def _lessons(sim: dict) -> str:
    obs = insights.observations(sim)
    if not obs:
        return '<div class="empty">Za mało danych. Wnioski pojawią się po kilku dniach.</div>' 
    cards = []
    for o in obs[:5]:
        tone = o.get("tone")
        cls = "up" if tone == "up" else ("down" if tone == "down" else "")
        cards.append(f'''<div class="obs">
  <div class="lab">{esc(o["title"])}</div>
  <div class="v {cls}">{esc(o["value"])}</div>
  <div class="t">{esc(o["text"])}</div>
  <div class="t-xs faint" style="margin-top:4px">z {o["n"]} {ui.pl_plural(o["n"], "zakupu", "zakupów", "zakupów")}</div>
</div>''')
    return "".join(cards)


def _news() -> str:
    t = news.today()
    items = list(t.get("items") or [])
    if not items:
        return '<div class="empty">Dziś nic. Czytam tylko wtedy, gdy mam kandydata do kupna.</div>' 
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
    n_items = len(t.get("items") or [])
    blocked = int(t.get("blocked") or 0)
    head = (f'<div class="t-sm mut" style="margin-bottom:6px">Dziś przeczytałem '
            f'<b>{n_items}</b> {ui.pl_plural(n_items, "nagłówek", "nagłówki", "nagłówków")}'
            + (f', {blocked} {ui.pl_plural(blocked, "wstrzymał", "wstrzymały", "wstrzymało")} zakup'
               if blocked else "") + ".</div>")
    return head + "".join(rows)


def _how(cfg: dict) -> str:
    """Kolejnosc pracy. Badanie spolki jest krokiem, nie ozdoba."""
    r = cfg.get("research") or {}
    steps = [
        ("01", "Skan", "Szukam sygnału"),
        ("02", "Badanie", "Czytam raporty spółki"),
        ("03", "Wiadomości", "Sprawdzam wieści"),
        ("04", "Plan", "Stop i cel"),
        ("05", "Wielkość", "Ryzyko najwyżej 1%"),
        ("06", "Koniec dnia", "Zamykam wszystko"),
    ]
    if r.get("enabled") is False:
        steps = [s for s in steps if s[1] != "Badanie"]
    cells = "".join(f'''<div class="step"><div class="n">{n}</div>
      <div class="h">{esc(h)}</div><div class="d">{esc(d)}</div></div>''' for n, h, d in steps)
    rule = ""
    if r.get("enabled") is not False:
        spadek = abs(float(r.get("max_revenue_drop_pct") or -15.0))
        rule = ("<div class=\"empty\" style=\"margin-top:12px\">Nie kupuję spółki, która "
                "w ostatnim kwartale straciła pieniądze, ani takiej, której przychody "
                "spadły o więcej niż %.0f%% rok do roku. Wszystko, co sprawdzam, "
                "zapisuję przy decyzji.</div>") % spadek
    return f'<div class="steps">{cells}</div>{rule}'


def _glossary() -> str:
    return ('<div class="gloss">'
            + "".join(f'<div><b>{esc(k)}</b><br><span>{esc(v)}</span></div>' for k, v in plain.GLOSSARY)
            + "</div>")


def _footer(sim: dict, cfg: dict, equity: list[dict] | None = None) -> str:
    """Stopka jako tabela liczb, nie akapit. Wzrok czyta liczby szybciej."""
    c, s = cfg["costs"], cfg["simulation"]
    try:
        day = int(sim.get("day_count") or 0)
    except (TypeError, ValueError):
        day = 0
    items = [
        ("Start", pln(s["start_capital_pln"])),
        ("Co miesiąc", "+" + pln(s["monthly_deposit_pln"])),
        ("Dni symulacji", "%d" % int(s["days"])),
        ("Wymiana waluty", num(c["fx_cost_pct"], 1) + "%"),
        ("Poślizg ceny", num(_f(c["slippage_bps"]) / 100.0, 2) + "%"),
        ("Zasady podatku", "jak polski rachunek"),
    ]
    cells = "".join(f'<div><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v in items)
    # tabela podatkowa: kwoty z rachunku, nie zalozenia
    last = _last_row(equity or [])
    paid_pln = _f(last.get("tax_paid_pln") if last.get("tax_paid_pln") not in (None, "") else sim.get("tax_paid_pln"))
    owed_pln = _f(last.get("tax_owed_pln") if last.get("tax_owed_pln") not in (None, "") else sim.get("tax_reserve_pln"))
    loss_pln = _f(last.get("loss_carry_pln") if last.get("loss_carry_pln") not in (None, "") else sim.get("loss_carry_pln"))
    tax_items = [("Podatek od zysku", "%d%%" % int(_f(c["tax_on_gains_pct"]))),
                 ("Termin zapłaty", "30 kwietnia")]
    if paid_pln > 0.5:
        tax_items.append(("Zapłacony", pln(paid_pln)))
    if owed_pln > 0.5:
        tax_items.append(("Do zapłaty", pln(owed_pln)))
    if loss_pln > 0.5:
        tax_items.append(("Strata do odliczenia", pln(loss_pln)))
    if paid_pln <= 0.5 and owed_pln <= 0.5:
        tax_items.append(("Podatek", "jeszcze żaden"))
    tax_cells = "".join(f'<div><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v in tax_items)
    return f'''<footer>
  <div class="costs">{cells}</div>
  <div class="lab" style="margin:18px 0 8px">Podatek &mdash; zasady polskie</div>
  <div class="costs">{tax_cells}</div>
  <p class="fine">
    19% od zysku rozliczam <b>raz w roku</b>, nie od każdej transakcji. Płacę do 30 kwietnia
    roku następnego, a stratę odliczam przez 5 lat (maks. połowę rocznie).
  </p>
  <p class="fine">
    Ceny z Yahoo, opóźnione. Zlecenia wymyślone &mdash; nic nie idzie do brokera.
    <b>To nie porada inwestycyjna.</b>
  </p>
</footer>'''


def _empty_intro(cfg: dict) -> str:
    s = cfg["simulation"]
    return f'''<div class="hero-note">
  <div class="lab">Zaczynam {esc(s["start_date"])}</div>
  <div class="t-lg" style="margin:6px 0 4px;font-weight:600">
    Wpłata {pln(s["start_capital_pln"])}, potem {pln(s["monthly_deposit_pln"])} co miesiąc.
  </div>
  <div class="t-sm mut">
    Pierwsze decyzje po 15:30 czasu polskiego.
    <a class="lnk" href="przyklad-panelu.png">Zobacz przykład wypełnionego panelu</a>
  </div>
</div>'''


# ------------------------------------------------------------------ build
def build(sim: dict, cfg: dict) -> str:
    equity = store.read_csv(store.EQUITY)
    trades = store.read_csv(store.TRADES)
    decisions = _load_decisions()
    dep = _f(sim.get("deposits_pln_total"))

    body = [_masthead(sim, cfg, equity), _summary(sim, cfg, equity, trades, decisions)]
    if not dep and not trades:
        body.append(_empty_intro(cfg))

    detail = [
        ("s1", "Co mam teraz", "", _positions(sim, trades, equity)),
        ("s2", "Spółki, które obserwuję", "", _spolki(decisions, sim)),
        ("s3", "Dlaczego kupił albo sprzedał", "", _decisions(decisions)),
        ("s4", "Od czego do czego", "", _funnel(sim)),
        ("s5", "Czego się nauczył", "", _lessons(sim)),
        ("s6", "Co czytał", "", _news()),
        ("s7", "Jak działa", "", _how(cfg)),
        ("s8", "Słowniczek", "", _glossary()),
    ]
    body.append('<section><div class="sec-h"><div class="lab">Szczegóły</div></div>'
                '<div class="grid2">')
    for i, (sid, title, sub, content) in enumerate(detail):
        span = ' style="grid-column:1/-1"' if sid in ("s7", "s6") else ""
        body.append(f'''<div class="card" id="{sid}"{span}>
  <h3>{esc(title)}</h3>
  <div class="t-sm mut" style="margin:-6px 0 14px">{esc(sub)}</div>
  {content}
</div>''')
    body.append("</div></section>")
    body.append(_footer(sim, cfg, equity))

    html = f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Dziennik symulacji inwestowania: co bot zrobil i dlaczego.">
<title>XTB Day Trader — dziennik symulacji</title>
<style>{CSS}</style></head>
<body><div class="app">
{_sidebar()}
<main class="main">
{''.join(body)}
</main>
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

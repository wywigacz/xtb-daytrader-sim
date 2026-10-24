"""Klocki graficzne panelu: czysty SVG, bez bibliotek, bez JS.

Zasady, ktorymi sie kieruje (research: Microsoft Power BI dashboard tips,
WCAG 2.2, praktyka projektowania dashboardow):
  * wykres bez legendy - serie podpisane bezposrednio przy linii,
  * maksymalnie 3 linie siatki, etykiety osi 12 px (nie 10 px),
  * gruba linia danych, cienkie linie pomocnicze (data-ink ratio),
  * zadnych efektow 3D, kol kolowych ani wskaznikow "zegarowych".
"""
from __future__ import annotations

from html import escape


def esc(x) -> str:
    return escape(str(x if x is not None else ""), quote=True)


def esc_attr(x) -> str:
    return escape(str(x if x is not None else ""), quote=True)


NBSP = "\u00a0"


def pln(x, decimals: int = 0) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    s = ("{:,.%df}" % decimals).format(abs(v)).replace(",", NBSP)
    return sign + s.replace(".", ",") + NBSP + "zł"


def pln_short(x) -> tuple[str, str]:
    """(krotko, dokladnie): 110400 -> ('110,4 tys. zł', '110 400 zł').

    Duze liczby skracamy - czytanie '110,4 tys.' jest szybsze niz '110 400',
    a dokladna wartosc zostaje w drugiej linii.
    """
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—", "—"
    exact = pln(v)
    if abs(v) >= 1_000_000:
        return ("%.2f mln zł" % (v / 1_000_000)).replace(".", ","), exact
    if abs(v) >= 100_000:
        return ("%.1f tys. zł" % (v / 1_000)).replace(".", ","), exact
    return exact, exact


def usd(x, decimals: int = 2) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    s = ("{:,.%df}" % decimals).format(abs(v)).replace(",", NBSP)
    return sign + "$" + NBSP + s.replace(".", ",")


def pct(x, decimals: int = 1, plus: bool = True) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    fmt = ("{:+.%df}" if plus else "{:,.%df}") % decimals
    return fmt.format(v).replace(".", ",") + "%"


def num(x, decimals: int = 0) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    return ("{:,.%df}" % decimals).format(v).replace(",", NBSP).replace(".", ",")


def num_short(x) -> str:
    """1234 -> '1,2 tys.'; do gestszych miejsc (lejek, liczniki)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1000:
        return ("%.1f tys." % (v / 1000)).replace(".", ",")
    return num(v)


# ------------------------------------------------------------------ paleta
INK = "#0C1116"        # tekst glowny  (kontrast ~18:1 na papierze)
MUTED = "#55606E"      # tekst pomocniczy (kontrast ~6,5:1)
FAINT = "#5F6875"      # etykiety i godziny - 5,3:1 na papierze (WCAG AA)
LINE = "#E2DED5"
UP = "#0B6B4A"
DOWN = "#A32017"
ACCENT = "#1D3F8F"
PAPER = "#FAF9F6"


def _pt(x: float, y: float) -> str:
    return "%.1f,%.1f" % (x, y)


def line_chart(rows: list[dict], width: int = 1000, height: int = 228,
               narrow: bool = False) -> str:
    """Wykres kapitalu: portfel / wplacone / benchmark.

    Bez legendy - serie podpisane przy koncu linii (mniej przewijania okiem).
    """
    if not rows:
        return ('<div class="empty">Wykres pojawi sie po pierwszych dniach handlowych. '
                'Zielona linia to wartosc portfela, przerywana - suma wplat.</div>')
    # waska wersja ma mniej miejsca na podpisy i mniej etykiet osi
    pad_l, pad_r, pad_t, pad_b = 10, (72 if narrow else 104), 14, 26
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b

    vals: list[float] = []
    for r in rows:
        for k in ("equity_pln", "deposits_pln_total", "bench_pln"):
            v = r.get(k)
            if v not in (None, ""):
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
    if not vals:
        return '<div class="empty">Brak danych do wykresu.</div>'
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or max(abs(hi) * 0.1, 1.0)
    lo -= span * 0.14
    hi += span * 0.14
    n = len(rows)

    def X(i: int) -> float:
        return pad_l + (w * i / max(n - 1, 1))

    def Y(v: float) -> float:
        return pad_t + h - (float(v) - lo) / (hi - lo) * h

    def points(key: str) -> list[tuple[float, float]]:
        pts = []
        for i, r in enumerate(rows):
            v = r.get(key)
            if v in (None, ""):
                continue
            try:
                pts.append((X(i), Y(float(v))))
            except (TypeError, ValueError):
                continue
        return pts

    def path(pts) -> str:
        return "M " + " L ".join(_pt(*p) for p in pts) if len(pts) >= 2 else ""

    eq, dep, bench = points("equity_pln"), points("deposits_pln_total"), points("bench_pln")
    eq_path, dep_path, bench_path = path(eq), path(dep), path(bench)

    area = ""
    if eq_path:
        area = ('<path d="%s L %.1f,%.1f L %.1f,%.1f Z" fill="%s" fill-opacity="0.10" stroke="none"/>'
                % (eq_path, X(n - 1), pad_t + h, pad_l, pad_t + h, UP))

    # 3 linie siatki, etykiety 12 px, bez zbednych liczb
    grid, labels = [], []
    for k in range(3):
        y = pad_t + h * k / 2
        v = hi - (hi - lo) * k / 2
        grid.append('<line x1="%.0f" y1="%.1f" x2="%.0f" y2="%.1f" stroke="%s" stroke-width="1"/>'
                    % (pad_l, y, pad_l + w, y, LINE))
        labels.append('<text x="%.0f" y="%.1f" class="ax" text-anchor="end">%s</text>'
                      % (width - 2, y + 4, num_short(v).replace(NBSP, " ")))

    xlab = []
    step = max(1, n // (3 if narrow else 5))
    for i in range(0, n, step):
        d = str(rows[i].get("date") or "")
        if len(d) >= 10:
            xlab.append('<text x="%.1f" y="%.0f" class="ax" text-anchor="middle">%s</text>'
                        % (X(i), height - 6, esc(d[8:10] + "." + d[5:7])))

    # serie podpisane przy koncu linii - zamiast legendy
    def endlabel(pts, color, text, dy=0.0):
        if not pts:
            return ""
        x, y = pts[-1]
        return ('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>'
                '<text x="%.1f" y="%.1f" class="sv" fill="%s">%s</text>'
                % (x, y, color, x + 8, y + 4 + dy, color, esc(text)))

    lastv = ""
    if eq:
        x, y = eq[-1]
        short, _exact = pln_short(rows[-1].get("equity_pln"))
        lastv = ('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="#fff" stroke-width="2.5"/>'
                 '<text x="%.1f" y="%.1f" class="lastv">%s</text>'
                 % (x, y, UP, x + 9, y + 4, esc(short)))

    return f'''<svg viewBox="0 0 {width} {height}" width="100%" role="img"
     aria-label="Wartosc portfela w czasie" preserveAspectRatio="none">
  {''.join(grid)}{area}
  <path d="{dep_path}" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="{bench_path}" fill="none" stroke="{ACCENT}" stroke-width="1.6" stroke-dasharray="2 4" opacity="0.9"/>
  <path d="{eq_path}" fill="none" stroke="{UP}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
  {lastv}
  {endlabel(dep, MUTED, "Wplacone", dy=14)}{endlabel(bench, ACCENT, "S&P 500", dy=-8)}
  {''.join(labels)}{''.join(xlab)}
</svg>'''


def r_gauge(stop: float, entry: float, target: float, price: float | None) -> str:
    """Pasek: stop --- wejscie --- cel, z zaznaczona cena.

    Zrobiony w HTML/CSS, nie w SVG. Powod: SVG z preserveAspectRatio="none"
    rozciaga sie razem z tekstem i kolka staja sie elipsami - na telefonie
    wygladalo to zle. Tutaj tekst jest zwyklym tekstem, a kropki zwyklymi
    elementami o stalym rozmiarze.
    """
    try:
        stop, entry, target = float(stop), float(entry), float(target)
        price = float(price) if price else entry
    except (TypeError, ValueError):
        return ""
    lo, hi = min(stop, price, entry), max(target, price, entry)
    if hi <= lo:
        return ""

    def X(v: float) -> float:
        return 2 + (v - lo) / (hi - lo) * 96

    xs, xe, xt, xp = X(stop), X(entry), X(target), X(price)
    color = "var(--up)" if price >= entry else "var(--down)"
    return (
        '<div class="rg" role="img" aria-label="Odleglosc ceny od stopu i celu">'
        '<div class="rg-track"></div>'
        f'<div class="rg-seg" style="left:{xs:.1f}%;width:{max(xe - xs, 0):.1f}%;background:var(--down)"></div>'
        f'<div class="rg-seg" style="left:{xe:.1f}%;width:{max(xt - xe, 0):.1f}%;background:var(--up)"></div>'
        f'<div class="rg-dot" style="left:{xs:.1f}%;background:var(--down)"></div>'
        f'<div class="rg-dot" style="left:{xt:.1f}%;background:var(--up)"></div>'
        f'<div class="rg-entry" style="left:{xe:.1f}%"></div>'
        f'<div class="rg-price" style="left:{xp:.1f}%;background:{color}"></div>'
        f'<div class="rg-lab" style="left:{max(xs, 9):.1f}%">stop</div>'
        f'<div class="rg-lab" style="left:{min(xt, 91):.1f}%">cel</div>'
        '</div>')


def funnel(steps: list[tuple[str, str, str]]) -> str:
    """Lejek: liczba + nazwa + jedno zdanie. Szerokosc paska = wielkosc liczby."""
    if not steps:
        return ""
    rows = []
    n = len(steps)
    for i, (value, label, note) in enumerate(steps):
        width = 100 - i * (44 / max(n, 1))
        rows.append(f'''<div class="fn-row">
  <div class="fn-bar" style="width:{width:.1f}%">
    <span class="fn-val">{esc(value)}</span><span class="fn-lab">{esc(label)}</span>
  </div>
  <div class="fn-note">{esc(note)}</div>
</div>''')
    return '<div class="fn">' + "".join(rows) + "</div>"

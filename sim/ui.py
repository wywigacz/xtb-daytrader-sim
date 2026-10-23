"""Klocki graficzne panelu: czysty SVG, bez bibliotek, bez JS.

Kazda funkcja zwraca kawalek HTML/SVG. Dzieki temu panel wyglada tak samo
w przegladarce i na zrzucie PNG (ktory robi sie w GitHub Actions).
"""
from __future__ import annotations

from html import escape


def esc(x) -> str:
    return escape(str(x if x is not None else ""), quote=True)


def esc_attr(x) -> str:
    return escape(str(x if x is not None else ""), quote=True)


def pln(x, decimals: int = 0) -> str:
    """1234567 -> '1 234 567 zl' (polski format: spacja w tysiacach)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    s = ("{:,.%df}" % decimals).format(abs(v))
    s = s.replace(",", "\u00a0").replace(".", ",")
    return sign + s + "\u00a0zl"


def usd(x, decimals: int = 2) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    s = ("{:,.%df}" % decimals).format(abs(v))
    return sign + "$\u00a0" + s.replace(",", "\u00a0").replace(".", ",")


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
    s = ("{:,.%df}" % decimals).format(v)
    return s.replace(",", "\u00a0").replace(".", ",")


# ----------------------------------------------------------------- własności
INKE = "#101418"
MUTED = "#6A7079"
LINE = "#E3E0D8"
UP = "#0E6B4F"
DOWN = "#A32017"
ACCENT = "#1D3F8F"
SAND = "#F1EEE6"


def _pt(x: float, y: float) -> str:
    return "%.1f,%.1f" % (x, y)


def line_chart(rows: list[dict], width: int = 1000, height: int = 300) -> str:
    """Wykres kapitalu: portfel / wplacone / benchmark. Czysty SVG."""
    if not rows:
        return ('<div class="empty">Tu pojawi sie wykres, gdy tylko zaczna sie pierwsze dni handlowe.'
                '</div>')
    pad_l, pad_r, pad_t, pad_b = 8, 96, 18, 30
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
    span = (hi - lo) or max(hi * 0.1, 1.0)
    lo -= span * 0.12
    hi += span * 0.12
    n = len(rows)

    def X(i: int) -> float:
        return pad_l + (w * i / max(n - 1, 1))

    def Y(v: float) -> float:
        return pad_t + h - (float(v) - lo) / (hi - lo) * h

    def path(key: str) -> str:
        pts = []
        for i, r in enumerate(rows):
            v = r.get(key)
            if v in (None, ""):
                continue
            try:
                pts.append((X(i), Y(float(v))))
            except (TypeError, ValueError):
                continue
        if len(pts) < 2:
            return ""
        return "M " + " L ".join(_pt(*p) for p in pts)

    eq_path = path("equity_pln")
    dep_path = path("deposits_pln_total")
    bench_path = path("bench_pln")
    area = ""
    if eq_path:
        first_x = pad_l
        last_x = X(n - 1)
        area = ('<path d="%s L %.1f,%.1f L %.1f,%.1f Z" fill="#0E6B4F" fill-opacity="0.09" stroke="none"/>'
                % (eq_path, last_x, pad_t + h, first_x, pad_t + h))

    grid = []
    for k in range(4):
        y = pad_t + h * k / 3
        v = hi - (hi - lo) * k / 3
        grid.append('<line x1="%.0f" y1="%.1f" x2="%.0f" y2="%.1f" stroke="%s" stroke-width="1"/>'
                    % (pad_l, y, pad_l + w, y, LINE))
        grid.append('<text x="%.0f" y="%.1f" class="ax" text-anchor="end">%s</text>'
                    % (width - 2, y + 4, num(round(v), 0).replace("\u00a0", " ")))

    xlab = []
    step = max(1, n // 6)
    for i in range(0, n, step):
        d = str(rows[i].get("date") or "")
        xlab.append('<text x="%.1f" y="%.0f" class="ax" text-anchor="middle">%s</text>'
                    % (X(i), height - 8, esc(d[8:10] + "." + d[5:7] if len(d) >= 10 else "")))

    last = rows[-1]
    lx, ly = X(n - 1), Y(float(last.get("equity_pln") or 0))
    marker = ('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="%s" stroke-width="2"/>'
              % (lx, ly, UP, "#fff"))
    label = ('<text x="%.1f" y="%.1f" class="lastv" text-anchor="start">%s</text>'
             % (lx + 10, ly + 5, pln(last.get("equity_pln") or 0)))

    # legenda
    leg = []
    for i, (name, color, dash) in enumerate((
            ("Wartosc portfela", UP, ""),
            ("Wplacone", MUTED, ' stroke-dasharray="6 4"'),
            ("S&P 500 (te same wplaty)", ACCENT, ' stroke-dasharray="2 4"'))):
        x = pad_l + i * 250
        leg.append('<line x1="%.0f" y1="%d" x2="%.0f" y2="%d" stroke="%s" stroke-width="2.5"%s/>'
                   % (x, 12, x + 22, 12, color, dash))
        leg.append('<text x="%.0f" y="%d" class="lg">%s</text>' % (x + 30, 16, esc(name)))

    return f'''<svg viewBox="0 0 {width} {height}" width="100%" role="img"
     aria-label="Wykres wartosci portfela w czasie" preserveAspectRatio="none">
  {''.join(grid)}
  {area}
  <path d="{dep_path}" fill="none" stroke="{MUTED}" stroke-width="1.8" stroke-dasharray="6 4"/>
  <path d="{bench_path}" fill="none" stroke="{ACCENT}" stroke-width="1.6" stroke-dasharray="2 4" opacity="0.85"/>
  <path d="{eq_path}" fill="none" stroke="{UP}" stroke-width="2.6" stroke-linejoin="round"/>
  {marker}{label}
  {''.join(leg)}
  {''.join(xlab)}
</svg>'''


def r_gauge(stop: float, entry: float, target: float, price: float | None) -> str:
    """Pasek: stop --- wejscie --- cel, z zaznaczona aktualna cena."""
    try:
        stop, entry, target = float(stop), float(entry), float(target)
        price = float(price) if price else entry
    except (TypeError, ValueError):
        return ""
    lo = min(stop, price, entry)
    hi = max(target, price, entry)
    if hi <= lo:
        return ""

    def X(v: float) -> float:
        return 6 + (v - lo) / (hi - lo) * 88

    xe, xs, xt, xp = X(entry), X(stop), X(target), X(price)
    color = UP if price >= entry else DOWN
    return f'''<svg viewBox="0 0 100 16" width="100%" height="16" preserveAspectRatio="none"
     aria-label="Odleglosc od stopu i celu">
  <line x1="6" y1="9" x2="94" y2="9" stroke="{LINE}" stroke-width="3" stroke-linecap="round"/>
  <line x1="{xs:.1f}" y1="9" x2="{xe:.1f}" y2="9" stroke="{DOWN}" stroke-width="3" stroke-linecap="round" opacity="0.35"/>
  <line x1="{xe:.1f}" y1="9" x2="{xt:.1f}" y2="9" stroke="{UP}" stroke-width="3" stroke-linecap="round" opacity="0.35"/>
  <circle cx="{xs:.1f}" cy="9" r="2.6" fill="{DOWN}"/>
  <circle cx="{xt:.1f}" cy="9" r="2.6" fill="{UP}"/>
  <circle cx="{xe:.1f}" cy="9" r="2.2" fill="#fff" stroke="{MUTED}" stroke-width="1.4"/>
  <circle cx="{xp:.1f}" cy="9" r="3.4" fill="{color}" stroke="#fff" stroke-width="1.4"/>
</svg>'''


def funnel(steps: list[tuple[str, str, str]]) -> str:
    """Lejek decyzji: [(liczba, etykieta, dopisek)] - malejace szerokosci."""
    if not steps:
        return ""
    rows = []
    n = len(steps)
    for i, (value, label, note) in enumerate(steps):
        width = 100 - i * (42 / max(n, 1))
        opacity = 1 - i * 0.12
        rows.append(f'''<div class="fn-row">
  <div class="fn-bar" style="width:{width:.1f}%;opacity:{opacity:.2f}">
    <span class="fn-val">{esc(value)}</span><span class="fn-lab">{esc(label)}</span>
  </div>
  <div class="fn-note">{esc(note)}</div>
</div>''')
    return '<div class="fn">' + "".join(rows) + "</div>"


def gauge_ring(fraction: float, label: str, sub: str, size: int = 92) -> str:
    """Pierscien postepu (0-1)."""
    try:
        f = max(0.0, min(1.0, float(fraction)))
    except (TypeError, ValueError):
        f = 0.0
    r = 38
    c = 2 * 3.14159265 * r
    dash = c * f
    return f'''<div class="ring">
  <svg viewBox="0 0 92 92" width="{size}" height="{size}" aria-hidden="true">
    <circle cx="46" cy="46" r="{r}" fill="none" stroke="{LINE}" stroke-width="8"/>
    <circle cx="46" cy="46" r="{r}" fill="none" stroke="{UP}" stroke-width="8"
            stroke-linecap="round" stroke-dasharray="{dash:.1f} {c:.1f}"
            transform="rotate(-90 46 46)"/>
    <text x="46" y="51" text-anchor="middle" class="ring-v">{esc(label)}</text>
  </svg>
  <div class="ring-s">{esc(sub)}</div>
</div>'''

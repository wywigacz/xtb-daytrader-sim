"""Model kosztow brokera XTB (Polska) dla symulacji. Tylko stdlib.

ZALOZENIA (wszystkie konfigurowalne w sim/config.json, patrz docs/XTB-ZALOZENIA.md):
  * Rachunek w PLN, handel akcjami realnymi USA (XTB: 0% prowizji do limitu
    obrotu w miesiacu; powyzej limitu prowizja procentowa).
  * Przewalutowanie PLN->USD po kursie XTB; narzut (spread) domyslnie 0.5%.
    W symulacji wymieniamy raz, przy wplacie - dalej srodki zostaja w USD
    (tak robi trader, ktory nie wyprowadza zyskow co miesiac).
  * Poslizg (slippage) rynkowy: domyslnie 5 pkt bazowych (0.05%) na niekorzysc.
  * Podatek Belki 19% od zrealizowanych zyskow, odkladany do rezerwy.
"""
from __future__ import annotations


def fx_pln_to_usd(pln: float, usdpln: float, cost_pct: float) -> tuple[float, float]:
    """Zwraca (usd_netto, koszt_usd) dla wymiany pln -> usd po kursie usdpln."""
    if usdpln <= 0:
        raise ValueError("kurs USD/PLN musi byc dodatni")
    gross = pln / usdpln
    fee = gross * (cost_pct / 100.0)
    return round(gross - fee, 2), round(fee, 2)


def usd_to_pln(usd: float, usdpln: float) -> float:
    return round(usd * usdpln, 2)


def commission_usd(notional_usd: float, commission_pct: float, min_usd: float = 0.0) -> float:
    c = notional_usd * (commission_pct / 100.0)
    if notional_usd > 0 and c > 0:
        c = max(c, min_usd)
    return round(c, 2)


def slippage_price(price: float, side: str, slippage_bps: float) -> float:
    """Cena po poslizgu: kupno drozej, sprzedaz taniej."""
    adj = price * (slippage_bps / 10000.0)
    return round(price + adj, 4) if side == "buy" else round(price - adj, 4)


def tax_on_gain(gain_usd: float, usdpln: float, tax_pct: float) -> float:
    """Podatek Belki od zysku (w PLN) -> zwraca PLN."""
    if gain_usd <= 0:
        return 0.0
    return round(gain_usd * usdpln * (tax_pct / 100.0), 2)

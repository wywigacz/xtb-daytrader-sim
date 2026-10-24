"""Model kosztów brokera XTB (Polska) dla symulacji. Tylko stdlib.

ZALOZENIA (wszystkie konfigurowalne w sim/config.json, patrz docs/XTB-ZALOZENIA.md):
  * Rachunek w PLN, handel akcjami realnymi USA (XTB: 0% prowizji do limitu
    obrotu w miesiacu; powyzej limitu prowizja procentowa).
  * Przewalutowanie PLN->USD po kursie XTB; narzut (spread) domyslnie 0.5%.
    W symulacji wymieniamy raz, przy wplacie - dalej srodki zostaja w USD
    (tak robi trader, który nie wyprowadza zyskow co miesiąc).
  * Poślizg (slippage) rynkowy: domyslnie 5 pkt bazowych (0.05%) na niekorzyść.
  * Podatek 19% od zysku, rozliczany RAZ W ROKU jak na polskim rachunku.
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
    """Cena po poślizgu: kupno drozej, sprzedaż taniej."""
    adj = price * (slippage_bps / 10000.0)
    return round(price + adj, 4) if side == "buy" else round(price - adj, 4)


def tax_on_gain(gain_usd: float, usdpln: float, tax_pct: float) -> float:
    """Podatek Belki od zysku (w PLN) -> zwraca PLN."""
    if gain_usd <= 0:
        return 0.0
    return round(gain_usd * usdpln * (tax_pct / 100.0), 2)


# ---------------------------------------------------------------------------
# Podatek od zyskow kapitalowych - zasady polskie (zwykly rachunek maklerski)
#
#  * 19% od dochodu, ale rozliczane RAZ W ROKU, nie od pojedynczej transakcji
#    (art. 30a ustawy o PIT). W trakcie roku nic nie placisz.
#  * Strata z danego roku obniza dochod w NASTEPNYCH latach: maksymalnie 5 lat
#    i nie wiecej niz 50% kwoty straty w jednym roku (art. 9 ust. 3 PIT).
#  * Deklaracja PIT-38 i zaplata podatku - do 30 kwietnia roku nastepnego.
#    Do tego dnia pieniadze na podatek pracuja na koncie.
#  * Przychod i koszt przelicza sie po kursie NBP z dnia poprzedzajacego
#    transakcje. Tu liczymy wynik dnia po kursie dnia (uproszczenie -
#    przy transakcjach jednodniowych roznica jest znikoma).
# ---------------------------------------------------------------------------
TAX_PAY_MONTH_DAY = (4, 30)   # 30 kwietnia
TAX_LOSS_YEARS = 5            # ile lat mozna odliczac strate
TAX_LOSS_SHARE = 0.5          # max 50% straty z lat ubieglych na jeden rok


def settle_tax_year(net_pln: float, carried_loss_pln: float, tax_pct: float):
    """Rozlicza JEDEN rok podatkowy po polsku.

    net_pln          - wynik roku w PLN (zyski minus straty tego roku)
    carried_loss_pln - nieodliczona strata z lat ubieglych
    zwraca (podatek_pln, odliczona_strata_pln, strata_do_przeniesienia_pln)
    """
    net = float(net_pln or 0)
    carried = max(0.0, float(carried_loss_pln or 0))
    if net <= 0:
        # dochodu nie ma: podatku nie ma, a strata rosnie
        return 0.0, 0.0, round(carried + abs(net), 2)
    # z dochodu mozna odjac najwyzej polowe straty z lat ubieglych
    deduction = min(carried * TAX_LOSS_SHARE, net)
    tax = round((net - deduction) * (float(tax_pct) / 100.0), 2)
    return tax, round(deduction, 2), round(carried - deduction, 2)


def accrued_tax_year(net_pln: float, carried_loss_pln: float, tax_pct: float) -> float:
    """Podatek naliczony za rok jeszcze nierozliczony (do pokazania w panelu)."""
    return settle_tax_year(net_pln, carried_loss_pln, tax_pct)[0]

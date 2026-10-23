"""Tlumaczenie technicznych komunikatow skilla na krotki, prosty polski.

Skill (day-trader-skill) pisze po angielsku i technicznie, np.
    "loss: 9 shares x 5.86 risk a share = $52.74 at the stop, over your $50 max loss per trade"
Panel ma byc zrozumialy dla osoby bez wiedzy finansowej, wiec kazdy powod
dostaje jeden krotki polski opis + kod (do kolorowania i statystyk).
"""
from __future__ import annotations

from datetime import datetime

# Kody powodow odrzucenia -> krotki polski + "co to znaczy" (jedno zdanie).
BLOCK_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (("max loss per trade", "loss:"), "strata",
     "Za duza strata na jedna transakcje",
     "Gdyby cena spadla do stopu, stracilbym wiecej niz moj limit na jedna transakcje."),
    (("reward:risk", "reward : risk"), "cel",
     "Cel zbyt blisko ceny wejscia",
     "Do celu zostalo mniej niz do stopu, wiec gra nie byla warta ryzyka."),
    (("position cap", "position:"), "koncentracja",
     "Za duza pozycja w jednej spolce",
     "Jedna spolka mialaby za duzy udzial w calym portfelu."),
    (("cash buffer", "cash:"), "gotowka",
     "Za malo gotowki zostaloby na koncie",
     "Zlamalbym zasade trzymania bufora gotowki."),
    (("window", "before ", "after "), "godziny",
     "Za wczesnie albo za pozno na wejscie",
     "Poza godzinami, w ktorych ta metoda pozwala otwierac nowe pozycje."),
    (("trades per day", "trades:"), "limit",
     "Wyczerpany dzienny limit transakcji",
     "Mialem juz tyle transakcji dzisiaj, ile pozwalaja zasady."),
    (("duplicate",), "duplikat",
     "Ta spolka byla juz dzis grana",
     "Nie dokladam do pozycji, ktora juz otworzylem tego dnia."),
    (("blocked",), "zakaz",
     "Spolka na liscie wykluczonych",
     "Ta spolka jest recznie zablokowana w ustawieniach."),
    (("daily loss", "daily limit"), "limit-strat",
     "Dzienny limit strat osiagniety",
     "Dzisiejsze straty wyczerpaly limit - koniec handlu na dzis."),
    (("stop",), "stop",
     "Brak zabezpieczenia (stop-loss)",
     "Nie kupuje bez z gory ustalonego poziomu wyjscia ze straty."),
    (("short",), "krotka",
     "Krotka sprzedaz niedozwolona",
     "Ta symulacja gra tylko na wzrosty."),
    (("option", "crypto", "asset"), "typ",
     "Niedozwolony typ instrumentu",
     "Symulacja handluje tylko akcjami, nie opcjami ani kryptowalutami."),
    (("format", "malformed"), "format",
     "Blednie zbudowane zlecenie",
     "Zlecenie nie mialo poprawnego ksztaltu - odrzucone technicznie."),
    (("min order", "under your minimum"), "minimum",
     "Zlecenie za male",
     "Pozycja bylaby mniejsza niz minimalna wartosc zlecenia."),
]

SIZE_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (("reward:risk", "the move it was waiting for"), "cel",
     "Cena juz odjechala - nie gonie",
     "Do celu zostalo zbyt malo miejsca. Wejscie teraz to gra o grosze przy duzym ryzyku."),
    (("too far away", "zero shares", "no order"), "strata",
     "Stop zbyt daleko jak na limit straty",
     "Przy tym stopie nawet 1 akcja ryzykuje wiecej, niz pozwalaja zasady."),
    (("not fresh", "older than", "stale"), "dane",
     "Cena z rynku byla nieaktualna",
     "Nie ufam nieaktualnej cenie - odczekalem na swieza."),
    (("refus", "refused"), "odmowa",
     "Plan nie spelnil warunkow",
     "Plan wejscia nie przeszedl kontroli - wolalem odpuscic."),
]

EXIT_PL = {
    "target": ("Cel osiagniety", "Cena doszla do zalozonego celu - zamkniete z zyskiem."),
    "stop": ("Stop-loss zadzialal", "Cena spadla do poziomu, ktorym chronilem kapital - zamkniete ze strata."),
    "flat_by": ("Koniec dnia", "Zamkniete przed zamknieciem gieldy - nic nie zostaje na noc."),
    "eod_flat": ("Awaryjne domkniecie", "Po sesji zostala pozycja, wiec domknalem ja po ostatniej cenie."),
}

EXIT_SHORT = {"target": "cel", "stop": "stop", "flat_by": "koniec dnia", "eod_flat": "awaryjnie"}


def classify(text: str, rules) -> tuple[str, str, str]:
    low = str(text or "").lower()
    for keys, code, title, meaning in rules:
        if any(k in low for k in keys):
            return code, title, meaning
    return "inne", "Odrzucone przez kontrole ryzyka", "Zlecenie nie przeszlo kontroli."


def block_reason(text: str) -> tuple[str, str, str]:
    return classify(text, BLOCK_RULES)


def size_reason(text: str) -> tuple[str, str, str]:
    return classify(text, SIZE_RULES)


def exit_reason(code: str) -> tuple[str, str]:
    return EXIT_PL.get(code, ("Zamkniete", "Pozycja zamknieta."))


def exit_short(code: str) -> str:
    return EXIT_SHORT.get(code, code or "-")


GLOSSARY = [
    ("Stop-loss", "Poziom ceny, przy ktorym automatycznie sprzedaje, zeby ograniczyc strate. Jak hamulec bezpieczenstwa."),
    ("Cel (target)", "Poziom ceny, przy ktorym biore zysk. Ustawiony z gory, przed wejsciem."),
    ("R", "Jednostka ryzyka. 1R = tyle, ile moge stracic na jednej transakcji. Wynik +1R = zarobilem tyle, ile bylem gotow stracic."),
    ("Opening range", "Zakres cen z pierwszych 15 minut sesji. Jego przebicie to sygnal, ktorego szuka bot."),
    ("Pozycja", "Akcje, ktore w danej chwili posiadam."),
    ("Gotowka", "Pieniadze na koncie, ktore nie sa zainwestowane."),
    ("Poslizg", "Roznica miedzy cena, ktora widze, a cena, po ktorej naprawde kupuje. Zawsze troche na moja niekorzysc."),
    ("Podatek Belki", "19% podatku od zysku ze sprzedazy akcji. Odkladam go z gory, zeby nie zniknal z wyniku."),
    ("Benchmark", "Wzorzec do porownania. Tu: co by bylo, gdybym te same wplaty wrzucil w indeks S&P 500."),
]


def money_pl(x, suffix: str = " zl") -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "-"
    s = "{:,.0f}".format(abs(v)).replace(",", " ")
    return ("-" if v < 0 else "") + s + suffix


def usd(x) -> str:
    try:
        return "${:,.2f}".format(float(x)).replace(",", " ")
    except (TypeError, ValueError):
        return "-"


def pct(x, digits: int = 1) -> str:
    try:
        return ("{:+,." + str(digits) + "f}%").format(float(x)).replace(".", ",")
    except (TypeError, ValueError):
        return "-"


def clock(ts: str) -> str:
    """'2026-10-23 10:20' -> '10:20'."""
    try:
        return datetime.strptime(str(ts)[:16], "%Y-%m-%d %H:%M").strftime("%H:%M")
    except ValueError:
        return str(ts)[:5]


def day_month(ts: str) -> str:
    try:
        d = datetime.strptime(str(ts)[:10], "%Y-%m-%d")
        return "%d.%m" % (d.day, d.month)
    except ValueError:
        return str(ts)[:10]


DOW = ["poniedzialek", "wtorek", "sroda", "czwartek", "piatek", "sobota", "niedziela"]


def weekday_pl(ts: str) -> str:
    try:
        return DOW[datetime.strptime(str(ts)[:10], "%Y-%m-%d").weekday()]
    except ValueError:
        return ""

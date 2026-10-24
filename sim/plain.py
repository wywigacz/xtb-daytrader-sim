"""Tlumaczenie technicznych komunikatow skilla na krótki, prosty polski.

Skill (day-trader-skill) pisze po angielsku i technicznie, np.
    "loss: 9 shares x 5.86 risk a share = $52.74 at the stop, over your $50 max loss per trade"
Panel ma byc zrozumiały dla osoby bez wiedzy finansowej, wiec każdy powod
dostaje jeden krótki polski opis + kod (do kolorowania i statystyk).
"""
from __future__ import annotations

from datetime import datetime

# Kody powodow odrzucenia -> krotki polski + "co to znaczy" (jedno zdanie).
BLOCK_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    # kolejnosc ma znaczenie: najpierw wezsze reguly (dzienny limit strat),
    # potem ogolne - inaczej "daily loss:" zostalby rozpoznany jako zwykla strata
    (("daily loss", "daily limit"), "limit-strat",
     "Dzienny limit strat osiągnięty",
     "Dzisiejsze straty wyczerpaly limit - koniec handlu na dziś."),
    (("max loss per trade",), "strata",
     "Za duża strata na jedna transakcje",
     "Gdyby cena spadła do stopu, stracilbym więcej niz moj limit na jedna transakcje."),
    (("reward:risk", "reward : risk"), "cel",
     "Cel zbyt blisko ceny wejścia",
     "Do celu zostało mniej niz do stopu, wiec gra nie była warta ryzyka."),
    (("position cap", "position:"), "koncentracja",
     "Za duża pozycja w jednej spolce",
     "Jedna spółka mialaby za duży udział w calym portfelu."),
    (("cash buffer", "cash:"), "gotówka",
     "Za mało gotówki zostaloby na koncie",
     "Zlamalbym zasade trzymania bufora gotówki."),
    (("window", "before ", "after "), "godziny",
     "Za wczesnie albo za pozno na wejście",
     "Poza godzinami, w których ta metoda pozwala otwierac nowe pozycje."),
    (("trades per day", "trades:"), "limit",
     "Wyczerpany dzienny limit transakcji",
     "Mialem już tyle transakcji dzisiaj, ile pozwalaja zasady."),
    (("duplicate",), "duplikat",
     "Ta spółka była już dziś grana",
     "Nie dokladam do pozycji, która już otworzylem tego dnia."),
    (("blocked",), "zakaz",
     "Spółka na liście wykluczonych",
     "Ta spółka jest recznie zablokowana w ustawieniach."),
    (("stop",), "stop",
     "Brak zabezpieczenia (stop-loss)",
     "Nie kupuję bez z góry ustalonego poziomu wyjścia że straty."),
    (("short",), "krótka",
     "Krotka sprzedaż niedozwolona",
     "Ta symulacja gra tylko na wzrosty."),
    (("option", "crypto", "asset"), "typ",
     "Niedozwolony typ instrumentu",
     "Symulacja handluje tylko akcjami, nie opcjami ani kryptowalutami."),
    (("format", "malformed"), "format",
     "Blednie zbudowane zlecenie",
     "Zlecenie nie mialo poprawnego ksztaltu - odrzucone technicznie."),
    (("min order", "under your minimum"), "minimum",
     "Zlecenie za małe",
     "Pozycja bylaby mniejsza niz minimalna wartość zlecenia."),
]

SIZE_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (("reward:risk", "the move it was waiting for", "the move has already happened",
      "not above the entry"), "cel",
     "Cena już odjechala - nie gonie",
     "Cena poszła wyzej, niz miałem w planie, zanim zdazylem kupić. Do celu nie ma już miejsca."),
    (("too far away", "zero shares", "no order"), "strata",
     "Stop zbyt daleko jak na limit straty",
     "Przy tym stopie nawet 1 akcja ryzykuję więcej, niz pozwalaja zasady."),
    (("not fresh", "older than", "stale"), "dane",
     "Cena z rynku była nieaktualna",
     "Nie ufam nieaktualnej cenie - odczekalem na świeża."),
    (("refus", "refused"), "odmowa",
     "Plan nie spelnil warunkow",
     "Plan wejścia nie przeszedl kontroli - wolalem odpuscic."),
]

EXIT_PL = {
    "target": ("Cel osiągnięty", "Cena doszła do zalozonego celu - zamknięte z zyskiem."),
    "stop": ("Stop-loss zadziałał", "Cena spadła do poziomu, którym chronilem kapitał - zamknięte że strata."),
    "flat_by": ("Koniec dnia", "Zamknięte przed zamknięciem giełdy - nic nie zostaje na noc."),
    "eod_flat": ("Awaryjne domkniecie", "Po sesji została pozycja, wiec domknalem ja po ostatniej cenie."),
}

EXIT_SHORT = {"target": "cel", "stop": "stop", "flat_by": "koniec dnia", "eod_flat": "awaryjnie"}


def classify(text: str, rules) -> tuple[str, str, str]:
    low = str(text or "").lower()
    for keys, code, title, meaning in rules:
        if any(k in low for k in keys):
            return code, title, meaning
    return "inne", "Odrzucone przez kontrole ryzyka", "Zlecenie nie przeszło kontroli."


def block_reason(text: str) -> tuple[str, str, str]:
    return classify(text, BLOCK_RULES)


def size_reason(text: str) -> tuple[str, str, str]:
    return classify(text, SIZE_RULES)


def exit_reason(code: str) -> tuple[str, str]:
    return EXIT_PL.get(code, ("Zamknięte", "Pozycja zamknięta."))


def exit_short(code: str) -> str:
    return EXIT_SHORT.get(code, code or "-")


# Kody, ktore nadaje wlasny silnik (z wlasnym tytulem i uzasadnieniem).
# Trzymane OSOBNO: title_for/meaning_for ich uzywaja, ale classify() nie -
# inaczej slowa typu "size" albo "news" przeszkadzalyby w dopasowaniu
# komunikatow skilla.
CODE_ONLY: list[tuple[str, str, str]] = [
    ("cena-pod-stopem", "Cena zdążyła zjechac pod stop",
     "Po sygnale cena spadła ponizej poziomu, na którym miałem się wycofać. "
     "Wejście teraz to strata ustawiona z góry."),
    ("news", "Wiadomosci wstrzymaly zakup",
     "Naglowek o realnym wstrzasie (wstrzymanie handlu, upadlosc, dochodzenie, krach). "
     "Nie kupuję, gdy cena może skoczyc w obie strony."),
    ("cel", "Cel zbyt blisko ceny wejścia",
     "Do zysku zostało mniej miejsca niz do straty, wiec gra nie była warta ryzyka."),
    ("plan", "Nie udało się ustalic stopu i celu",
     "Bez z góry ustalonego wyjścia nie wchodze - plan musi istniec przed zakupem."),
    ("size", "Kalkulator nie znalazł bezpiecznego rozmiaru",
     "Przy tak ustawionym stopie żadna liczba akcji nie miescila się w limicie straty."),
    ("fill", "Nie udało się zapisać wykonania",
     "Zlecenie przeszło kontrole, ale zapis realizacji się nie powiodl."),
    ("dane", "Brak wiarygodnej ceny",
     "Feed nie dal ceny, której moglbym zaufac - nie ryzykowalem."),
]


def has_code(code: str) -> bool:
    """Czy kod ma własne, napisane po polsku wyjaśnienie?"""
    return any(c == code for c, _title, _meaning in CODE_ONLY)


def meaning_for(code: str) -> str:
    """Jedno zdanie 'co to znaczy' dla kodu odrzucenia (zbiorczo dla panelu)."""
    for rules in (BLOCK_RULES, SIZE_RULES):
        for keys, c, _title, meaning in rules:
            if c == code:
                return meaning
    for c, _title, meaning in CODE_ONLY:
        if c == code:
            return meaning
    return "Zlecenie nie przeszło kontroli."


def title_for(code: str) -> str:
    for c, title, _meaning in CODE_ONLY:
        if c == code:
            return title
    for rules in (BLOCK_RULES, SIZE_RULES):
        for keys, c, title, meaning in rules:
            if c == code:
                return title
    return "Odrzucone przez kontrole ryzyka"


GLOSSARY = [
    ("Stop-loss", "Poziom ceny, przy którym automatycznie sprzedaję, żeby ograniczyć stratę. Jak hamulec bezpieczeństwa."),
    ("Cel (target)", "Poziom ceny, przy którym biorę zysk. Ustawiony z góry, przed wejściem."),
    ("R", "Jednostka ryzyka. 1R = tyle, ile mogę stracić na jednej transakcji. Wynik +1R = zarobiłem tyle, ile byłem gotów stracić."),
    ("Opening range", "Zakres cen z pierwszych 15 minut sesji. Jego przebicie to sygnał, którego szuka bot."),
    ("Pozycja", "Akcje, które w danej chwili posiadam."),
    ("Gotówka", "Pieniądze na koncie, które nie są zainwestowane."),
    ("Poślizg", "Różnica między ceną, którą widzę, a ceną, po której naprawdę kupuję. Zawsze trochę na moją niekorzyść."),
    ("Podatek Belki", "19% podatku od zysku ze sprzedaży akcji. Odkładam go z góry, żeby nie zniknął z wyniku."),
    ("Benchmark", "Wzorzec do porównania. Tu: co by było, gdybym te same wpłaty wrzucił w indeks S&P 500."),
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


DOW = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]


def weekday_pl(ts: str) -> str:
    try:
        return DOW[datetime.strptime(str(ts)[:10], "%Y-%m-%d").weekday()]
    except ValueError:
        return ""

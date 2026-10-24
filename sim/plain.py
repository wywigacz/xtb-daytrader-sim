"""Tlumaczenie technicznych komunikatow skilla na krótki, prosty polski.

Skill (day-trader-skill) pisze po angielsku i technicznie, np.
    "loss: 9 shares x 5.86 risk a share = $52.74 at the stop, over your $50 max loss per trade"
Panel ma być zrozumiały dla osoby bez wiedzy finansowej. Dlatego:
  * tytul powodu: najwyżej 5 slow, bez żargonu,
  * wyjaśnienie: jedno krótkie zdanie, najwyżej ~12 slow,
  * żadnych skrotow ani nazw, których trzeba się domyślać.
"""
from __future__ import annotations

from datetime import datetime

# Kody powodow odrzucenia -> krótki polski + "co to znaczy" (jedno zdanie).
BLOCK_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    # kolejnosc ma znaczenie: najpierw wezsze reguly (dzienny limit strat),
    # potem ogolne - inaczej "daily loss:" zostalby rozpoznany jako zwykla strata
    (("daily loss", "daily limit"), "limit-strat",
     "Limit strat na dziś",
     "Straciłem dziś tyle, ile wolno. Koniec na dziś."),
    (("max loss per trade",), "strata",
     "Za duża strata na jeden zakup",
     "Przy tym stopie straciłbym więcej, niż wolno na jeden zakup."),
    (("reward:risk", "reward : risk"), "cel",
     "Cel za blisko ceny",
     "Do zysku było bliżej niż do straty. Nie warto."),
    (("position cap", "position:"), "koncentracja",
     "Za dużo w jednej spółce",
     "Ta spółka zajęłaby za dużo miejsca w portfelu."),
    (("cash buffer", "cash:"), "gotówka",
     "Za mało gotówki",
     "Zostałbym bez zapasu gotówki na koncie."),
    (("window", "before ", "after "), "godziny",
     "Zła godzina",
     "Ta metoda kupuje tylko w wyznaczonych godzinach."),
    (("trades per day", "trades:"), "limit",
     "Limit zakupów na dziś",
     "Kupowałem dziś tyle razy, ile wolno."),
    (("duplicate",), "duplikat",
     "Ta spółka już dziś była",
     "Nie dokupuję do spółki, którą kupiłem dziś."),
    (("blocked",), "zakaz",
     "Spółka zablokowana",
     "Ta spółka jest wyłączona w ustawieniach."),
    (("stop",), "stop",
     "Brak poziomu wyjścia",
     "Nie kupuję bez ustalonego poziomu, na którym sprzedam ze stratą."),
    (("short",), "krótka",
     "Gra tylko na wzrosty",
     "Nie sprzedaję pożyczonych akcji."),
    (("option", "crypto", "asset"), "typ",
     "To nie jest akcja",
     "Ta symulacja kupuje tylko akcje."),
    (("format", "malformed"), "format",
     "Błąd w zleceniu",
     "Zlecenie było źle zbudowane. Odrzucone."),
    (("min order", "under your minimum"), "minimum",
     "Zbyt mały zakup",
     "Wyszłoby mniej niż najmniejszy możliwy zakup."),
]

SIZE_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (("reward:risk", "the move it was waiting for", "the move has already happened",
      "not above the entry"), "cel",
     "Cena już odjechała",
     "Cena poszła wyżej, niż planowałem. Do zysku nie ma już miejsca."),
    (("too far away", "zero shares", "no order"), "strata",
     "Stop za daleko",
     "Nawet jedna akcja ryzykowałaby więcej, niż wolno."),
    (("not fresh", "older than", "stale"), "dane",
     "Cena nieaktualna",
     "Cena była stara. Czekałem na świeżą."),
    (("refus", "refused"), "odmowa",
     "Plan odrzucony",
     "Plan zakupu nie przeszedł kontroli."),
]

EXIT_PL = {
    "target": ("Cel osiągnięty", "Cena doszła do celu. Sprzedane z zyskiem."),
    "stop": ("Stop zadziałał", "Cena spadła do poziomu, który chronił pieniądze. Sprzedane ze stratą."),
    "flat_by": ("Koniec dnia", "Zamknięte przed końcem giełdy. Nic nie zostaje na noc."),
    "eod_flat": ("Domknięte awaryjnie", "Po giełdzie została pozycja. Domknąłem ją po ostatniej cenie."),
}

EXIT_SHORT = {"target": "cel", "stop": "stop", "flat_by": "koniec dnia", "eod_flat": "awaryjnie"}


def classify(text: str, rules) -> tuple[str, str, str]:
    low = str(text or "").lower()
    for keys, code, title, meaning in rules:
        if any(k in low for k in keys):
            return code, title, meaning
    return "inne", "Odrzucone", "Zlecenie nie przeszło kontroli."


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
    ("cena-pod-stopem", "Cena spadła pod stop",
     "Po sygnale cena zjechała poniżej poziomu wyjścia. Kupno oznaczałoby stratę z góry."),
    ("news", "Wiadomości wstrzymały zakup",
     "Nagłówek o wstrząsie: upadłość, dochodzenie, krach. Wtedy nie kupuję."),
    ("cel", "Cel za blisko ceny",
     "Do zysku było bliżej niż do straty."),
    ("plan", "Brak planu wyjścia",
     "Nie kupuję bez ustalonego stopu i celu."),
    ("size", "Nie wyszła żadna liczba akcji",
     "Przy tym stopie każda liczba akcji przekraczała limit straty."),
    ("fill", "Nie zapisało się wykonanie",
     "Zlecenie przeszło kontrole, ale zapis się nie udał."),
    ("dane", "Brak ceny",
     "Nie było ceny, której mogłem zaufać."),
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
    return "Odrzucone"


# Slowniczek: tylko pojecia, ktore naprawde pojawiaja sie w panelu.
# Kazde wyjasnienie to jedno krótkie zdanie.
GLOSSARY = [
    ("Stop", "Cena, przy której sprzedaję ze stratą."),
    ("Cel", "Cena, przy której sprzedaję z zyskiem."),
    ("× ryzyko", "Ile zarabiam na złotówkę ryzyka."),
    ("Przebicie", "Cena nad szczytem pierwszych 15 minut."),
    ("Pozycja", "Akcje, które mam teraz."),
    ("Gotówka", "Pieniądze poza akcjami."),
    ("Poślizg", "Różnica między ceną widzianą a zapłaconą."),
    ("Podatek", "19% od zysku, odkładane z góry."),
    ("S&P 500", "Wzorzec: te same wpłaty w indeks."),
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

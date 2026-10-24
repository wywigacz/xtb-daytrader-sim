# XTB Day Trader — symulator day-tradingu

Autonomiczny symulator handlu akcjami USA w ciągu dnia, oparty na metodyce
[**day-trader-skill**](https://github.com/Jakeschincariol/day-trader-skill),
z kosztami i podatkami jak na polskim rachunku **XTB**.

* Kapitał startowy: **10 000 zł**, potem **+10 000 zł co miesiąc**.
* Horyzont: **300 dni**.
* Handel **tylko w ciągu dnia** — wszystkie pozycje zamknięte przed końcem sesji.
* Uruchamiany automatycznie przez **GitHub Actions**, bez udziału człowieka.
* Wszystkie zlecenia są **symulowane** — nic nie trafia do brokera.

## Panel z wynikami

**https://wywigacz.github.io/xtb-daytrader-sim/**

Panel tłumaczy każdą decyzję: co bot kupił, dlaczego, jak ustawił stop i cel,
ile okazji odrzucił i z jakiego powodu, co przeczytał i czego się nauczył.
Napisany prostym językiem, bez żargonu — wszystkie pojęcia w słowniczku.

Panel jest pusty z wyjaśnieniem do pierwszego dnia handlowego (26.10.2026).
Podgląd, jak wygląda wypełniony, jest w `docs/przyklad-panelu.png`.

## Jak działa bot

1. **Skanuje** ~50 płynnych spółek USA i szuka jednego sygnału: cena przebiła
   maksimum pierwszych 15 minut sesji i **zamknęła się** nad nim.
2. **Czyta nagłówki** o kandydacie. Wzmianka o realnym wstrząsie (wstrzymanie
   handlu, upadłość, dochodzenie, krach) → odpuszcza. Zwykłe wzmianki
   o wynikach nie blokują handlu.
3. **Planuje wyjście przed wejściem**: stop = środek porannego zakresu,
   cel = 1R (tyle samo, ile ryzykuje).
4. **Liczy wielkość pozycji** tak, by maksymalna strata na transakcji to
   1% kapitału.
5. **Kontroluje ryzyko**: limity strat dnia, liczba transakcji, warunki wejścia.
6. **Kupuje** po cenie rynkowej plus poślizg, **zamyka** na stopie, celu albo
   najpóźniej 15:55 czasu Nowego Jorku.

Każda decyzja trafia do `sim/state/decisions.jsonl` razem z powodem — z tego
powstaje panel.

## Pieniądze i koszty

| | |
| --- | --- |
| Kapitał startowy | 10 000 zł |
| Wpłaty miesięczne | 10 000 zł, pierwszy dzień handlowy miesiąca |
| Razem przez 300 dni | ~110 000 zł |
| Przewalutowanie PLN→USD | 0,5% (jak spread XTB) |
| Poślizg rynkowy | 0,05% na transakcję |
| Prowizja za akcje USA | 0% (do limitu obrotu w XTB) |
| Podatek Belki | 19% od zysku, odkładany w rezerwie |

Handel odbywa się na akcjach amerykańskich, więc wpłata jest przewalutowana
raz; dalej środki zostają w dolarach. Wartość portfela jest przeliczana na
złotówki po bieżącym kursie USD/PLN — to realne ryzyko walutowe, nie błąd.

## Czego symulator nie robi

Nie łączy się z żadnym kontem, nie wysyła prawdziwych zleceń, nie handluje
opcjami, kryptowalutami, na dźwigni ani na krótko, nie trzyma pozycji przez
noc, nie obiecuje zysku.

Sekcja „Czego się nauczył” w panelu to **statystyka z własnych transakcji**,
nie uczenie maszynowe. Przy małej liczbie transakcji panel mówi wprost
„za mało danych”, zamiast wymyślać wnioski.

## Uruchomienie lokalne

```bash
python sim/tick.py                               # jeden tick w sesji
python sim/tick.py --now "2026-10-23 10:20"      # tick na zamrożonym zegarze
python sim/daily.py                              # rozliczenie dnia + panel
python sim/dashboard.py                          # sam panel (docs/index.html)
python sim/render.py --html docs/index.html --out docs/panel.png   # zrzut PNG
```

Wymagania: **Python 3.9+** i nic więcej. Do zrzutu PNG: `playwright` + Chrome.

## Struktura repo

```
sim/            silnik symulacji
  session.py      zegar giełdy USA: sesja, święta, DST, flat-by
  market.py       darmowe dane Yahoo (świece 5-min, kurs USD/PLN)
  xtb.py          koszty: przewalutowanie, prowizja, poślizg, podatek
  book.py         papierowy broker: wpłaty, kupno/sprzedaż, wycena, księga
  strategy.py     decyzje: skan → nagłówki → wejście → plan → wielkość → ryzyko
  news.py         ile przeczytano i czy zmieniło decyzję
  insights.py     lejek decyzji + obserwacje z własnych transakcji
  plain.py        tłumaczenie żargonu skilla na prosty polski
  ui.py           klocki graficzne (czysty SVG, bez bibliotek)
  dashboard.py    panel: składanie strony
  render.py       zrzut panelu do PNG
  tick.py         jedno uruchomienie w sesji
  daily.py        rozliczenie po sesji
  config.json     wszystkie ustawienia
  state/          stan: kapitał, transakcje, decyzje, nagłówki

skills/         oryginalny day-trader-skill (MIT, autor: Jake Schincariol)
trader/         pliki roboczego „konta” w USD (format skilla)
docs/           panel (GitHub Pages) + dokumentacja
universe.txt    lista spółek do skanowania
```

## Dokumentacja

* [`docs/JAK-PATRZEC.md`](docs/JAK-PATRZEC.md) — jak czytać panel
* [`docs/JAK-WLACZYC.md`](docs/JAK-WLACZYC.md) — włącz, wyłącz, zmień ustawienia
* [`docs/XTB-ZALOZENIA.md`](docs/XTB-ZALOZENIA.md) — dokładne założenia kosztowe i podatkowe
* [`docs/FAQ.md`](docs/FAQ.md) — najczęstsze pytania

## Podziękowania

Strategia, narzędzia i metodyka pochodzą z projektu
[day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT).
Ten projekt dokłada: papierowy broker, koszty XTB, wpłaty miesięczne, podatek,
warstwę nagłówków, panel z wyjaśnieniami i automatyczne uruchamianie.

Licencja: MIT (patrz `LICENSE`).

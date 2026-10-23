# XTB Day Trader — dziennik symulacji

Automatyczna symulacja day-tradingu na akcjach USA, oparta na metodyce skilla
[**day-trader-skill**](https://github.com/Jakeschincariol/day-trader-skill),
z kosztami i podatkami jak na rachunku **XTB w PLN**.

* Start: **10 000 zł**, potem **+10 000 zł co miesiąc**.
* Horyzont: **300 dni**.
* Handel **tylko w ciągu dnia** — wszystko zamknięte przed końcem sesji.
* Działa **samo** (GitHub Actions), bez Twojego komputera — co 10 minut w oknie
  porannym, co 30 minut w pozostałej części sesji.
* Repo jest **prywatne** — widzisz je tylko Ty.

> **To nie jest prawdziwe konto i nie jest to porada inwestycyjna.**
> Zlecenia są symulowane, a nie wysyłane do XTB. Nikt nie obiecuje zysku —
> większość osób handlujących w ciągu dnia traci pieniądze.

---

## Zobacz wyniki

| Co | Gdzie |
| --- | --- |
| **Jak to wygląda (przykład)** | `docs/przyklad-panelu.png` — przebieg testowy na prawdziwych danych |
| **Panel (obrazek, najprościej)** | `docs/panel.png` — otwórz i powiększ |
| **Panel (wersja pełna)** | `docs/index.html` → **Raw** → pobierz → otwórz w przeglądarce |
| **Instrukcja patrzenia** | [`docs/JAK-PATRZEC.md`](docs/JAK-PATRZEC.md) |

Panel jest obrazkiem, bo **GitHub Pages na darmowym planie zawsze publikuje
stronę publicznie** — a Ty chcesz prywatnie. Obrazek w prywatnym repo jest
widoczny tylko dla Ciebie i nie wymaga żadnego logowania poza GitHubem.

---

## Co panel pokazuje (9 sekcji)

| Sekcja | Odpowiada na pytanie |
| --- | --- |
| **01 Dziś w skrócie** | Co bot zrobił dziś — po kolei, jednym zdaniem każde |
| **02 Kapitał w czasie** | Jak zmieniała się wartość, na tle wpłat i indeksu S&P 500 |
| **03 Pozycje** | Co trzyma teraz (z odległością do stopu i celu) i co zamknął dziś |
| **04 Dlaczego podjął te decyzje** | Powód każdego kupna i sprzedaży + liczby |
| **05 Lejek decyzji** | Jak z 5 943 spółek zostaje kilka transakcji |
| **06 Czego się nauczył** | Wnioski z własnych transakcji, zawsze z podaniem próby |
| **07 Co czytał** | Nagłówki, które widział, i czy któryś wstrzymał zakup |
| **08 Jak to działa** | Pięć kroków, powtarzanych codziennie |
| **09 Słowniczek** | Każde pojęcie jednym zdaniem |

---

## Jak działa bot (w skrócie)

1. **Skanuje** ~50 płynnych spółek USA i szuka jednego sygnału: cena przebiła
   maksimum pierwszych 15 minut sesji i **zamknęła się** nad nim.
2. **Czyta wiadomości** o kandydacie. Nagłówek o realnym wstrząsie
   (wstrzymanie handlu, upadłość, dochodzenie, krach) → odpuszcza.
   Zwykłe wzmianki o wynikach **nie** blokują handlu.
3. **Planuje wyjście** przed wejściem: stop = środek porannego zakresu,
   cel = 1R (tyle samo, ile ryzykuje).
4. **Liczy wielkość** tak, żeby maksymalna strata to 1% kapitału.
5. **Kontroluje ryzyko**: limity strat dnia, liczba transakcji, filtr spółek.
6. **Kupuje** po cenie rynkowej + poślizg 0,05%.
7. **Zamyka** na stopie, celu albo najpóźniej 15:55 czasu Nowego Jorku.

Każda z tych decyzji ląduje w `sim/state/decisions.jsonl` razem z powodem —
z tego powstaje panel.

---

## Pieniądze

| | |
| --- | --- |
| Wpłata startowa | 10 000 zł |
| Wpłaty miesięczne | 10 000 zł, pierwszy dzień handlowy miesiąca |
| Razem przez 300 dni | ~110 000 zł |
| Przewalutowanie PLN→USD | 0,5% (jak spread XTB) |

Handlujemy akcjami amerykańskimi, więc wpłata jest przewalutowana **raz**;
dalej środki zostają w dolarach. Na koniec wartość jest przeliczana z powrotem
na złotówki po bieżącym kursie USD/PLN.

### Koszty i podatek

| Koszt | Wartość | Uwaga |
| --- | --- | --- |
| Prowizja XTB za akcje USA | 0% | do limitu obrotu w miesiącu |
| Spread / poślizg | 0,05% na transakcję | symulacja rynku |
| Przewalutowanie PLN→USD | 0,5% | tylko przy wpłacie |
| Podatek Belki | 19% od zysku | odkładany w rezerwie, widoczny osobno |

Wszystkie liczby są w `sim/config.json`.

---

## Czego bot **nie** robi

Nie łączy się z Twoim kontem XTB, nie wysyła prawdziwych zleceń, nie handluje
opcjami, kryptowalutami, na dźwigni ani na krótko, nie trzyma pozycji przez
noc, nie obiecuje zysku.

„Czego się nauczył” to **statystyka z jego własnych transakcji**, nie uczenie
maszynowe. Przy małej liczbie transakcji panel mówi wprost „za mało danych”,
zamiast wymyślać wnioski.

---

## Uruchomienie ręczne (do testów)

```bash
python sim/tick.py                              # jeden tick w sesji
python sim/tick.py --now "2026-10-23 10:20"     # tick na zamrożonym zegarze
python sim/daily.py                             # rozliczenie + panel
python sim/dashboard.py                         # sam panel
python sim/render.py --html docs/index.html --out docs/panel.png   # zrzut PNG
```

Wymagania: **Python 3.9+** i nic więcej (do zrzutu PNG: `playwright` + Chrome).

---

## Struktura repo

```
sim/            silnik symulacji
  session.py      zegar giełdy USA: sesja, święta, DST, flat-by
  market.py       darmowe dane Yahoo (świece 5-min, kurs USD/PLN)
  xtb.py          koszty: przewalutowanie, prowizja, poślizg, podatek
  book.py         papierowy broker: wpłaty, kupno/sprzedaż, wycena, księga
  strategy.py     decyzje: skan → newsy → wejście → plan → wielkość → ryzyko
  news.py         ile przeczytał i czy to zmieniło decyzję
  insights.py     lejek decyzji + obserwacje z własnych transakcji
  plain.py        tłumaczenie żargonu skilla na prosty polski
  ui.py           klocki graficzne (czysty SVG)
  dashboard.py    panel: składanie strony
  render.py       zrzut panelu do PNG (podgląd w repo)
  tick.py         jedno uruchomienie w sesji
  daily.py        rozliczenie po sesji
  config.json     wszystkie ustawienia
  state/          stan: kapitał, transakcje, decyzje, newsy

skills/         oryginalny day-trader-skill (MIT, autor: Jake Schincariol)
trader/         pliki roboczego „konta” w USD (format skilla)
docs/           panel + dokumentacja
universe.txt    lista spółek do skanowania
```

---

## Dokumentacja

* [`docs/JAK-PATRZEC.md`](docs/JAK-PATRZEC.md) — jak patrzeć na panel
* [`docs/JAK-WLACZYC.md`](docs/JAK-WLACZYC.md) — włącz/wyłącz/zmień/reset
* [`docs/XTB-ZALOZENIA.md`](docs/XTB-ZALOZENIA.md) — dokładne założenia kosztowe i podatkowe
* [`docs/FAQ.md`](docs/FAQ.md) — najczęstsze pytania

## Podziękowania

Strategia, narzędzia i cała metodyka pochodzą z projektu
[day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT).
Ten projekt dokłada: papierowy broker, koszty XTB, wpłaty miesięczne, podatek,
warstwę wiadomości, panel z wyjaśnieniami i automatyczne uruchamianie.

Licencja: MIT (patrz `LICENSE`).
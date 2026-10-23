# XTB Day Trader Sim — symulacja inwestowania 10 000 zł + 10 000 zł/mies.

Automatyczna symulacja day-tradingu na akcjach USA, oparta na metodyce
skilla **[day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)**,
z kosztami i podatkami jak na rachunku **XTB w PLN**.

* Start: **10 000 zł**, potem **+10 000 zł co miesiąc**.
* Horyzont: **300 dni** (od 26.10.2026 do ok. 21.08.2027).
* Handel **tylko w ciągu dnia** — wszystko zamykane przed końcem sesji, zero trzymania na noc.
* Działa **samo na GitHubie** (GitHub Actions), nie potrzebuje Twojego komputera.
* Wynik widać na jednej stronie: **`docs/index.html`** (GitHub Pages).

> **To nie jest prawdziwe konto i nie jest to porada inwestycyjna.**
> Zlecenia są symulowane, a nie wysyłane do XTB. Nikt nie obiecuje zysku —
> większość osób handlujących w ciągu dnia traci pieniądze.

---

## Gdzie patrzeć (2 miejsca)

| Co | Gdzie |
| --- | --- |
| **Wynik, wykres, transakcje, decyzje** | GitHub Pages → `https://TWOJ-LOGIN.github.io/xtb-daytrader-sim/` |
| **Surowe pliki** | `sim/state/` (historia kapitału, transakcje, dziennik decyzji) |

---

## Jak to działa (prosto, 6 kroków)

Każdego dnia w sesji USA (15:30–22:00 czasu polskiego) bot robi to samo:

1. **Skanuje** ~50 płynnych spółek USA i szuka jednego konkretnego sygnału:
   cena przebiła maksimum pierwszych 15 minut sesji i zamknęła się nad nim.
2. **Sprawdza plan wyjścia** — gdzie jest stop-loss (środek porannego zakresu),
   a gdzie cel (1× tyle, ile ryzykujemy). Plan powstaje **przed** wejściem.
3. **Liczy, ile akcji kupić** — tak, żeby maksymalna strata na jednej transakcji
   to 1% kapitału. Nie „na oko”.
4. **Kontrola ryzyka** — limit strat dnia, limit liczby transakcji, filtr spółek.
   Jak coś nie gra, transakcja jest odrzucana.
5. **Kupuje (symulacja)** — po cenie rynkowej + poślizg 0,05%.
6. **Zamyka** na stopie, celu albo najpóźniej 15:55 czasu Nowego Jorku.

Po zamknięciu sesji bot robi wycenę, dopisuje punkt na wykresie, aktualizuje stronę
i zapisuje wszystko w repo. W pierwszym dniu handlowym miesiąca dopisuje 10 000 zł.

---

## Twoje pieniądze w symulacji

| | |
| --- | --- |
| Wpłata startowa | 10 000 zł (26.10.2026) |
| Wpłaty miesięczne | 10 000 zł, pierwszy dzień handlowy miesiąca |
| Razem przez 300 dni | ~110 000 zł |
| Przewalutowanie PLN→USD | 0,5% (tak jak spread XTB) |

**Dlaczego USD?** Bo handlujemy amerykańskimi akcjami. Wpłata w PLN jest
przewalutowana raz; dalej środki zostają w dolarach. Na koniec wartość jest
przeliczana z powrotem na PLN po bieżącym kursie USD/PLN.

---

## Koszty i podatek (uczciwie, nie „za darmo”)

| Koszt | Wartość | Uwaga |
| --- | --- | --- |
| Prowizja XTB za akcje USA | 0% | do limitu obrotu w miesiącu (XTB) |
| Spread / poślizg | 0,05% na transakcję | symulacja rynku |
| Przewalutowanie PLN→USD | 0,5% | tylko przy wpłacie |
| Podatek Belki | 19% od zysku | odkładany w rezerwie, nie „znika” z wyniku |

Wszystkie liczby są w `sim/config.json` i można je zmienić.

---

## Co bot robi, a czego nie robi

**Robi:** skanuje, planuje stop i cel, liczy wielkość pozycji, pilnuje limitów
ryzyka, symuluje wykonanie, prowadzi pełną księgowość i dziennik decyzji.

**Nie robi:** nie łączy się z Twoim kontem XTB, nie wysyła prawdziwych zleceń,
nie handluje opcjami, kryptowalutami, na dźwigni ani na krótko, nie trzyma
pozycji przez noc, nie obiecuje zysku.

---

## Zmiana ustawień

Wszystko w **`sim/config.json`**:

| Pole | Znaczenie |
| --- | --- |
| `start_capital_pln` | wpłata startowa |
| `monthly_deposit_pln` | wpłata miesięczna |
| `days` | długość symulacji |
| `risk_from_equity.max_loss_per_trade_pct` | ile % kapitału można stracić na jednej transakcji |
| `risk_from_equity.max_position_pct` | maks. udział jednej spółki |
| `risk_from_equity.max_trades_per_day` | maks. transakcji dziennie |
| `costs.slippage_bps` | poślizg w punktach bazowych |
| `costs.fx_cost_pct` | koszt przewalutowania |

Lista spółek: **`universe.txt`** (jedna spółka w linii).

---

## Uruchomienie ręczne (do testów)

```bash
# pojedynczy „tick” w sesji
python sim/tick.py

# tick z zamrożonym zegarem (odtwarzanie konkretnego dnia)
python sim/tick.py --now "2026-10-23 10:20"

# rozliczenie dnia + przebudowa dashboardu
python sim/daily.py
```

Wymagania: **Python 3.9+**, nic więcej. Żadnych `pip install` — cała logika
korzysta wyłącznie z biblioteki standardowej.

---

## Struktura repo

```
sim/            silnik symulacji (mój kod)
  session.py      zegar giełdy USA: sesja, święta, DST, flat-by
  market.py       darmowe dane Yahoo (5-minutowe świece, kurs USD/PLN)
  xtb.py          koszty: przewalutowanie, prowizja, poślizg, podatek
  book.py         papierowy broker: wpłaty, kupno/sprzedaż, wycena, dziennik
  strategy.py     decyzje: skan → wejście → stop/cel → wielkość → kontrola ryzyka
  skilltools.py   wywołania narzędzi skilla jako podprocesów
  tick.py         jedno uruchomienie w sesji
  daily.py        rozliczenie po sesji
  dashboard.py    generator strony wynikowej
  config.json     wszystkie ustawienia symulacji
  state/          stan: kapitał, transakcje, decyzje (commitowane codziennie)

skills/         oryginalny day-trader-skill (MIT, autor: Jake Schincariol)
trader/         pliki roboczego „konta” w USD (format skilla)
docs/           GitHub Pages: index.html + dokumentacja
universe.txt    lista spółek do skanowania
```

---

## Dokumentacja

* [`docs/XTB-ZALOZENIA.md`](docs/XTB-ZALOZENIA.md) — dokładne założenia kosztowe i podatkowe
* [`docs/FAQ.md`](docs/FAQ.md) — najczęstsze pytania, proste odpowiedzi
* [`docs/JAK-WLACZYC.md`](docs/JAK-WLACZYC.md) — włączanie/wyłączanie automatu

## Podziękowania

Strategia, narzędzia i cała metodyka pochodzą z projektu
[day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
(MIT). Ten projekt dokłada do niego: papierowy broker, koszty XTB, wpłaty
miesięczne, podatek, automatyczne uruchamianie i dashboard.

Licencja: MIT (patrz `LICENSE`).

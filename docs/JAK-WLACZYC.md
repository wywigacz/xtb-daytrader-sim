# Jak włączyć, sprawdzić i wyłączyć automat

Wszystko klikasz w przeglądarce na GitHubie. Nic nie instalujesz.

---

## 1. Włącz stronę z wynikami (GitHub Pages) — raz, na 30 sekund

1. Wejdź na swoje repo: `https://github.com/wywigacz/xtb-daytrader-sim`
   (strona z wynikami jest już włączona: https://wywigacz.github.io/xtb-daytrader-sim/ )
2. Kliknij **Settings** (koło zębate, prawy górny róg).
3. W lewej kolumnie przewiń do **Pages**.
4. W sekcji **Build and deployment**:
   * **Source**: wybierz `Deploy from a branch`
   * **Branch**: `main`, folder: **`/docs`**
5. Kliknij **Save**.
6. Poczekaj 1–2 minuty, odśwież stronę Pages — pojawi się link:
   `https://wywigacz.github.io/xtb-daytrader-sim/`

To jest Twoja strona z wykresem i transakcjami. Odświeża się sama po każdym
rozliczeniu dnia.

---

## 2. Sprawdź, czy automat działa

1. W repo kliknij zakładkę **Actions** (u góry).
2. Zobaczysz dwa automaty: **tick (sesja USA)** i **daily (rozliczenie po sesji)**.
3. Kliknij któryś → **Run workflow** → zielony przycisk. To uruchomienie na żądanie.
4. Po ~1 minucie wpis zmieni kolor na zielony (sukces) albo czerwony (błąd).
5. Kliknij wpis → kliknij krok **Tick symulacji** / **Rozliczenie dzienne** →
   zobaczysz cały tekst, co bot policzył i dlaczego.

Czerwony wpis nie psuje symulacji — stan jest zapisany, następne uruchomienie
spróbuje ponownie.

---

## 3. Wyłącz automat (wakacje, koniec testu)

1. **Actions** → wybierz **tick (sesja USA)** → przycisk **⋯** po prawej →
   **Disable workflow**.
2. To samo dla **daily (rozliczenie po sesji)**.

Włączasz z powrotem tym samym przyciskiem (**Enable workflow**).
Historia i kapitał zostają nietknięte.

---

## 4. Zmień ustawienia (wpłata, limity, spółki)

1. Otwórz plik `sim/config.json` w repo.
2. Kliknij ołówek (Edit).
3. Zmień liczbę, np. `"monthly_deposit_pln": 10000` → `5000`.
4. Na dole **Commit changes**.

Zmiana działa od następnego uruchomienia. Nic nie trzeba restartować.

Lista spółek: plik `universe.txt` — jedna spółka w linii, wielkimi literami.

---

## 5. Co zrobić, jeśli coś wygląda dziwnie

| Objaw | Co to znaczy | Co zrobić |
| --- | --- | --- |
| Brak nowych transakcji przez kilka dni | Normalne. Sygnał jest wybiórczy. | Nic. |
| Wartość spadła | Strata na transakcji albo kurs USD/PLN. | Zajrzyj w `sim/state/trades.csv`. |
| Wpis w Actions czerwony, „rate limit” | Yahoo ograniczyło darmowe dane. | Poczekaj — następny tick spróbuje sam. |
| Dashboard się nie zmienia | Pages nie są włączone albo brak commita. | Punkt 1 powyżej + sprawdź Actions. |
| „Symulacja zakonczona” | Minęło 300 dni. | Zmień `days` w `sim/config.json`. |

---

## 6. Gdzie szukać szczegółów

* `sim/state/decisions.jsonl` — **każda** decyzja bota z uzasadnieniem
  (dlaczego kupił, dlaczego odpuścił, jaki limit zadziałał).
* `sim/state/trades.csv` — wszystkie zamknięte transakcje.
* `sim/state/ledger.csv` — każdy ruch pieniędzy.
* `sim/state/equity.csv` — wartość portfela dzień po dniu.

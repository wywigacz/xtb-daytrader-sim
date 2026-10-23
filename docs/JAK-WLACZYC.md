# Jak włączyć, wyłączyć i zmienić ustawienia

Wszystko klikasz w przeglądarce lub w aplikacji GitHub. Nic nie instalujesz.
Repo jest **prywatne** — widzisz je tylko Ty.

---

## 1. Sprawdź, czy automat działa

1. Wejdź na `https://github.com/wywigacz/xtb-daytrader-sim` → zakładka **Actions**.
2. Są dwa automaty:
   * **tick (sesja USA)** — uruchamia się co 10 minut w oknie porannym
     (9:45–11:30 czasu Nowego Jorku) i co 30 minut w pozostałej części sesji,
   * **daily (rozliczenie po sesji)** — raz dziennie po zamknięciu.
3. Kliknij któryś → **Run workflow** → zielony przycisk. To uruchomienie na żądanie.
4. Po ~1 minucie wpis zmieni kolor: zielony = sukces, czerwony = błąd.
5. Kliknij wpis → kliknij krok, np. **Tick symulacji** → zobaczysz pełny tekst:
   co bot policzył i dlaczego.

Czerwony wpis niczego nie psuje. Stan jest zapisany w repo, następne
uruchomienie spróbuje ponownie.

---

## 2. Obejrzyj panel

* **Obrazek:** `docs/panel.png` — otwórz i powiększ. To codzienny zrzut panelu.
* **Wersja pełna:** `docs/index.html` → przycisk **Raw** → pobierz → otwórz
  dwuklikiem w przeglądarce.

Szczegóły: [`JAK-PATRZEC.md`](JAK-PATRZEC.md).

---

## 3. Wyłącz automat (wakacje, koniec testu)

1. **Actions** → wybierz **tick (sesja USA)** → menu **⋯** po prawej →
   **Disable workflow**.
2. To samo dla **daily (rozliczenie po sesji)**.

Włączasz z powrotem tym samym przyciskiem (**Enable workflow**).
Historia, kapitał i panel zostają nietknięte.

---

## 4. Zmień ustawienia

1. Otwórz `sim/config.json` w repo → ołówek **Edit**.
2. Zmień liczbę i kliknij **Commit changes** na dole.

| Pole | Znaczenie |
| --- | --- |
| `start_capital_pln` | wpłata startowa |
| `monthly_deposit_pln` | wpłata miesięczna |
| `days` | długość symulacji |
| `max_concurrent_positions` | ile pozycji naraz (domyślnie 3) |
| `risk_from_equity.max_loss_per_trade_pct` | ile % kapitału można stracić na jednej transakcji |
| `risk_from_equity.max_position_pct` | maks. udział jednej spółki |
| `risk_from_equity.max_trades_per_day` | maks. transakcji dziennie |
| `costs.slippage_bps` | poślizg w punktach bazowych |
| `costs.fx_cost_pct` | koszt przewalutowania PLN→USD |

Lista spółek: `universe.txt` — jedna spółka w linii, wielkimi literami.

Zmiany działają od następnego uruchomienia. Nic nie trzeba restartować.

---

## 5. Jak zatrzymać hałas w historii (opcjonalnie)

Historia zmian w repo rośnie z każdym commitem (panel + zrzut PNG).
Jeśli kiedyś zrobi się tego za dużo, mogę przestawić zrzut PNG na
cotygodniowy — powiedz, to zmienię.

---

## 6. Reset symulacji od zera

Usuń z repo (przez interfejs GitHub, plik po pliku):

* `sim/state/` (cały folder),
* `trader/portfolio.json`, `trader/config.json`, `trader/plan.json`,
  `trader/entry.json`, `trader/orders.json`, `trader/prices.json`,
  `trader/state/`,
* `docs/index.html`, `docs/panel.png`.

Przy następnym uruchomieniu wszystko powstanie na nowo, z wpłatą startową.

---

## 7. Co zrobić, jeśli coś wygląda dziwnie

| Objaw | Co to znaczy | Co zrobić |
| --- | --- | --- |
| Kilka dni bez transakcji | Normalne — sygnał jest wybiórczy. | Nic. Panel pokaże, ile okazji odrzucono. |
| Wartość spadła | Strata na transakcji albo kurs USD/PLN. | Sekcja 03 i 04 panelu. |
| Czerwony wpis, „rate limit” | Yahoo ograniczyło darmowe dane. | Poczekaj — następny tick spróbuje sam. |
| Brak nowego `panel.png` | Zrzut się nie udał (nie jest krytyczny). | Zobacz `docs/index.html`; następny dzień spróbuje znowu. |
| „Symulacja zakonczona” | Minęło 300 dni. | Zwiększ `days` w `sim/config.json`. |

---

## 8. Gdzie są szczegóły

| Plik | Zawartość |
| --- | --- |
| `sim/state/decisions.jsonl` | Każda decyzja bota z powodem |
| `sim/state/trades.csv` | Zamknięte transakcje |
| `sim/state/equity.csv` | Wartość portfela dzień po dniu |
| `sim/state/news.json` | Nagłówki przeczytane każdego dnia |
| `sim/state/ledger.csv` | Każdy ruch pieniędzy |
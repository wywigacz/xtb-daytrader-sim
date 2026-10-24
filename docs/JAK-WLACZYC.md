# Włączanie, wyłączanie, zmiana ustawień

Wszystko robi się w przeglądarce na GitHubie. Nic nie trzeba instalować.

---

## Sprawdź, czy automat działa

1. Wejdź na `https://github.com/wywigacz/xtb-daytrader-sim` → zakładka **Actions**.
2. Są dwa automaty:
   * **tick (sesja USA)** — co 10 minut w oknie porannym (9:45–11:30 czasu
     Nowego Jorku) i co 30 minut w pozostałej części sesji;
   * **daily (rozliczenie po sesji)** — raz dziennie po zamknięciu.
3. Kliknij wybrany → **Run workflow** → zielony przycisk. To uruchomienie
   na żądanie.
4. Po chwili wpis zmieni kolor: zielony = sukces, czerwony = błąd.
5. Kliknij wpis → kliknij krok, np. **Tick symulacji** → widać pełny tekst:
   co bot policzył i dlaczego.

Czerwony wpis niczego nie psuje. Stan jest zapisany w repo, następne
uruchomienie próbuje ponownie.

---

## Panel z wynikami

* **Strona:** `https://wywigacz.github.io/xtb-daytrader-sim/`
* **Obrazek (jeden plik do wysłania):** `python sim/render.py` tworzy
  `docs/panel.png`

Szczegóły czytania: [`JAK-PATRZEC.md`](JAK-PATRZEC.md).

---

## Wyłącz automat

1. **Actions** → wybierz **tick (sesja USA)** → menu **⋯** po prawej →
   **Disable workflow**.
2. To samo dla **daily (rozliczenie po sesji)**.

Włączasz z powrotem tym samym przyciskiem (**Enable workflow**).
Historia, kapitał i panel zostają nietknięte.

---

## Zmień ustawienia

Otwórz `sim/config.json` w repo → ołówek **Edit** → zmień liczbę →
**Commit changes**.

| Pole | Znaczenie |
| --- | --- |
| `start_capital_pln` | kapitał startowy |
| `monthly_deposit_pln` | wpłata miesięczna |
| `days` | długość symulacji |
| `max_concurrent_positions` | ile pozycji naraz (domyślnie 3) |
| `risk_from_equity.max_loss_per_trade_pct` | ile % kapitału można stracić na jednej transakcji |
| `risk_from_equity.max_position_pct` | maks. udział jednej spółki |
| `risk_from_equity.max_trades_per_day` | maks. transakcji dziennie |
| `costs.slippage_bps` | poślizg w punktach bazowych |
| `costs.fx_cost_pct` | koszt przewalutowania PLN→USD |

Lista spółek: `universe.txt` — jedna spółka w linii, wielkimi literami.
Zmiany działają od następnego uruchomienia.

---

## Reset symulacji od zera

Usuń z repo: `sim/state/` (cały folder), pliki `trader/*.json`,
`trader/state/` oraz `docs/index.html`. Przy następnym uruchomieniu wszystko
powstanie na nowo, z wpłatą startową.

---

## Gdy coś wygląda dziwnie

| Objaw | Co to znaczy | Co zrobić |
| --- | --- | --- |
| Kilka dni bez transakcji | Normalne — sygnał jest wybiórczy. | Panel pokazuje, ile okazji odrzucono i dlaczego. |
| Wartość spadła | Strata na transakcji albo kurs USD/PLN. | Sekcje 03 i 04 panelu. |
| Czerwony wpis, „rate limit” | Yahoo ograniczyło darmowe dane. | Poczekaj — następny tick próbuje sam. |
| „Symulacja zakończona” | Minęło 300 dni. | Zwiększ `days` w `sim/config.json`. |

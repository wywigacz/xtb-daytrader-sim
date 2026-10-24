# Jak czytać panel

Panel: **https://wywigacz.github.io/xtb-daytrader-sim/**

Jest to jedna strona, która tłumaczy co się stało i dlaczego. Odświeża się
automatycznie po każdym rozliczeniu dnia. Nie wymaga logowania ani instalowania
niczego.

Podgląd wypełnionego panelu (z przebiegu testowego) jest w
`docs/przyklad-panelu.png`.

---

## Co jest w panelu (od góry)

Pasek na samej górze pozwala przeskoczyć do wybranej sekcji.

| Sekcja | Odpowiada na pytanie |
| --- | --- |
| Cztery liczby na starcie | Ile jest warte, ile zarobiło, ile wpłacono, jak wypada S&P 500 |
| **01 Dziś w skrócie** | Co bot zrobił dziś — po kolei, jednym zdaniem każde |
| **02 Kapitał w czasie** | Jak zmieniała się wartość, na tle wpłat i indeksu |
| **03 Pozycje** | Co trzyma teraz (z odległością do stopu i celu) i co zamknął dziś |
| **04 Dlaczego podjął te decyzje** | Powód każdego kupna i sprzedaży + liczby |
| **05 Lejek decyzji** | Jak z ~6 000 spółek zostaje kilka transakcji |
| **06 Czego się nauczył** | Wnioski z własnych transakcji, zawsze z podaniem próby |
| **07 Co czytał** | Nagłówki, które widział, i czy któryś wstrzymał zakup |
| **08 Jak to działa** | Pięć kroków, powtarzanych codziennie |
| **09 Słowniczek** | Każde pojęcie jednym zdaniem |

---

## Jak czytać liczby

* **Wartość portfela** — ile jest warte teraz, po przeliczeniu na złotówki.
* **Zysk / strata** — różnica od sumy wpłat, nie od „wczoraj”. Wpłaty
  podnoszą wartość, więc sam wzrost jeszcze nic nie znaczy.
* **S&P 500 zamiast tego** — co by było, gdyby te same wpłaty wrzucić
  w indeks. To uczciwy punkt odniesienia.
* **R** — jednostka ryzyka. `+2R` znaczy „zarobiłem dwa razy tyle, ile byłem
  gotów stracić na tej transakcji”.
* **Pozycje zamknięte przed końcem dnia** — to nie błąd, to zasada: nic nie
  zostaje na noc.

---

## Gdzie są surowe dane

| Plik | Co zawiera |
| --- | --- |
| `sim/state/decisions.jsonl` | Każda decyzja bota z powodem |
| `sim/state/trades.csv` | Wszystkie zamknięte transakcje |
| `sim/state/equity.csv` | Wartość portfela dzień po dniu |
| `sim/state/news.json` | Nagłówki przeczytane każdego dnia |
| `sim/state/ledger.csv` | Każdy ruch pieniędzy |

---

## Czego w panelu nie ma i dlaczego

* **Nie ma prognoz.** Panel pokazuje, co się stało, a nie co będzie.
* **Nie ma „sygnałów” do skopiowania.** To dziennik symulacji, nie doradztwo.
* **Nie ma danych osobowych** ani dostępu do żadnego konta.

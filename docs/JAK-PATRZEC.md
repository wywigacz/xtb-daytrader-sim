# Jak patrzeć na panel (repo prywatne)

Repo jest **prywatne**. To znaczy, że tylko Ty widzisz kod, wyniki i panel.
Nie ma publicznego adresu w internecie — i celowo, bo GitHub Pages na darmowym
planie zawsze publikuje stronę publicznie.

Dlatego panel jest **obrazkiem w repo**: po każdym dniu bot zapisuje
`docs/panel.png`. GitHub wyświetla obrazy bezpośrednio — nie trzeba nic
pobierać ani nic instalować.

---

## Najprościej: telefon (aplikacja GitHub)

1. Otwórz aplikację **GitHub**.
2. Wejdź w swoje repo `xtb-daytrader-sim`.
3. Otwórz folder **docs**.
4. Dotknij **panel.png**.

Obraz otworzy się na cały ekran. Możesz powiększyć dwoma palcami — jest
zrobiony w wysokiej rozdzielczości, więc liczby pozostają ostre.

## Na komputerze

1. Wejdź na `https://github.com/wywigacz/xtb-daytrader-sim`
2. Kliknij `docs` → `panel.png`.
3. Kliknij obraz, żeby powiększyć.

### Chcesz najpierw zobaczyć, jak to wygląda?

Otwórz **`docs/przyklad-panelu.png`** — to przebieg **testowy** na prawdziwych
danych z 22–23.10.2026, zrobiony tylko po to, żebyś zobaczył układ i sposób
wyjaśniania. To **nie są Twoje wyniki**. Twoje pojawią się w `docs/panel.png`
po pierwszym dniu handlowym.

---

## Co jest w panelu (od góry)

| Sekcja | Odpowiada na pytanie |
| --- | --- |
| Nagłówek + 4 liczby | Ile mam, ile zarobiłem, ile wpłaciłem, jak wypada S&P 500 |
| **01 Dzis w skrócie** | Co bot zrobił dziś, po kolei, jednym zdaniem każde |
| **02 Kapitał w czasie** | Jak zmieniała się wartość — na tle wpłat i indeksu |
| **03 Pozycje** | Co trzyma teraz (z odległością do stopu i celu) i co zamknął dziś |
| **04 Dlaczego podjął te decyzje** | Powód każdego kupna i sprzedaży + liczby |
| **05 Lejek decyzji** | Z 5 943 spółek — ile przeszło filtry |
| **06 Czego się nauczył** | Wnioski z własnych transakcji, z podaniem próby |
| **07 Co czytał** | Nagłówki, które widział, i czy któryś wstrzymał zakup |
| **08 Jak to działa** | Pięć kroków, powtarzanych codziennie |
| **09 Słowniczek** | Każde pojęcie jednym zdaniem |

---

## Wersja interaktywna (pełna)

Plik `docs/index.html` to ten sam panel w wersji „na żywo”. Żeby go otworzyć:

1. Otwórz `docs/index.html` w repo.
2. Kliknij przycisk **Raw** (prawy górny róg pliku) — pobierze się plik.
3. Otwórz pobrany plik w przeglądarce (dwuklik).

Nic nie trzeba instalować. Panel nie łączy się z internetem.

---

## Gdzie są surowe dane

| Plik | Co zawiera |
| --- | --- |
| `sim/state/decisions.jsonl` | Każda decyzja z powodem (pełny dziennik) |
| `sim/state/trades.csv` | Wszystkie zamknięte transakcje |
| `sim/state/equity.csv` | Wartość portfela dzień po dniu |
| `sim/state/news.json` | Nagłówki przeczytane każdego dnia |
| `sim/state/ledger.csv` | Każdy ruch pieniędzy |

---

## Czego nie da się zrobić na darmowym GitHubie

Prywatny adres WWW z panelem (np. `panel.twojadomena.pl`) wymaga albo płatnego
planu GitHub Enterprise, albo zewnętrznego hostingu z logowaniem
(np. Cloudflare Access — darmowy, ale wymaga osobnego konta).

Jeśli będziesz chciał taki prywatny link, da się to dopiąć — powiedz, to
dodam publikację na Cloudflare obok obrazka w repo.

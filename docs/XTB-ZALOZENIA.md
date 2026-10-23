# Założenia: XTB, koszty, podatek, dane

Ten plik mówi dokładnie, **jakie liczby przyjąłem** i dlaczego. Jeśli któraś
liczbowka jest inna u Ciebie w XTB, zmień ją w `sim/config.json`.

---

## 1. Rachunek

* Rachunek w **PLN** (tak jak typowy polski rachunek XTB).
* Handel **akcjami realnymi USA** (nie CFD). XTB oferuje akcje spółek
  amerykańskich; prowizja 0% do miesięcznego limitu obrotu, powyżej limitu
  prowizja procentowa.
* **Bez dźwigni.** Bez CFD, bez opcji, bez krótkiej sprzedaży.
  Symulacja nie pożycza pieniędzy.
* **Akcje całkowite**, bez ułamków — tak jak przy zleceniach typu bracket.

## 2. Koszty, które symulacja naprawdę odejmuje

| Koszt | Wartość domyślna | Kiedy | Pole w config |
| --- | --- | --- | --- |
| Przewalutowanie PLN→USD | 0,50% | przy każdej wpłacie | `costs.fx_cost_pct` |
| Prowizja za akcje USA | 0,00% | przy kupnie i sprzedaży | `costs.commission_pct` |
| Poślizg rynkowy | 5 pb = 0,05% | kupno drożej, sprzedaż taniej | `costs.slippage_bps` |
| Podatek Belki | 19% od zysku | odkładany po każdej zamkniętej transakcji | `costs.tax_on_gains_pct` |

**Przewalutowanie liczę raz, przy wpłacie.** To celowe: realny trader
z rachunkiem PLN nie wymienia pieniędzy tam i z powrotem co tydzień — trzyma
USD na koncie i handluje. Gdybyś wypłacał zysk co miesiąc, dołóż drugie 0,5%.

**Poślizg** to nie spread w rozumieniu CFD. Przy akcjach realnych płacisz
różnicę między ceną, którą widzisz, a ceną realizacji. 5 pb to ostrożne,
uczciwe założenie dla płynnych large-capów.

## 3. Podatek

* 19% od **zrealizowanego** zysku (nie od niezrealizowanego).
* Kwota podatku jest odejmowana od wyniku i pokazywana osobno jako
  „podatek w rezerwie”. Nie znika po cichu ze statystyk.
* Strata z jednej transakcji **nie** obniża podatku od zysku w tej symulacji
  (uproszczenie — w Polsce rozlicza się to narastająco w roku).
* Nie modeluję podatku od dywidend (spółki w symulacji dywidend nie wypłacają
  w horyzoncie jednego dnia).

## 4. Kurs USD/PLN

* Pobierany z Yahoo (`PLN=X`) przy każdym uruchomieniu.
* Wartość portfela w PLN = wartość w USD × bieżący kurs.
* Kurs historyczny nie jest „zamrażany” — wykres w PLN zmienia się też od
  samego kursu walutowego. To jest realne ryzyko walutowe, nie błąd.

## 5. Dane cenowe

* Darmowe, nieoficjalne API Yahoo Finance (`query2`, zapasowo `query1`).
* Świece **5-minutowe**; decyzje podejmowane po **zamknięciu** świecy.
* Dane mogą być opóźnione o kilkadziesiąt sekund do kilku minut.
* GitHub Actions uruchamia się „co około 15 minut” — może się spóźnić.
  Dlatego zarządzanie pozycją przechodzi **świeca po świecy** od momentu
  wejścia, a nie „patrzy tylko na teraz”. Jeśli bot obudzi się 40 minut po
  czasie, i tak wychwyci stop, który został trafiony w międzyczasie.
* Poślizg z tego wynikający jest wliczony: wejście po cenie rynkowej
  z góry założonym pogorszeniem, wyjście po stopie lub gorzej (luka).

## 6. Zasady wejścia i wyjścia (z day-trader-skill)

* **Wejście:** pierwsza świeca 5 min, która **zamknęła się** powyżej maksimum
  pierwszych 15 minut sesji (opening range). Drgnięcie ceny w środku świecy
  się nie liczy — liczy się zamknięcie.
* **Stop:** środek porannego zakresu (opening-range midpoint).
* **Cel:** 1R, czyli tyle samo, ile wynosi ryzyko na akcję.
* **Wielkość pozycji:** najmniejsza z czterech granic — limit straty na
  transakcję, limit udziału jednej spółki, limit wartości zlecenia, dostępna
  gotówka z buforem.
* **Zamknięcie:** stop, cel albo 15:55 czasu Nowego Jorku — zawsze przed
  zamknięciem sesji.
* **Okno wejść:** 9:45–15:30 ET (na skróconym dniu proporcjonalnie wcześniej).

## 7. Limity ryzyka (domyślne)

| Limit | Wartość | Znaczenie |
| --- | --- | --- |
| Max strata na transakcję | 1% kapitału | przy stopie; to decyduje o liczbie akcji |
| Max strata dnia | 3% kapitału | po wyczerpaniu — koniec handlu na dziś |
| Max transakcji dnia | 3 | |
| Max pozycji jednocześnie | 3 | |
| Max udział jednej spółki | 30% | |
| Bufor gotówki | 20% | nigdy nie inwestowany |

Limity przeliczają się **codziennie od aktualnego kapitału** — gdy kapitał
rośnie, pozycje rosną proporcjonalnie; gdy spada, maleją.

## 8. Czego symulacja NIE uwzględnia

* Opłat za prowadzenie rachunku (XTB ich nie pobiera).
* Podatku od dywidend i withholding tax USA.
* Sesji przed- i po-giełdowej (handlujemy tylko 9:30–16:00 ET).
* Zawieszenia handlu na spółce (halt) — jeśli wystąpi, świece będą brakować
  i pozycja zostanie zamknięta przy najbliższej dostępnej cenie.
* Rzeczywistego poślizgu w panice — zakładam 5 pb; w panic sell bywa gorzej.

## 9. Skąd „300 dni”

300 dni kalendarzowych od startu, handel tylko w dni sesyjne. To około
210 sesji i **10 wpłat miesięcznych** po 10 000 zł.

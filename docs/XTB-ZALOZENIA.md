# Założenia: XTB, koszty, podatek, dane

Ten plik mówi dokładnie, **jakie liczby przyjął symulator** i dlaczego.
Wszystkie są do zmiany w `sim/config.json` — jeśli realne stawki są inne,
wystarczy podmienić wartość.

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
| Podatek od zysku | 19% | raz w roku, od wyniku za cały rok | `costs.tax_on_gains_pct` |

**Przewalutowanie liczę raz, przy wpłacie.** To celowe: realny trader
z rachunkiem PLN nie wymienia pieniędzy tam i z powrotem co tydzień — trzyma
USD na koncie i handluje. Gdybyś wypłacał zysk co miesiąc, dołóż drugie 0,5%.

### Dlaczego koszt wychodzi „równo" 50 zł od 10 000 zł

Bo to **procent, nie wynik rynku**: 0,5% z 10 000 zł = 50 zł — zawsze, przy
każdym kursie. Po wymianie mam 2 534,32 USD, a gdy przeliczę to z powrotem po
tym samym kursie, wychodzi 9 950 zł. Kurs się skraca (10 000 × 0,995 = 9 950),
więc kwota wygląda podejrzanie równo. W realnym XTB koszt siedzi w gorszym
kursie, jaki dostajesz, ale efekt jest ten sam: 0,5%.

### Czy jest sens wymieniać z góry, a nie dopiero przy zakupie?

**Koszt jest identyczny** — 0,5% od wymienianej kwoty, niezależnie od tego,
kiedy wymieniasz. Jeśli wymieniasz przy każdym zakupie, po pewnym czasie
i tak przewalisz większość konta (pozycje to do 30% kapitału, do trzech naraz).
Nie ma więc powodu czekać.

Jest jednak **jedna realna różnica**: trzymając dolary, ponosisz **ryzyko
kursowe** także na tej części, która leży bezczynnie (bufor gotówki 20%).
Złotówka lekko się umacnia (założenie: ok. 1% rocznie), więc w przeliczeniu na
złotówki ta część z czasem traci nieco na wartości. Wymiana „na bieżąco”
zostawiłaby tę rezerwę w złotówkach i bez tego ryzyka.

Przy 300 dniach różnica jest mała (ułamek procenta), ale jest. Jeśli chcesz,
da się to zmienić na wersję „wymieniam tylko tyle, ile kupuję” — powiedz.

**Poślizg** to nie spread w rozumieniu CFD. Przy akcjach realnych płacisz
różnicę między ceną, którą widzisz, a ceną realizacji. 5 pb to ostrożne,
uczciwe założenie dla płynnych large-capów.

## 2a. Badanie spółki przed każdym kupnem

Zanim cokolwiek kupię, czytam **raporty spółki ze SEC** (narzędzie
`trader-analyst` z dołączonego skilla): przychody, marże, zysk netto,
zysk na akcję i wzrost rok do roku. To prawdziwe dane z ostatnich raportów
kwartalnych, nie prognoza.

Reguła jest jawna i prosta:

* **nie kupuję** spółki, która w ostatnim kwartale **straciła pieniądze**,
* **nie kupuję** takiej, której **przychody spadły o więcej niż 15%** rok do roku.

Progi zmieniasz w `sim/config.json` (klucz `research`). Badanie wyłącza się
ustawieniem `"enabled": false`.

Co sprawdziłem, zapisuję przy decyzji — panel pokazuje te liczby w karcie
kupna, więc widać nie tylko *co*, ale i *na jakiej podstawie*.

**Kontakt do SEC:** SEC wymaga nagłówka z nazwą i adresem e-mail. W kodzie jest
neutralny zapas. Chcesz swój? Dodaj sekret `SEC_USER_AGENT` w repozytorium
GitHub (Settings → Secrets and variables → Actions) — nie trafi do publicznego
repozytorium. Uwaga: SEC odrzuca domenę `users.noreply.github.com`.

Jeżeli SEC nie odpowiada, badanie jest pomijane, a symulacja działa dalej —
nie udajemy, że coś sprawdziliśmy.

## 2b. Dlaczego pozycje są małe i co robi reszta pieniędzy

Wielkością pozycji rządzą dwie liczby:

* **ryzyko na transakcję: 1% kapitału** (~25 USD przy wpłacie 10 000 zł),
* **maksymalny udział jednej spółki: 30% kapitału** (~760 USD).

Stop w tej metodzie leży blisko ceny wejścia — to środek zakresu pierwszych
15 minut, zwykle 0,5–1% pod ceną. Żeby zaryzykować **1% kapitału** przy stopie
**0,5% pod ceną**, pozycja musiałaby być warta **2× całe konto**. Bez dźwigni
to niemożliwe, więc zawsze wygrywa limit 30% i pozycja wychodzi mała.

Przykład z 26.10.2026 (JPM): stop wypadł tylko **0,09% pod ceną wejścia**.
„1% ryzyka" wymagałoby wtedy 84 akcji (~28 000 USD) przy koncie 2 534 USD.
Limit 30% kupił **2 akcje**. Faktyczne ryzyko: **0,02% konta**.

Mówię to wprost: **przy koncie tej wielkości metoda nie jest w stanie
zaryzykować 1%.** Jej transakcje to ruchy rzędu 0,1% konta, więc wynik dnia
jest mały z arytmetyki, nie z awarii.

Reszta pieniędzy leży w gotówce, bo tak działa ta metoda — czeka na sygnał,
a regulaminowo trzyma jeszcze **20% bufora**. Gotówka **nie procentuje**;
leży w dolarach, więc zmienia się tylko jej wartość w złotówkach po kursie.

## 3. Podatek — tak, jak na polskim rachunku maklerskim

Podatku **nie płaci się od każdej transakcji**. Zasady są takie jak w PIT-38:

* **19% od zysku za cały rok**, nie od pojedynczej transakcji.
* Strata z danego roku **obniża** zysk w latach następnych.
* Odliczać można przez **5 lat**, w jednym roku **najwyżej połowę** straty.
* Podatek płaci się **do 30 kwietnia** roku następnego. Do tego dnia pieniądze
  na podatek zostają na koncie i pracują.
* Deklarację składasz sam — broker wystawia tylko PIT-8C.

Dlatego w panelu są **dwie różne liczby**:

* **ile masz na koncie** — pełna wartość, razem z pieniędzmi na podatek,
* **ile zostanie po podatku** — po odjęciu podatku, który już się naliczył.

Przeliczanie na złotówki: wynik liczę po kursie z dnia transakcji. W realnym
rozliczeniu bierze się kurs NBP z dnia poprzedzającego — przy transakcjach
jednodniowych różnica jest znikoma.

Podatku od dywidend nie ma, bo nic nie trzymam przez noc.

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
* **Cel:** tyle samo, ile wynosi ryzyko na akcję (1 do 1).
* **Wielkość pozycji:** najmniejsza z czterech granic — limit straty na
  transakcję, limit udziału jednej spółki, limit wartości zlecenia, dostępna
  gotówka z buforem.
* **Zamknięcie:** stop, cel albo 15:55 czasu Nowego Jorku — zawsze przed
  zamknięciem sesji.
* **Okno wejść:** 9:45–15:30 ET (na skróconym dniu proporcjonalnie wcześniej).

## 6a. Warstwa wiadomości (żeby bot nie kupował w środku wstrząsu)

Przed każdym zakupem bot czyta nagłówki Yahoo Finance dla kandydata (ostatnie
24 h). Są trzy możliwe skutki:

| Sytuacja | Co robi |
| --- | --- |
| Nagłówek o **realnym wstrząsie** (wstrzymanie handlu, upadłość, dochodzenie SEC, fraud, krach, gwałtowny zjazd, rezygnacja zarządu) | **odpuszcza zakup** i zapisuje to w panelu jako decyzję |
| Zwykła wzmianka o **wynikach** („raportuje w tym tygodniu”, „analityk podniósł cenę”) | **nie blokuje** — inaczej w sezonie wyników nie byłoby ani jednej transakcji (sprawdzone: dało 0 transakcji) |
| Brak nagłówków / feed nie odpowiada | nie blokuje; informacja zapisana jako „brak wpływu” |

Liczba przeczytanych nagłówków i każdy z nich ląduje w panelu (sekcja
*Co czytał*) oraz w `sim/state/news.json`. **Nie streszczam artykułów, których
nie mogę przeczytać** — pokazuję tytuł, źródło i godzinę.

## 6b. Kontrola sensu ceny przed wejściem

Między sygnałem (zamknięcie świecy) a wykonaniem mija kilkadziesiąt sekund,
czasem minut. Jeśli w tym czasie:

* cena spadła **poniżej poziomu stopu** — setup się zepsuł, bot **nie wchodzi**
  (wcześniej bez tej kontroli powstawały absurdy: wyjście na stopie z zyskiem,
  bo stop był wyżej niż cena wejścia),
* cena poszła **powyżej celu** — ruch już się wydarzył, do celu nie ma miejsca,
  bot **nie wchodzi** (R byłby bliski zeru).

Ryzyko na akcję liczone jest od **faktycznej** ceny wejścia do stopu, nie od
ceny z planu. Dzięki temu „× ryzyko” w panelu pokazuje prawdę.

**Dwie ceny, celowo różne.** Do pomiaru ryzyka i do wyceny portfela używana
jest cena z **ostatniej zamkniętej** świecy 5-minutowej — to fakt, a nie
drgnięcie w trakcie formowania świecy. Do symulowanego wykonania zlecenia
używana jest cena **bieżąca** (ostatni tick z Yahoo), bo taką cenę widzi
trader klikający „kup” i po takiej realizuje się zlecenie rynkowe. Różnica
między nimi bywa kilkuminutowa i jest wliczona w wynik — nie zakładam, że
kupuję po cenie, którą widziałem kilka minut wcześniej.

Przy odtwarzaniu przeszłego dnia (tryb testowy z zamrożonym zegarem) obie
ceny to ostatnia zamknięta świeca **do odtwarzanej godziny**, a nie cena
zamknięcia dnia. Bez tego testy pokazywałyby przyszłość: wychodziły
„odrzucone, bo cena zjechała pod stop”, choć o odtwarzanej godzinie cena była
jeszcze w porządku.

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

# FAQ — najczęstsze pytania

### Czy to handluje prawdziwymi pieniędzmi?
Nie. Symulacja. Żadne zlecenie nie idzie do XTB ani nigdzie indziej.

### Czy mogę podłączyć prawdziwe konto XTB?
Technicznie XTB udostępnia API (`xStation5 API`), ale to wymaga umowy,
kluczy i zgód. Ten projekt **celowo** tego nie robi — najpierw chcesz
zobaczyć, jak metoda zachowuje się na sucho.

### Ile to zarobi?
Nie wiem i nikt nie wie. Symulacja pokaże **jak**, nie **ile**.
Uczciwe oczekiwanie: day-trading na małym koncie po kosztach i podatku
często kończy się lekko pod kreską. Jeśli wynik jest dodatni — świetnie,
ale 300 dni to za mało, żeby uznać to za przewagę statystyczną.

### Dlaczego transakcji jest tak mało?
Bo metoda jest wybiórcza: max 3 dziennie, jedna pozycja na spółkę i tylko
wtedy, gdy sygnał jest świeży. Bot **nie goni** ceny, która już odjechała —
wolumenowo wyjdzie 1–2 transakcje dziennie, czasem zero.

### Co jeśli GitHub Actions się nie uruchomi?
Stan jest zapisany w repo — nic nie przepada. Następne uruchomienie
dociągnie zaległe świece i domknie pozycję. GitHub czasem spóźnia cron
o kilka–kilkanaście minut; dlatego okno wejść kończy się o 15:30 ET,
zapasem przed zamknięciem.

### Czy bot trzyma pozycje przez noc?
Nie. Wszystko jest zamykane najpóźniej 15:55 ET. Jeśli bot nie zdąży,
rozliczenie dzienne domyka resztki po ostatniej cenie.

### Skąd się bierze zmiana wartości, skoro nie ma transakcji?
Z kursu USD/PLN i z wyceny otwartych pozycji. Portfel jest w dolarach,
a pokazuję go w złotówkach.

### Czy mogę zmienić listę spółek?
Tak — `universe.txt`, jedna spółka w linii. Uwaga: muszą to być spółki
dostępne w XTB jako akcje realne i płynne (duży obrót, wąski spread).

### Jak zmienić wpłatę miesięczną?
`sim/config.json` → `monthly_deposit_pln`.

### Gdzie dokładnie jest panel? Dlaczego nie ma adresu www?
Nie ma adresu www i to nie jest błąd. GitHub Pages na darmowym planie zawsze
publikuje stronę **publicznie** — każdy mógłby ją otworzyć. Ponieważ repo ma
być prywatne, panel jest **obrazkiem w repo** (`docs/panel.png`), widocznym
tylko dla Ciebie. Jeśli kiedyś zechcesz normalny prywatny adres, da się to
zrobić na Cloudflare Access — daj znać.

### Dlaczego czasem bot nic nie robi przez kilka dni?
Bo szuka jednego, rzadkiego sygnału i sam się hamuje. Panel w sekcji
*Lejek decyzji* pokazuje, ile okazji odrzucił i z jakiego powodu.
Zero transakcji to też decyzja — i bywa tą właściwszą.

### Skąd bot wie, że coś się dzieje w spółce?
Czyta nagłówki z Yahoo Finance (darmowe) dla kandydatów do kupna. Sekcja
*Co czytał* pokazuje, co widział i czy któryś nagłówek wstrzymał zakup.
Blokuje tylko przy realnym wstrząsie (wstrzymanie handlu, upadłość,
dochodzenie, krach) — nie przy zwykłej wzmiance o wynikach.

### Jak zatrzymać symulację?
GitHub → zakładka **Actions** → wybierz workflow → **Disable**.
Albo usuń pliki `.github/workflows/tick.yml` i `daily.yml`.

### Jak zresetować symulację od zera?
Usuń `sim/state/`, `trader/portfolio.json`, `trader/config.json`,
`trader/plan.json`, `trader/entry.json`, `trader/orders.json`,
`trader/prices.json`, `trader/state/` i `docs/index.html`.
Przy następnym uruchomieniu wszystko powstanie na nowo, z wpłatą startową.

### Dlaczego R multiple czasem nie zgadza się z „1R”?
Bo wchodzimy po cenie rynkowej, a plan liczył ryzyko od ceny sygnału.
R liczę od **faktycznej** ceny wejścia do stopu, więc wychodzi inaczej
niż „1” z planu. To poprawne.

### Czy to jest bezpieczne dla moich danych?
W repo nie ma żadnych kluczy ani haseł. Symulacja nie łączy się z Twoim
kontem. Cały „sekret” to nic — nie ma czego ukrywać.

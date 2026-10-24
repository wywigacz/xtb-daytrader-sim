# FAQ — najczęstsze pytania

### Czy to handluje prawdziwymi pieniędzmi?
Nie. To symulator. Żadne zlecenie nie trafia do brokera.

### Czy da się podłączyć prawdziwe konto XTB?
Technicznie XTB udostępnia API, ale wymaga to umowy, kluczy i zgód. Ten
projekt celowo tego nie robi — najpierw testuje samą metodę.

### Ile to zarobi?
Nie wiadomo i nikt tego nie obiecuję. Symulacja pokazuje **jak** podejmowane
są decyzje, a nie **ile** da się zarobić. Uczciwe oczekiwanie: day-trading na
małym koncie, po kosztach i podatku, często kończy się lekko pod kreską.
300 dni to i tak za mało, żeby mówić o jakiejkolwiek przewadze statystycznej.

### Dlaczego transakcji jest tak mało?
Bo metoda jest wybiórcza: maksymalnie 3 transakcje dziennie, jedna pozycja
na spółkę i tylko przy świeżym sygnale. Symulator nie goni ceny, która już
odjechała. W sekcji *Lejek decyzji* widać dokładnie, ile okazji odrzucono
i z jakiego powodu.

### Co się dzieje, jeśli GitHub Actions się nie uruchomi?
Stan jest zapisany w repo — nic nie przepada. Następne uruchomienie dociągnie
zaległe świece i domknie pozycję. Cron GitHuba bywa spóźniony o kilka minut,
dlatego okno wejść kończy się o 15:30 czasu Nowego Jorku — z zapasem.

### Czy pozycje są trzymane przez noc?
Nie. Wszystko zamykane jest najpóźniej o 15:55 czasu Nowego Jorku. Jeśli bot
nie zdąży, rozliczenie dzienne domyka resztki po ostatniej cenie.

### Skąd bierze się zmiana wartości, skoro nie ma transakcji?
Z kursu USD/PLN i z wyceny otwartych pozycji. Portfel jest w dolarach,
a panel pokazuje złotówki — wahania kursu są częścią wyniku.

### Skąd bot wie, że coś się dzieje w spółce?
Czyta nagłówki Yahoo Finance dla kandydatów do kupna. Sekcja *Co czytał*
pokazuje, co widział i czy któryś nagłówek wstrzymał zakup. Blokuje tylko
przy realnym wstrząsie (wstrzymanie handlu, upadłość, dochodzenie, krach) —
nie przy zwykłej wzmiance o wynikach.

### Jak zmienić wpłatę miesięczną albo listę spółek?
`sim/config.json` oraz `universe.txt`. Szczegóły w
[`JAK-WLACZYC.md`](JAK-WLACZYC.md).

### Jak zatrzymać symulację?
GitHub → zakładka **Actions** → wybrany workflow → **Disable workflow**.

### Dlaczego „× ryzyko” czasem nie wychodzi równe 1?
Bo kupno następuje po cenie rynkowej, a plan liczył ryzyko od ceny sygnału.
„× ryzyko” liczę od **faktycznej** ceny kupna do stopu, więc wychodzi inaczej
niż 1 z planu. To poprawne.

### Czy bot bada spółkę, zanim ją kupi?
Tak. Przed każdym kupnem czyta **raporty spółki ze SEC**: przychody, marże, zysk
netto, zysk na akcję, wzrost rok do roku. Nie kupuje spółki, która w ostatnim
kwartale straciła pieniądze, ani takiej, której przychody spadły o więcej niż
15% rok do roku. Co sprawdził, widać przy decyzji w panelu.

### Jak liczysz podatek?
19% od zysku **za cały rok**, nie od każdej transakcji. Stratę odliczam w kolejnych
latach — maksymalnie 5 lat i nie więcej niż połowę straty na rok. Płacę do
**30 kwietnia** roku następnego, więc do tego dnia pieniądze na podatek pracują.

### Czy w panelu są jakieś dane osobowe?
Nie. Panel pokazuje wyłącznie wyniki symulacji, koszty i statystyki. Nie ma
w nim żadnych danych konta ani informacji osobowych.

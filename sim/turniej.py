"""Turniej: ~1000 wariantów, różne warunki, wybór i sprawdzenie.

Po co: jeden wynik po 14 miesiącach nic nie powie — nie ma z czym porównać.
Tu liczymy ~1000 wariantów na 60 dniach sesyjnych i patrzymy, co naprawdę
działa, a co jest przypadkiem.

Jak to jest zrobione uczciwie:
  * OKNA CZASU. 60 dni dzielę na 3 okna po 20 dni. Wariant, który wygrywa
    w jednym oknie, a przegrywa w drugim, to nie przewaga, tylko szum.
  * WYBÓR I SPRAWDZENIE. Najlepsze warianty wybieram na oknach 1-2, a potem
    sprawdzam je na oknie 3, którego nie widziały. To jedyny uczciwy test.
  * ROZKŁAD SZCZĘŚCIA. 150 wariantów ma IDENTYCZNE reguły i różni się tylko
    losowym wyborem sygnałów. Ich rozrzut pokazuje, ile wyniku to czysty traf.
  * RÓŻNE WARUNKI. Rodzina reguł (przebicie / powrót do średniej), zasięg
    stopu, cel, ryzyko, liczba pozycji, okno wejścia, dźwignia, koszyk spółek.
  * KOSZTY: wymiana waluty 0,5%, poślizg 5 pb na stronę, podatek 19% na koniec.
  * CZEGO NIE MA: prowizji CFD (nie znam stawki), swapu (pozycje dzienne),
    realnych świąt giełdowych (dni z małą liczbą świec odrzucam).

Uruchomienie:
  python sim/turniej.py            # dane z cache, liczy i zapisuje wynik
  python sim/turniej.py --swiezo   # wymusza ponowne pobranie danych
"""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim import market, store  # noqa: E402

# --- założenia ---------------------------------------------------------------
START_PLN = 10000.0
MIESIEC_PLN = 10000.0
KURS = 3.9378
FX = 0.005
SLIP = 0.0005
PODATEK = 0.19
MIN_WOLNY_DEPOZYT = 0.20
WEJSCIE_OD = 9 * 60 + 45
PLASKIE_OD = 15 * 60 + 55
MIN_SWIEC = 40
OKIEN = 3                        # na ile części dzielę okres
LOSOWYCH = 150                   # ile wariantów na rozkład szczęścia
CEL_WARIANTÓW = 1000
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "turniej-5m.json")
DANE = os.path.join(store.ROOT, "docs", "turniej.json")
ZIARNO = 20261026

# --- dane --------------------------------------------------------------------
def symbole() -> list[str]:
    out = []
    for linia in open(os.path.join(store.ROOT, "universe.txt"), encoding="utf-8"):
        kod = linia.split("#")[0].strip().upper()
        if kod:
            out.append(kod)
    return out


def pobierz(sym: list[str], swiezo: bool = False) -> dict:
    if not swiezo and os.path.exists(CACHE):
        try:
            d = json.load(open(CACHE, encoding="utf-8"))
            if all(s in d for s in sym + ["SPY"]):
                print("  dane z pamięci podręcznej (%d spółek + SPY)" % len(sym))
                return d
        except ValueError:
            pass
    d = {}
    for i, s in enumerate(sym + ["SPY"], 1):
        try:
            bary = market.bars(s, "60d", "5m")
            d[s] = [[b["ny"], b["o"], b["h"], b["l"], b["c"]] for b in bary]
            print("  [%2d/%d] %s: %d świec" % (i, len(sym) + 1, s, len(d[s])))
        except Exception as e:  # noqa: BLE001
            print("  [%2d/%d] %s: POMINIĘTE (%s)" % (i, len(sym) + 1, s, e))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(d, open(CACHE, "w", encoding="utf-8"))
    return d


def na_dni(dane: dict) -> dict:
    out = {}
    for sym, bary in dane.items():
        dni = defaultdict(list)
        for ny, o, h, l, c in bary:
            dni[ny[:10]].append((ny[11:16], o, h, l, c))
        dobre = {d: sorted(v) for d, v in dni.items() if len(v) >= MIN_SWIEC}
        if dobre:
            out[sym] = dobre
    return out


def na_minuty(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def koszyki(dni: dict) -> dict[str, set[str]]:
    """Podzbiory spółek: wszystkie, spokojne, zmienne, oraz branże z katalogu."""
    zmiennosc = {}
    for sym, per_day in dni.items():
        wart = [((b[2] - b[3]) / b[4]) for bary in per_day.values() for b in bary if b[4]]
        if wart:
            zmiennosc[sym] = sum(wart) / len(wart)
    posort = sorted(zmiennosc, key=lambda s: zmiennosc[s])
    trzecia = max(len(posort) // 3, 1)
    out = {"wszystkie": set(dni),
           "spokojne": set(posort[:trzecia]),
           "zmienne": set(posort[-trzecia:])}
    kat = defaultdict(set)
    sciezka = os.path.join(store.ROOT, "data", "spolki.csv")
    if os.path.exists(sciezka):
        for linia in open(sciezka, encoding="utf-8"):
            czesci = [x.strip() for x in linia.split(",")]
            if len(czesci) >= 3 and czesci[0].upper() in dni:
                k = czesci[2].lower()
                if "tech" in k or "półprzewod" in k or "internet" in k or "software" in k:
                    kat["tech"].add(czesci[0].upper())
                elif "finans" in k or "bank" in k:
                    kat["finanse"].add(czesci[0].upper())
                elif "energ" in k or "przem" in k or "motoryz" in k:
                    kat["przemysl"].add(czesci[0].upper())
    for k, v in kat.items():
        if len(v) >= 4:
            out[k] = v
    return {k: v for k, v in out.items() if v}


# --- sygnały -----------------------------------------------------------------
def _wyjscie(bary: list, idx: int, stop: float, cel: float, cena: float) -> tuple[float, str]:
    """Gdzie kończy się transakcja: stop, cel czy zamknięcie dnia."""
    for b in bary[idx + 1:]:
        if na_minuty(b[0]) > PLASKIE_OD:
            break
        if b[3] <= stop:                    # gorzej liczę pierwsze
            return stop * (1 - SLIP), "stop"
        if b[2] >= cel:
            return cel, "cel"
    ostatni = [b for b in bary[idx + 1:] if na_minuty(b[0]) <= PLASKIE_OD]
    if not ostatni:
        return cena, "koniec dnia"
    return ostatni[-1][4] * (1 - SLIP), "koniec dnia"


def sygnaly(dni: dict, rodzina: str = "przebicie") -> dict:
    """Wejścia i wyniki dla każdej spółki i dnia, dla wszystkich par (stop, cel).

    rodzina "przebicie"     — kupno, gdy cena zamknie się NAD szczytem otwarcia
    rodzina "powrot"        — kupno, gdy cena zamknie się POD dołem otwarcia
    """
    out = defaultdict(dict)
    for sym, per_day in dni.items():
        for dzien, bary in per_day.items():
            or_bary = [b for b in bary if na_minuty(b[0]) < WEJSCIE_OD]
            if len(or_bary) < 3:
                continue
            gora = max(b[2] for b in or_bary)
            dol = min(b[3] for b in or_bary)
            szerokosc = gora - dol
            if szerokosc <= 0:
                continue
            wejscie = None
            for i, b in enumerate(bary):
                if na_minuty(b[0]) < WEJSCIE_OD:
                    continue
                if rodzina == "przebicie" and b[4] > gora:
                    wejscie = (i, b)
                    break
                if rodzina == "powrot" and b[4] < dol:
                    wejscie = (i, b)
                    break
            if not wejscie:
                continue
            idx, bar = wejscie
            cena = bar[4]
            wynik = {}
            for k_stopu in ((0.5, 0.75, 1.0) if rodzina == "przebicie" else (0.25, 0.5, 1.0)):
                if rodzina == "przebicie":
                    stop = gora - k_stopu * szerokosc
                    if stop >= cena:
                        continue
                    r = cena - stop
                    for mult in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
                        cel = cena + mult * r
                        wyj, sposob = _wyjscie(bary, idx, stop, cel, cena)
                        wynik[("przebicie", k_stopu, mult)] = {
                            "cena": round(cena, 4), "stop": round(stop, 4), "cel": round(cel, 4),
                            "wyj": round(wyj, 4), "sposob": sposob,
                            "r": round((wyj - cena) / r, 4)}
                else:
                    # powrót do średniej: kupno PO zejściu pod dół zakresu.
                    # Stop pod ceną (to pozycja długa), cel nad nią.
                    stop = round(cena - k_stopu * szerokosc, 4)
                    if stop <= 0 or stop >= cena:
                        continue
                    r = cena - stop
                    for mult in (0.5, 1.0, 1.5, 2.0, 3.0):
                        cel = cena + mult * r
                        wyj, sposob = _wyjscie(bary, idx, stop, cel, cena)
                        wynik[("powrot", k_stopu, mult)] = {
                            "cena": round(cena, 4), "stop": round(stop, 4), "cel": round(cel, 4),
                            "wyj": round(wyj, 4), "sposob": sposob,
                            "r": round((wyj - cena) / r, 4)}
            if wynik:
                out[sym][dzien] = {"cena": round(cena, 4), "godz": bar[0],
                                   "or_high": round(gora, 4), "or_low": round(dol, 4),
                                   "nad_szczytem": round((cena / gora - 1) * 100, 3),
                                   "wynik": wynik}
    return out


def sygnaly_moneta(dni: dict) -> dict:
    """Kontrola: brak sygnału — wejście na otwarciu, stop 1,5%, cel 1,5%."""
    out = defaultdict(dict)
    for sym, per_day in dni.items():
        for dzien, bary in per_day.items():
            cena = bary[0][1]
            stop, cel = round(cena * 0.985, 4), round(cena * 1.015, 4)
            wyj, sposob = _wyjscie(bary, 0, stop, cel, cena)
            out[sym][dzien] = {"cena": round(cena, 4), "godz": bary[0][0], "nad_szczytem": 0.0,
                               "wynik": {("moneta", 0.0, 1.0): {
                                   "cena": round(cena, 4), "stop": stop, "cel": cel,
                                   "wyj": round(wyj, 4), "sposob": sposob,
                                   "r": round((wyj - cena) / (cena - stop), 4)}}}
    return out


# --- lista wariantów ---------------------------------------------------------
def warianty(kosz: dict[str, set[str]]) -> list[dict]:
    """~1000 wariantów: reguły (siatka + losowa próba), kontrole i wzorce."""
    rng = random.Random(ZIARNO)
    w = [
        {"id": "B0", "nazwa": "Nic nie robię (gotówka)", "typ": "gotowka"},
        {"id": "B1", "nazwa": "Indeks S&P 500 — kup i trzymaj", "typ": "spy"},
        {"id": "B2", "nazwa": "Te same spółki — kup i trzymaj", "typ": "kup_trzymaj"},
        {"id": "B3", "nazwa": "Bez sygnału: losowe spółki, stop 1,5%", "typ": "moneta",
         "rodzina": "moneta", "k_stopu": 0.0, "cel": 1.0, "ryzyko": 1.0, "ile": 3,
         "okno": 3, "dzwignia": 5.0, "koszyk": "wszystkie", "losowo": 3},
    ]
    nazwy_kosz = list(kosz)
    # siatka podstawowa: to, co już testowaliśmy (36 wariantów)
    for k_stopu in (0.5, 1.0):
        for cel in (1.0, 1.5, 2.0):
            for ryzyko in (0.5, 1.0, 2.0):
                for ile in (1, 3):
                    w.append(_w_reg("R-%s-%.2g-%.2g-%d" % (k_stopu, cel, ryzyko, ile),
                                    "przebicie", k_stopu, cel, ryzyko, ile, 2, 5.0, "wszystkie"))
    # reszta do ~1000: losowa próba z pełnej przestrzeni warunków
    zasoby = []
    for rodzina, kstop, cele in (("przebicie", (0.5, 0.75, 1.0), (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)),
                                 ("powrot", (0.25, 0.5, 1.0), (0.5, 1.0, 1.5, 2.0, 3.0))):
        for k in kstop:
            for c in cele:
                for r in (0.25, 0.5, 1.0, 2.0, 4.0):
                    for i in (1, 2, 3, 5):
                        for okno in (1, 2, 3):
                            for dzw in (1.0, 3.0, 5.0):
                                for kk in nazwy_kosz:
                                    zasoby.append(_w_reg(None, rodzina, k, c, r, i, okno, dzw, kk))
    rng.shuffle(zasoby)
    docel = CEL_WARIANTÓW - len(w) - LOSOWYCH - 1
    wybrane = zasoby[:docel]
    for n, x in enumerate(wybrane, 1):
        x["id"] = "S%03d" % n
    w += wybrane
    # rozkład szczęścia: identyczne reguły, różny losowy wybór sygnałów
    for seed in range(LOSOWYCH):
        w.append({"id": "L%03d" % seed, "nazwa": "losowy wybór sygnałów (te same reguły)",
                  "typ": "orb", "rodzina": "przebicie", "k_stopu": 0.5, "cel": 1.0,
                  "ryzyko": 1.0, "ile": 3, "okno": 2, "dzwignia": 5.0, "koszyk": "wszystkie",
                  "losowo": seed})
    return w


def _w_reg(wid, rodzina, k_stopu, cel, ryzyko, ile, okno, dzwignia, koszyk) -> dict:
    return {"id": wid, "nazwa": "%s | stop %.2g×zakres | cel %.2g×R | ryzyko %.2g%% | "
                                "pozycji %d | okno %d | dźwignia %.0f:1 | %s"
                                % (rodzina, k_stopu, cel, ryzyko, ile, okno, dzwignia, koszyk),
            "typ": "orb", "rodzina": rodzina, "k_stopu": k_stopu, "cel": cel,
            "ryzyko": ryzyko, "ile": ile, "okno": okno, "dzwignia": dzwignia, "koszyk": koszyk}


GRANICE_OKNA = {1: 10 * 60 + 30, 2: 11 * 60 + 30, 3: 14 * 60}


# --- symulacja ---------------------------------------------------------------
def _wplata(dzien: str, stan: dict) -> float:
    if not stan["depozyty"]:
        return 0.0
    miesiac = dzien[:7]
    if miesiac in stan["miesiace"]:
        return 0.0
    stan["miesiace"][miesiac] = True
    pln = START_PLN if not stan["bylo"] else MIESIEC_PLN
    stan["bylo"] = True
    stan["wplaty_pln"] += pln
    return pln * (1 - FX) / KURS


def _wzorzec(w: dict, dni_lista: list[str], bazy: dict, spy: dict, depozyty: bool) -> dict:
    stan = {"miesiace": {}, "bylo": False, "wplaty_pln": 0.0, "depozyty": depozyty}
    if not depozyty:
        stan["wplaty_pln"] = START_PLN
        gotowka = START_PLN * (1 - FX) / KURS
    else:
        gotowka = 0.0
    sztuki, seria = 0.0, []
    for dzien in dni_lista:
        gotowka += _wplata(dzien, stan)
        cena = (spy if w["typ"] == "spy" else bazy).get(dzien)
        if w["typ"] in ("spy", "kup_trzymaj") and cena and gotowka > 0:
            sztuki += gotowka / cena
            gotowka = 0.0
        seria.append(round((gotowka + (sztuki * cena if cena else 0.0)) * KURS, 2))
    return _podsumuj(w, seria, [], stan["wplaty_pln"])


def _orb(w: dict, sig: dict, kand: dict, dni_lista: list[str], depozyty: bool) -> dict:
    stan = {"miesiace": {}, "bylo": False, "wplaty_pln": 0.0, "depozyty": depozyty}
    if not depozyty:
        stan["wplaty_pln"] = START_PLN
        gotowka = START_PLN * (1 - FX) / KURS
    else:
        gotowka = 0.0
    seria, transakcje = [], []
    rng = random.Random(w.get("losowo", 7))
    losowo = w.get("losowo") is not None
    granica = GRANICE_OKNA.get(w.get("okno", 2), 11 * 60 + 30)
    dzw = float(w.get("dzwignia", 5.0))
    klucz = (w.get("rodzina", "przebicie"), w.get("k_stopu", 0.5), w.get("cel", 1.0))
    for dzien in dni_lista:
        gotowka += _wplata(dzien, stan)
        kapital = gotowka
        if kapital <= 0:
            seria.append(0.0)
            continue
        lista = [x for x in kand.get(dzien, [])
                 if na_minuty(x[1]["godz"]) <= granica and klucz in x[1]["wynik"]]
        if losowo:
            rng.shuffle(lista)
        else:
            lista.sort(key=lambda x: -x[1]["nad_szczytem"])
        wolne = kapital * dzw * (1 - MIN_WOLNY_DEPOZYT)
        wziete = 0
        for sym, d in lista:
            if wziete >= w["ile"]:
                break
            wyn = d["wynik"][klucz]
            cena, stop = d["cena"] * (1 + SLIP), wyn["stop"]   # zawsze kupno
            r_akcja = abs(cena - stop)
            if r_akcja <= 0:
                continue
            ile = int(min(kapital * w["ryzyko"] / 100.0 / r_akcja,
                          kapital * dzw / cena, wolne / cena))
            if ile < 1:
                continue
            gotowka -= ile * cena
            wolne -= ile * cena
            gotowka += ile * wyn["wyj"]
            transakcje.append({"sym": sym, "dzien": dzien, "r": wyn["r"], "sposob": wyn["sposob"]})
            wziete += 1
        seria.append(round(gotowka * KURS, 2))
    return _podsumuj(w, seria, transakcje, stan["wplaty_pln"])


def _podsumuj(w: dict, seria: list[float], transakcje: list[dict], wplaty_pln: float) -> dict:
    koniec = seria[-1] if seria else 0.0
    zysk = koniec - wplaty_pln
    po_podatku = koniec - max(zysk, 0.0) * PODATEK
    r_lista = [t["r"] for t in transakcje]
    szczyt = max_dd = 0.0
    for v in seria:
        szczyt = max(szczyt, v)
        max_dd = max(max_dd, (szczyt - v) / szczyt if szczyt else 0.0)
    return {"id": w["id"], "nazwa": w["nazwa"], "typ": w["typ"],
            "rodzina": w.get("rodzina", ""), "koszyk": w.get("koszyk", ""),
            "wplacone_pln": round(wplaty_pln, 2), "koniec_pln": round(koniec, 2),
            "zwrot_pct": round((po_podatku / wplaty_pln - 1) * 100, 2) if wplaty_pln else 0.0,
            "transakcje": len(transakcje),
            "skutecznosc_pct": round(100.0 * sum(1 for r in r_lista if r > 0) / len(r_lista), 1)
                                if r_lista else 0.0,
            "srednie_r": round(sum(r_lista) / len(r_lista), 3) if r_lista else 0.0,
            "max_spadek_pct": round(max_dd * 100, 2)}


def _raport(zapis: dict) -> str:
    """Strona z wynikami turnieju (osobna od panelu symulacji)."""
    w = zapis["wyniki"]
    wzorce = [x for x in w if x["id"].startswith("B")]
    sz = zapis.get("szczescie") or {}
    wy = zapis.get("wybor") or {}
    los = [x for x in w if x["id"].startswith("L")]
    b1 = next((x["zwrot_pct"] for x in wzorce if x["id"] == "B1"), 0.0)
    b0 = next((x["zwrot_pct"] for x in wzorce if x["id"] == "B0"), 0.0)
    procent = 100.0 * wy.get("plus_w_3_oknach", 0) / max(wy.get("regul_razem", 1), 1)

    def wiersz(x, i):
        ok = " ".join("%+.1f%%" % v for v in x.get("okna_pct", []))
        return ("<tr><td class='r'>%s</td><td><b>%s</b></td><td class='r %s'>%+.2f%%</td>"
                "<td class='faint'>%s</td><td class='r'>%d</td><td class='r'>%.1f%%</td>"
                "<td class='r'>%+.2f</td><td class='r'>%.1f%%</td><td>%s</td></tr>"
                % (i, x["id"], "up" if x["zwrot_pct"] > 0 else "down", x["zwrot_pct"], ok,
                   x["transakcje"], x["skutecznosc_pct"], x["srednie_r"],
                   x["max_spadek_pct"], x["nazwa"].split("|", 1)[-1].strip()))

    def wzor(x):
        return ("<tr><td></td><td><b>%s</b></td><td class='r %s'>%+.2f%%</td>"
                "<td class='faint'>%s</td><td colspan='5'>%s</td></tr>"
                % (x["id"], "up" if x["zwrot_pct"] > 0 else "down", x["zwrot_pct"],
                   " ".join("%+.1f%%" % v for v in x.get("okna_pct", [])), x["nazwa"]))

    return f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Turniej wariantów — {zapis["wariantow"]} wariantów</title>
<style>
 :root{{--bg:#141231;--card:#201D47;--line:#33305A;--ink:#EDEBFF;--mut:#A9A6CC;
       --up:#38D9A9;--down:#F06595;--acc:#A389F4}}
 *{{box-sizing:border-box}}
 body{{margin:0;background:var(--bg);color:var(--ink);
      font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
 .wrap{{max-width:1080px;margin:0 auto;padding:28px 20px 60px}}
 h1{{font-size:28px;margin:0 0 6px}} h2{{font-size:20px;margin:34px 0 12px}}
 p{{color:var(--mut);max-width:66ch;margin:8px 0}}
 a{{color:var(--acc)}}
 .kafle{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:20px 0}}
 .kaf{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}}
 .kaf span{{display:block;color:var(--mut);font-size:13px;margin-bottom:4px}}
 .kaf b{{font-size:20px}}
 .up{{color:var(--up)}} .down{{color:var(--down)}} .faint{{color:var(--mut);font-size:14px}}
 a.wroc{{display:inline-block;padding:3px 0}}
 table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;
        overflow:hidden;font-size:14px}}
 th,td{{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}}
 th{{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
 td.r,th.r{{text-align:right}}
 tr:last-child td{{border-bottom:0}}
 .uwaga{{background:rgba(240,101,149,.12);border:1px solid rgba(240,101,149,.42);
        border-radius:10px;padding:14px;color:#FBD9E5;margin:16px 0;max-width:70ch}}
 .dobra{{background:rgba(56,217,169,.10);border:1px solid rgba(56,217,169,.38);
        border-radius:10px;padding:14px;color:#D5FBEE;margin:16px 0;max-width:70ch}}
</style></head><body><div class="wrap">
<p><a class="wroc" href="index.html">&larr; panel symulacji</a></p>
<h1>Turniej wariantów</h1>
<p>{zapis["wariantow"]} wariantów na tych samych danych: {zapis["dni"]} dni sesyjnych
({zapis["od"]} → {zapis["do"]}), {zapis["spolek"]} spółek, {zapis["sygnalow"]["przebicie"]} sygnałów
przebicia i {zapis["sygnalow"]["powrot"]} powrotu do średniej.</p>

<div class="kafle">
 <div class="kaf"><span>Najlepszy wariant</span><b class="up">{w[0]["zwrot_pct"]:+.1f}%</b></div>
 <div class="kaf"><span>Indeks S&amp;P 500</span><b>{b1:+.1f}%</b></div>
 <div class="kaf"><span>Nic nie robię</span><b>{b0:+.1f}%</b></div>
 <div class="kaf"><span>Rozrzut przy tych samych regułach</span><b class="down">{sz.get("rozrzut", 0):.1f} pkt</b></div>
</div>

<div class="uwaga"><b>Najważniejsza liczba.</b> {wy.get("regul_razem", 0)} wariantów reguł,
a tylko {wy.get("plus_w_3_oknach", 0)} ({procent:.0f}%) było na plusie w <b>każdym</b>
z 3 okien czasowych. Reszta wygrywała raz i przegrywała raz — a to nie przewaga, tylko szum.</div>

<div class="dobra"><b>Uczciwy test.</b> Warianty wybrane na pierwszych dwóch oknach wypadły
na trzecim (nieznanym) oknie średnio <b>{wy.get("srednio_okno3", 0):+.2f}%</b>, przy medianie
wszystkich <b>{wy.get("mediana_okno3", 0):+.2f}%</b>. Wybór <i>coś</i> daje — ale o wiele mniej,
niż sugeruje tabela.</div>

<h2>Najlepsze 20 (cały okres)</h2>
<table><tr><th class="r">#</th><th>Wariant</th><th class="r">Wynik</th><th>Okna 1/2/3</th>
<th class="r">Transakcji</th><th class="r">Skuteczność</th><th class="r">Śr. R</th>
<th class="r">Maks. spadek</th><th>Reguły</th></tr>
{"".join(wiersz(x, i) for i, x in enumerate(w[:20], 1))}
</table>

<h2>Wzorce odniesienia</h2>
<p>Punkt odniesienia: <b>{b1:+.2f}%</b> daje samo trzymanie indeksu, a <b>{b0:+.2f}%</b> —
nic nie robienie (tyle kosztuje wymiana waluty).</p>
<table><tr><th class="r">#</th><th>Wariant</th><th class="r">Wynik</th><th>Okna 1/2/3</th>
<th colspan="5">Co robi</th></tr>
{"".join(wzor(x) for x in wzorce)}
</table>

<h2>Rozkład szczęścia</h2>
<p>{len(los)} wariantów ma <b>identyczne reguły</b> i różni się tylko tym, które sygnały wybrały.
Wynik od <b>{sz.get("najgorzej", 0):+.2f}%</b> do <b>{sz.get("najlepiej", 0):+.2f}%</b> —
rozrzut <b>{sz.get("rozrzut", 0):.2f} pkt proc.</b> przy <i>tych samych</i> regułach.
Tyle w tym eksperymencie wynosi czysty traf.</p>

<h2>Czego ten turniej nie mówi</h2>
<p>To <b>jeden okres i jeden rynek</b>. Wybór najlepszego wariantu po fakcie jest łatwy i zwykle
bezużyteczny — dlatego liczy się kolumna „okna" i test na nieznanym oknie. Koszty są policzone
(wymiana waluty 0,5%, poślizg 5 pb na stronę, podatek 19%), ale <b>bez prowizji CFD</b> — nie znam
stawki. Pozycje zamykam tego samego dnia, więc swapu nie ma.</p>
<p class="faint">Policzone {zapis["kiedy"]} czasu Nowego Jorku. Dane: Yahoo, świece 5-minutowe.
To nie porada inwestycyjna.</p>
</div></body></html>'''


def main() -> int:
    swiezo = "--swiezo" in sys.argv
    dane = pobierz(symbole(), swiezo=swiezo)
    pełne = na_dni(dane)
    dni_calosc = sorted(d for d in {x for pd in pełne.values() for x in pd}
                        if sum(1 for s in pełne if d in pełne[s]) >= 20)
    n_okna = max(len(dni_calosc) // OKIEN, 5)
    okna = [dni_calosc[i * n_okna:(i + 1) * n_okna] for i in range(OKIEN)]
    print("  spółek: %d | dni: %d | okna: %s"
          % (len(pełne), len(dni_calosc),
             ", ".join("%d dni (%s→%s)" % (len(o), o[0], o[-1]) for o in okna)))

    kosz = koszyki(pełne)
    print("  koszyki: %s" % ", ".join("%s=%d" % (k, len(v)) for k, v in kosz.items()))

    print("  liczę sygnały...")
    syg = {"przebicie": sygnaly(pełne, "przebicie"),
           "powrot": sygnaly(pełne, "powrot"),
           "moneta": sygnaly_moneta(pełne)}
    print("  sygnałów: przebicie %d, powrót %d"
          % (sum(len(v) for v in syg["przebicie"].values()),
             sum(len(v) for v in syg["powrot"].values())))

    def zbuduj_kand(sig: dict, koszyk: str) -> dict:
        dozwolone = kosz.get(koszyk, set(pełne))
        out = defaultdict(list)
        for sym, per_day in sig.items():
            if sym not in dozwolone:
                continue
            for d, v in per_day.items():
                out[d].append((sym, v))
        return out

    kand = defaultdict(dict)
    for rodzina in ("przebicie", "powrot", "moneta"):
        for k in kosz:
            kand[(rodzina, k)] = zbuduj_kand(syg[rodzina], k)

    bazy, spy = {}, {}
    for d in dni_calosc:
        otw = [pełne[s][d][0][1] for s in pełne if d in pełne[s]]
        if otw:
            bazy[d] = sum(otw) / len(otw)
        if "SPY" in pełne and d in pełne["SPY"]:
            spy[d] = pełne["SPY"][d][0][1]

    war = warianty(kosz)
    print("  liczę %d wariantów × (całość + %d okien)..." % (len(war), OKIEN))

    def uruchom(w: dict, dni_l: list[str], depozyty: bool, okno: int | None) -> dict:
        if w["typ"] in ("gotowka", "spy", "kup_trzymaj"):
            return _wzorzec(w, dni_l, bazy, spy, depozyty)
        rodzina = "moneta" if w["typ"] == "moneta" else w.get("rodzina", "przebicie")
        ww = dict(w)
        if okno is not None:
            ww["okno"] = okno
        return _orb(ww, syg[rodzina], kand[(rodzina, w.get("koszyk", "wszystkie"))],
                    dni_l, depozyty)

    wyniki = []
    for w in war:
        g = uruchom(w, dni_calosc, True, None)
        czastki = [uruchom(w, ok, False, i + 1)["zwrot_pct"] for i, ok in enumerate(okna) if ok]
        g["okna_pct"] = czastki
        g["w_oknach_plus"] = sum(1 for x in czastki if x > 0)
        wyniki.append(g)

    wyniki.sort(key=lambda x: -x["zwrot_pct"])
    reguly = [x for x in wyniki if x["id"][0] in "RS"]
    losowe = [x for x in wyniki if x["id"].startswith("L")]
    wzorce = [x for x in wyniki if x["id"].startswith("B")]

    # --- analiza ------------------------------------------------------------
    print("\n  === NAJLEPSZE 10 (cały okres) ===")
    for x in wyniki[:10]:
        print("   %-6s %+7.2f%%  okna %s  trans %4d  skut %4.1f%%  dd %4.1f%%  %s"
              % (x["id"], x["zwrot_pct"], x["okna_pct"], x["transakcje"],
                 x["skutecznosc_pct"], x["max_spadek_pct"], x["nazwa"][:52]))
    print("\n  === WZORCE ODNIESIENIA ===")
    for x in wzorce:
        print("   %-6s %+7.2f%%  okna %s  %s" % (x["id"], x["zwrot_pct"], x["okna_pct"], x["nazwa"]))

    zl = [x["zwrot_pct"] for x in losowe]
    med = statistics.median(zl) if zl else 0.0
    print("\n  === ROZKŁAD SZCZĘŚCIA (%d wariantów, identyczne reguły) ===" % len(losowe))
    print("   najgorzej %+.2f%% | mediana %+.2f%% | najlepiej %+.2f%%  → rozrzut %.2f pkt proc."
          % (min(zl), med, max(zl), max(zl) - min(zl)))

    # selekcja na oknach 1-2, sprawdzenie na oknie 3
    ws = [x for x in reguly if len(x["okna_pct"]) >= 3]
    ws.sort(key=lambda x: -(x["okna_pct"][0] + x["okna_pct"][1]))
    top = ws[:20]
    out3 = [x["okna_pct"][2] for x in top]
    wszystkie3 = [x["okna_pct"][2] for x in ws]
    print("\n  === WYBÓR NA OKNACH 1-2, SPRAWDZENIE NA OKNIE 3 ===")
    print("   wybrane 20 wariantów: średnio %+.2f%% na oknie 3 (mediana wszystkich %+.2f%%)"
          % (statistics.mean(out3) if out3 else 0.0, statistics.median(wszystkie3) if wszystkie3 else 0.0))
    rob = [x for x in ws if x["w_oknach_plus"] == 3]
    print("   wariantów na plus w KAŻDYM z 3 okien: %d z %d (%.0f%%)"
          % (len(rob), len(ws), 100.0 * len(rob) / max(len(ws), 1)))
    print("   wariantów na plus w całości: %d z %d (%.0f%%)"
          % (sum(1 for x in reguly if x["zwrot_pct"] > 0), len(reguly),
             100.0 * sum(1 for x in reguly if x["zwrot_pct"] > 0) / max(len(reguly), 1)))
    naj = wyniki[0]
    percentyl = 100.0 * sum(1 for z in zl if z < naj["zwrot_pct"]) / max(len(zl), 1)
    print("   najlepszy wariant (%s, %+.2f%%) jest na %.1f. percentylu rozkładu szczęścia"
          % (naj["id"], naj["zwrot_pct"], percentyl))

    zapis = {"kiedy": store.ny_stamp(),
             "dni": len(dni_calosc), "od": dni_calosc[0], "do": dni_calosc[-1],
             "spolek": len(pełne), "wariantow": len(war), "okien": OKIEN,
             "okna": [{"od": o[0], "do": o[-1], "dni": len(o)} for o in okna],
             "sygnalow": {"przebicie": sum(len(v) for v in syg["przebicie"].values()),
                          "powrot": sum(len(v) for v in syg["powrot"].values())},
             "szczescie": {"najgorzej": min(zl), "mediana": med, "najlepiej": max(zl),
                           "rozrzut": round(max(zl) - min(zl), 2)} if zl else {},
             "wybor": {"wybrane": 20, "srednio_okno3": round(statistics.mean(out3), 2) if out3 else 0.0,
                       "mediana_okno3": round(statistics.median(wszystkie3), 2) if wszystkie3 else 0.0,
                       "plus_w_3_oknach": len(rob), "plus_w_calosci":
                       sum(1 for x in reguly if x["zwrot_pct"] > 0), "regul_razem": len(reguly)},
             "wyniki": wyniki}
    os.makedirs(os.path.dirname(DANE), exist_ok=True)
    json.dump(zapis, open(DANE, "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"))
    raport = os.path.join(store.ROOT, "docs", "turniej.html")
    open(raport, "w", encoding="utf-8").write(_raport(zapis))
    print("\n  zapisano: %s i %s (%d wariantów)" % (DANE, raport, len(wyniki)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

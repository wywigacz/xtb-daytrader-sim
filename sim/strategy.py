"""Strategia: zarzadzanie otwartymi pozycjami i szukanie wejsc.

Metodyka pochodzi z day-trader-skill:
  skan ORB -> wiadomosci -> entry (pierwsza swieca 5m zamykajaca sie nad szczytem
  zakresu) -> exit (stop = srodek zakresu, target = 1R) -> size (pod limit straty)
  -> kontrola ryzyka (PASS/BLOCK).
Roznica: nie ma czlowieka, ktory powie "tak". Symulator sam potwierdza
zatwierdzenie (auto-yes) i sam wykonuje symulowana transakcje po cenie
z rynku powiekszonej o poslizg. To jest cala idea tego repo.

Kazda decyzja trafia do dziennika razem z polskim tytulem, jednym zdaniem
"dlaczego" i liczbami - z tego powstaje panel.
"""
from __future__ import annotations

import os
import time
from datetime import datetime

from . import book, market, news, plain, session as ses, skilltools, store, xtb


def _clock_args(now=None) -> list[str]:
    """Jesli zegar jest zamrozony (SIM_NOW), przekaz go rowniez narzedziom skilla."""
    stamp = store.ny_stamp(now) if now is not None else os.environ.get("SIM_NOW")
    return ["--now", stamp] if stamp else []


def build_risk_config(sim: dict, equity_usd: float) -> dict:
    """Wygeneruj trader/config.json (limity skilla) proporcjonalnie do kapitalu."""
    cfg = book.load_cfg()
    rf = cfg["risk_from_equity"]
    eq = max(float(equity_usd), 50.0)
    c = {
        "budget": round(eq, 2),
        "cash_buffer_pct": rf["cash_buffer_pct"],
        "max_position_pct": rf["max_position_pct"],
        "max_order_usd": round(eq * rf["max_position_pct"] / 100.0, 2),
        "min_order_usd": 5,
        "max_loss_per_trade_usd": round(eq * rf["max_loss_per_trade_pct"] / 100.0, 2),
        "max_daily_loss_usd": round(eq * rf["max_daily_loss_pct"] / 100.0, 2),
        "max_trades_per_day": rf["max_trades_per_day"],
        "max_orders_per_day": 10,
        "min_reward_risk": rf["min_reward_risk"],
        "require_stop": True,
        "no_entries_before": "09:45",
        "no_entries_after": "15:30",
        "flat_by": "15:55",
        "fractional": False,
        "broker": "xtb",
        "paper": True,
        "blocked": [],
        "allow_options": False,
        "allow_margin": False,
        "allow_short": False,
        "pdt_guard": False,
        "sec_user_agent": os.environ.get("SEC_USER_AGENT", "xtb-daytrader-sim contact@example.com"),
    }
    store.write_json(store.CONFIG, c)
    return c


def write_prices(quotes: dict[str, tuple[float, float]], merge: bool = True) -> None:
    """Zapisz trader/prices.json: {SYM: (cena, epoch)}. Domyslnie dopisuje do
    istniejacego pliku (ceny innych spolek zostaja)."""
    now_utc = datetime.utcnow()
    old = store.read_json(store.PRICES) if merge else None
    prices = dict((old or {}).get("prices") or {})
    detail = dict((old or {}).get("detail") or {})
    for s, (p, t) in quotes.items():
        s = s.upper()
        prices[s] = round(p, 4)
        detail[s] = {
            "time": datetime.utcfromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetched": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    store.write_json(store.PRICES, {
        "as_of": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "yahoo",
        "prices": prices,
        "detail": detail,
    })


def quotes_for(symbols: list[str]) -> dict[str, tuple[float, float]]:
    out = {}
    for s in symbols:
        try:
            out[s] = market.last_price(s)
        except Exception:  # noqa: BLE001
            continue
    return out


# ------------------------------------------------------------------ ZARZADZANIE
def _opened_epoch(op: dict) -> int:
    try:
        d = datetime.strptime(op["opened_at"], "%Y-%m-%d %H:%M").replace(tzinfo=ses.NY)
        return int(d.timestamp())
    except Exception:  # noqa: BLE001
        return 0


def manage(sim: dict, now=None, force_close_all: bool = False) -> list[dict]:
    """Przejdz po otwartych pozycjach po swiecach 5m i zamknij te, ktore trafily
    w stop / target / czas 'flat by'. Zwraca liste zamknietych transakcji."""
    cfg = book.load_cfg()
    costs = cfg["costs"]
    slip = float(costs["slippage_bps"])
    comm = float(costs["commission_pct"])
    comm_min = float(costs.get("commission_min_usd") or 0.0)
    now_dt = ses.now_ny(now)
    now_epoch = int(now_dt.timestamp())
    closed = []

    for symbol in list((sim.get("open") or {}).keys()):
        op = sim["open"][symbol]
        stop = float(op.get("stop") or 0)
        target = float(op.get("target") or 0)
        qty = float(op.get("qty") or 0)
        opened = _opened_epoch(op)
        flat_dt = ses.flat_by(datetime.strptime(op["opened_day"], "%Y-%m-%d").date(),
                              op.get("flat_by") or "15:55")
        flat_epoch = int(flat_dt.timestamp())

        try:
            bars = market.bars(symbol, "1d", "5m")
        except Exception as e:  # noqa: BLE001
            book.decide(sim, "manage_error", symbol=symbol,
                        title="Brak danych o %s" % symbol,
                        why="Nie moglem pobrac swiec - sprawdze przy nastepnym uruchomieniu.",
                        error=str(e))
            continue

        hit = None
        for b in bars:
            bt = b["t"]
            if bt <= opened:
                continue
            if bt + 300 > now_epoch and not force_close_all:
                break  # swieca jeszcze nie zamknieta
            if bt + 300 >= flat_epoch:
                hit = ("flat_by", b["c"], "czas flat-by (koniec dnia)")
                break
            if stop and b["l"] <= stop:
                fill = min(b["o"], stop)
                hit = ("stop", round(fill, 4), "stop-loss trafiony")
                break
            if target and b["h"] >= target:
                fill = max(b["o"], target)
                hit = ("target", round(fill, 4), "take-profit trafiony")
                break

        if hit is None and force_close_all:
            px = bars[-1]["c"] if bars else None
            if px:
                hit = ("eod_flat", round(px, 4), "awaryjne domkniecie po sesji")
        if hit is None and now_epoch >= flat_epoch:
            px = bars[-1]["c"] if bars else None
            if px:
                hit = ("flat_by", round(px, 4), "czas flat-by (koniec dnia)")

        if hit is None:
            continue

        reason, raw_price, note = hit
        if reason in ("flat_by", "eod_flat"):
            raw_price = xtb.slippage_price(raw_price, "sell", slip)
        fee = xtb.commission_usd(qty * raw_price, comm, comm_min)
        tr = book.close_position(sim, symbol, qty, round(raw_price, 4), fee, reason, now)

        title, why = plain.exit_reason(reason)
        book.decide(
            sim, "close", symbol=symbol,
            title="%s: %s" % (symbol, title.lower()),
            why=why,
            code=reason,
            numbers={
                "qty": qty, "entry": round(float(op.get("entry") or 0), 2),
                "exit": round(raw_price, 4), "pnl": tr["pnl_usd"],
                "r": tr.get("r_multiple"), "hold_min": tr.get("hold_min"),
                "stop": stop, "target": target,
            },
        )
        closed.append(tr)
    return closed


# ---------------------------------------------------------------------- WEJSCIA
def _traded_today(sim: dict, day: str) -> set[str]:
    today = set()
    for rec in (store.read_json(store.BROKER_STATE) or {}).get("orders", []):
        if str(rec.get("date")) == day and rec.get("kind") == "entry" and rec.get("status") in ("placed", "approved"):
            today.add(str(rec.get("symbol", "")).upper())
    return today


def scan_candidates(sim: dict, now=None) -> list[dict]:
    cfg = book.load_cfg()
    sc = cfg["scan"]
    args = [
        "orb",
        "--watchlist", "universe.txt",
        "--min-price", sc["min_price"],
        "--min-volume", sc["min_volume"],
        "--or-minutes", sc["or_minutes"],
        "--max-confirm", sc["max_confirm"],
        "--no-write",
    ]
    rc, doc, tail = skilltools.json_run("scan", args + _clock_args(now), timeout=240)
    if not doc:
        book.decide(sim, "scan_empty",
                    title="Skan nie zwrocil wynikow",
                    why="Feed z rynku nie odpowiedzial albo nie bylo jeszcze danych z sesji.",
                    note=tail[:300], rc=rc)
        return []
    hits = doc.get("hits") or []
    top = [h.get("symbol") for h in hits[:12]]
    book.decide(
        sim, "scan",
        title="Przejrzalem %s spolek" % doc.get("scanned"),
        why=("Szukalem ceny, ktora przebila maksimum pierwszych 15 minut sesji i zamknela sie nad nim. "
             "Znalazlem %d takich spolek." % len(hits)) if hits else
            ("Szukalem ceny, ktora przebila maksimum pierwszych 15 minut sesji. "
             "Zadna spolka nie dala sygnalu - nie kupuje na sile."),
        numbers={"scanned": doc.get("scanned"), "hits": len(hits), "top": top},
        as_of=doc.get("as_of"),
    )
    return hits


def try_enter(sim: dict, now=None) -> dict | None:
    """Jedno wejscie na tick, jesli sa wolne miejsca i wszystko przejdzie."""
    cfg = book.load_cfg()
    sim_cfg = cfg["simulation"]
    costs = cfg["costs"]
    now_dt = ses.now_ny(now)
    day = ses.iso_day(now_dt)

    if not ses.is_open(now_dt):
        return None
    if len(sim.get("open") or {}) >= int(sim_cfg["max_concurrent_positions"]):
        book.decide(sim, "skip", code="miejsca",
                    title="Brak wolnego miejsca",
                    why="Mam juz maksymalna liczbe otwartych pozycji naraz (%d)."
                        % int(sim_cfg["max_concurrent_positions"]))
        return None

    quotes = quotes_for(sorted(set(list(book.holdings().keys()) + ["SPY"])))
    if quotes:
        write_prices(quotes)
    m = book.mark(sim, {s: p for s, (p, _t) in quotes.items()})
    build_risk_config(sim, m["equity_usd"])

    hits = scan_candidates(sim, now_dt)
    if not hits:
        return None

    held = set(book.holdings().keys())
    already = _traded_today(sim, day)
    cands = [h for h in hits if str(h.get("symbol", "")).upper() not in held
             and str(h.get("symbol", "")).upper() not in already]
    if not cands:
        book.decide(sim, "skip", code="duplikat",
                    title="Wszystkie sygnaly juz wykorzystane",
                    why="Te spolki juz trzymam albo gralem nimi dzisiaj. Nie dokladam do tej samej pozycji.")
        return None

    for h in cands[:3]:
        sym = str(h["symbol"]).upper()
        res = _attempt(sim, sym, now_dt, costs)
        if res:
            return res
    return None


def _news_gate(sim: dict, sym: str, now_dt) -> dict:
    """Sprawdz wiadomosci. Sam wpis do dziennika robi wywolujacy (tylko gdy cos zmienia)."""
    doc = news.fetch([sym], hours=24)
    risk_items = [i for i in (doc.get("items") or []) if i.get("risk")]
    news.record(sim, doc,
                impact="wstrzymal zakup" if risk_items else "nie zmienil decyzji",
                symbol=sym)
    return {"blocked": bool(risk_items), "items": doc.get("items") or [],
            "count": doc.get("count") or 0, "risk_items": risk_items}


def _attempt(sim: dict, sym: str, now_dt, costs: dict) -> dict | None:
    """Sciezka jednego wejscia: wiadomosci -> entry -> exit -> size -> risk -> fill."""
    slip = float(costs["slippage_bps"])
    comm = float(costs["commission_pct"])
    comm_min = float(costs.get("commission_min_usd") or 0.0)

    # 0. Wiadomosci: twardy sygnal ryzyka = odpuszczam.
    gate = _news_gate(sim, sym, now_dt)
    if gate["blocked"]:
        hit = gate["risk_items"][0]
        book.decide(
            sim, "block", symbol=sym, code="news",
            title="Odpuscilem %s przez wiadomosci" % sym,
            why='Naglowek: "%s". Po takiej informacji cena potrafi skoczyc w obie strony, '
                'a ja nie zgaduje kierunku.' % str(hit.get("title") or "")[:110],
            numbers={"naglowek": str(hit.get("title") or "")[:160],
                     "zrodlo": hit.get("source") or "", "naglowkow": gate["count"]},
        )
        return None

    # 1. Swieza cena (do pomiaru ryzyka i do fillu).
    try:
        px, _t = market.last_price(sym)
    except Exception as e:  # noqa: BLE001
        book.decide(sim, "skip", symbol=sym, code="dane",
                    title="Brak swiezej ceny %s" % sym,
                    why="Nie mialem wiarygodnej ceny, wiec nie ryzykowalem.", error=str(e))
        return None
    write_prices({sym: (px, _t)})

    # 2. Entry Timer skilla: czy setup sie potwierdzil?
    rc, out, err = skilltools.run("entry", ["check", sym, "--write"] + _clock_args(now_dt), timeout=120)
    entry_doc = store.read_json(store.ENTRY) or {}
    status = str(entry_doc.get("status") or "")
    if rc != 0 or "trigger" not in status.lower():
        book.decide(sim, "skip", symbol=sym, code="brak-sygnalu",
                    title="%s nie potwierdzil sygnalu" % sym,
                    why="Cena nie zamknela sie nad porannym szczytem w sposob, ktory wymaga metoda.",
                    status=status)
        return None

    # 3. Exit Planner: stop = srodek zakresu, target 1R.
    rc, out, err = skilltools.run("exit", ["plan", "--stop", "or-mid", "--target", "1R", "--write"] + _clock_args(now_dt), timeout=120)
    if rc != 0:
        book.decide(sim, "skip", symbol=sym, code="plan",
                    title="Plan dla %s nie powstal" % sym,
                    why="Nie moglem wyznaczyc stopu i celu, a bez nich nie wchodze.",
                    detail=(err or out).strip()[:160])
        return None
    plan = store.read_json(store.PLAN) or {}
    if str(plan.get("symbol", "")).upper() != sym:
        book.decide(sim, "skip", symbol=sym, code="plan",
                    title="Plan dotyczyl innej spolki",
                    why="Plan wyjscia nie pasowal do tej spolki - odpuszczam.")
        return None

    # 4. Budget Manager: ile akcji.
    rc, out, err = skilltools.run("size", ["--write"] + _clock_args(now_dt), timeout=120)
    if rc != 0:
        code, title, meaning = plain.size_reason((err or out) + " " + (out or ""))
        book.decide(sim, "block", symbol=sym, code=code,
                    title="%s: %s" % (sym, title.lower()), why=meaning,
                    detail=(out or err).strip()[:200])
        return None
    orders = store.read_json(store.ORDERS) or {}
    olist = orders.get("orders") or []
    if not olist:
        book.decide(sim, "block", symbol=sym, code="size",
                    title="%s: zlecenie nie powstalo" % sym,
                    why="Kalkulator wielkosci pozycji nie znalazl bezpiecznego rozmiaru.")
        return None
    order = olist[0]
    qty = float(order.get("qty") or 0)
    if qty <= 0:
        book.decide(sim, "block", symbol=sym, code="size",
                    title="%s: zero akcji" % sym,
                    why="Przy tym stopie nie da sie kupic nawet jednej akcji w limicie straty.")
        return None

    # 5. Kontrola ryzyka: PASS albo BLOCK.
    rc, verdicts, tail = skilltools.json_run("check", _clock_args(now_dt), timeout=120)
    results = (verdicts or {}).get("results") or []
    passed = next((r for r in results if r.get("verdict") == "PASS"), None)
    if passed is None:
        raw = " ".join(str(x) for r in results for x in (r.get("reasons") or []))
        code, title, meaning = plain.block_reason(raw)
        book.decide(sim, "block", symbol=sym, code=code,
                    title="%s: %s" % (sym, title.lower()), why=meaning,
                    detail=raw[:220])
        return None

    # 5b. Kontrola sensu ceny. Miedzy sygnalem a wykonaniem cena mogla pojsc
    #     w zla strone. Jesli juz jest pod stopem (setup sie zepsul) albo nad
    #     celem (ruch sie wydarzyl) - nie wchodze. Bez tego wychodzily
    #     absurdalne transakcje: "stop" z zyskiem, bo stop byl nad wejsciem.
    fill = xtb.slippage_price(px, "buy", slip)
    stop_lvl = float(plan.get("stop") or 0)
    target_lvl = float(plan.get("target") or 0)
    if stop_lvl and fill <= stop_lvl:
        book.decide(
            sim, "block", symbol=sym, code="cena-pod-stopem",
            title="%s: cena zdazyla zjechac pod stop" % sym,
            why="Po sygnale cena spadla ponizej poziomu, na ktorym mialem sie wycofac. "
                "Wejscie teraz to strata ustawiona z gory.",
            numbers={"cena": round(fill, 2), "stop": stop_lvl},
        )
        return None
    if target_lvl and fill >= target_lvl:
        book.decide(
            sim, "block", symbol=sym, code="cel",
            title="%s: ruch juz sie wydarzyl" % sym,
            why="Cena poszla wyzej, niz byl moj cel, zanim zdazylem kupic. "
                "Do celu nie ma juz miejsca, wiec gra nie jest warta ryzyka.",
            numbers={"cena": round(fill, 2), "cel": target_lvl},
        )
        return None
    plan = dict(plan)
    plan["risk_per_share"] = round(fill - stop_lvl, 4) if stop_lvl else plan.get("risk_per_share")

    notional = qty * fill
    fee = xtb.commission_usd(notional, comm, comm_min)
    ts = store.ny_stamp(now_dt)
    skilltools.run("ticket", ["approve", "--index", 1, "--reply", "yes", "--now", ts], timeout=60)
    rc, out, err = skilltools.run(
        "ticket",
        ["result", "--index", 1, "--status", "placed", "--broker-id", "SIM-%s" % int(time.time()),
         "--filled-qty", qty, "--filled-price", round(fill, 4), "--now", ts],
        timeout=60,
    )
    if rc != 0:
        book.decide(sim, "error", symbol=sym, code="fill",
                    title="Nie udalo sie zaksiiegowac kupna %s" % sym,
                    why="Zlecenie przeszlo kontrole, ale zapis wykonania sie nie powiodl.",
                    detail=(err or out).strip()[:160])
        return None

    # 7. Stan symulacji.
    book.record_open(sim, sym, qty, round(fill, 4), plan, notional, fee,
                     reason="ORB", now=now_dt)

    rng = entry_doc.get("opening_range") or {}
    pct_over = ""
    try:
        if rng.get("high"):
            pct_over = "%+.2f%% nad szczytem" % ((float(entry_doc.get("price") or 0) / float(rng["high"]) - 1) * 100)
    except (TypeError, ValueError, ZeroDivisionError):
        pct_over = ""
    book.decide(
        sim, "open", symbol=sym,
        title="Kupilem %s %s" % (int(qty), sym),
        why=("Cena przebila poranny szczyt (%s) i zamknela sie nad nim. "
             "Stop chroni mnie %.0f%% nizej, cel jest tak samo daleko jak stop."
             % (pct_over or "zakres 15 min",
                (1 - float(plan.get("stop") or 0) / max(fill, 0.01)) * 100)),
        numbers={
            "qty": int(qty), "entry": round(fill, 2), "stop": plan.get("stop"),
            "target": plan.get("target"), "risk_share": plan.get("risk_per_share"),
            "max_loss": passed.get("max_loss"), "rr": passed.get("reward_risk"),
            "range_high": rng.get("high"), "range_low": rng.get("low"),
            "trigger": entry_doc.get("time"), "news": gate.get("count") or 0,
        },
    )
    return {"symbol": sym, "qty": qty, "fill": round(fill, 4), "plan": plan}


def log_daily_news_summary(sim: dict) -> None:
    """Na koniec dnia: ile lacznie przeczytal i czy to zmienilo decyzje."""
    t = news.today()
    n = int(t.get("read") or 0)
    if not n:
        return
    blocked = int(t.get("blocked") or 0)
    book.decide(
        sim, "news_summary",
        title="Dzisiaj przeczytalem %d naglowkow" % n,
        why=("Zadnego nie uznalem za wystarczajacy powod, zeby zmienic plan."
             if not blocked else
             "%d raz(y) wiadomosci wstrzymaly zakup - to tez jest decyzja." % blocked),
        read=n, risk=blocked,
    )

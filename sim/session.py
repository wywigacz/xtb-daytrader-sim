"""Zegar giełdy USA w czasie Nowego Jorku. Tylko biblioteka standardowa.

Sesja: 9:30-16:00 ET (w dni skrocone 13:00 ET). Weekendy i święta NYSE zamknięte.
Uzywane przez cały silnik: tick srodzienny, rozliczenie dzienne, flat-by.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import os

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Swieta NYSE 2026-2027 (zrodlo: nyse.com). Format ISO.
HOLIDAYS = {
    # 2026
    "2026-01-01",  # Nowy Rok
    "2026-01-19",  # Martin Luther King
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Wielki Piatek
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Dzien Niepodleglosci (obchodzony, 4.07 = sobota)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Boze Narodzenie
    # 2027
    "2027-01-01",
    "2027-01-18",
    "2027-02-15",
    "2027-03-26",  # Wielki Piatek
    "2027-05-31",  # Memorial Day
    "2027-06-18",  # Juneteenth (obchodzony, 19.06 = sobota)
    "2027-07-05",  # Dzien Niepodleglosci (obchodzony, 4.07 = niedziela)
    "2027-09-06",  # Labor Day
    "2027-11-25",  # Thanksgiving
    "2027-12-24",  # Boze Narodzenie (obchodzone, 25.12 = sobota)
}

# Dni z zamknieciem o 13:00 ET
EARLY_CLOSE = {
    "2026-11-27",  # po Thanksgiving
    "2026-12-24",  # wigilia
    "2027-11-26",  # po Thanksgiving
}

OPEN_TIME = time(9, 30)
CLOSE_TIME = time(16, 0)
EARLY_CLOSE_TIME = time(13, 0)


def now_ny(now: datetime | None = None) -> datetime:
    """Teraz w Nowym Jorku (albo podany moment, jesli naiwny -> traktowany jako NY).

    Zmienna srodowiskowa SIM_NOW (format "YYYY-MM-DD HH:MM", czas NY) pozwala
    'zamrozic' zegar - uzywane do testów i odtwarzania sesji.
    Poza testami: ustawiana przez tick.py/daily.py z argumentu --now.
    """
    if now is None:
        pin = os.environ.get("SIM_NOW")
        if pin:
            try:
                return datetime.strptime(pin, "%Y-%m-%d %H:%M").replace(tzinfo=NY)
            except ValueError:
                pass
        return datetime.now(NY)
    if now.tzinfo is None:
        return now.replace(tzinfo=NY)
    return now.astimezone(NY)


def to_ny(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=NY)


def is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d.isoformat() not in HOLIDAYS


def close_time(d: date) -> time:
    return EARLY_CLOSE_TIME if d.isoformat() in EARLY_CLOSE else CLOSE_TIME


def session_bounds(d: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(d, OPEN_TIME, tzinfo=NY),
        datetime.combine(d, close_time(d), tzinfo=NY),
    )


def is_open(now: datetime | None = None) -> bool:
    n = now_ny(now)
    if not is_trading_day(n.date()):
        return False
    o, c = session_bounds(n.date())
    return o <= n < c


def is_rth_before(now: datetime | None = None) -> bool:
    """Przed otwarciem tego samego dnia (pre-market)."""
    n = now_ny(now)
    if not is_trading_day(n.date()):
        return False
    o, _ = session_bounds(n.date())
    return n < o


def next_open(now: datetime | None = None) -> datetime:
    n = now_ny(now)
    d = n.date()
    for _ in range(15):
        if is_trading_day(d):
            o, c = session_bounds(d)
            if n < o:
                return o
            if n < c:
                return o  # juz otwarte
        d = d + timedelta(days=1)
    return n


def minutes_since_open(now: datetime | None = None) -> float:
    n = now_ny(now)
    o, _ = session_bounds(n.date())
    return (n - o).total_seconds() / 60.0


def flat_by(d: date, flat_by_hhmm: str = "15:55") -> datetime:
    """Moment 'flat by': na skroconym dniu 3 godziny wczesniej."""
    h, m = (int(x) for x in flat_by_hhmm.split(":"))
    dt = datetime.combine(d, time(h, m), tzinfo=NY)
    if d.isoformat() in EARLY_CLOSE:
        dt = dt - timedelta(hours=3)
    return dt


def iso_day(d: date | datetime) -> str:
    return d.strftime("%Y-%m-%d")


def label_ny(now: datetime | None = None) -> str:
    return now_ny(now).strftime("%Y-%m-%d %H:%M ET")


if __name__ == "__main__":  # szybki podglad
    n = now_ny()
    print("Teraz w NY:", label_ny(n))
    print("Dzień handlowy:", is_trading_day(n.date()))
    print("Sesja otwarta:", is_open(n))
    print("Nastepne otwarcie:", next_open(n).isoformat())
    print("Flat by:", flat_by(n.date()).isoformat())

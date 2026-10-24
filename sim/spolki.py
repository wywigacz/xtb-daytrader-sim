"""Katalog spółek: nazwa i kategoria, żeby panel mówił CO to za spółki.

Dane w `data/spolki.csv` (symbol,nazwa,kategoria). Plik można edytować bez
dotykania kodu. Brak wpisu nie jest błędem — pokazujemy wtedy sam symbol.
"""
from __future__ import annotations

from . import store

_CACHE: dict[str, dict] | None = None


def load() -> dict[str, dict]:
    """{SYMBOL: {'nazwa': ..., 'kategoria': ...}}"""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    out: dict[str, dict] = {}
    try:
        for r in store.read_csv(store.SPOLKI):
            sym = str(r.get("symbol") or "").strip().upper()
            if sym:
                out[sym] = {"nazwa": (r.get("nazwa") or sym).strip(),
                            "kategoria": (r.get("kategoria") or "Inne").strip()}
    except Exception:  # noqa: BLE001 - brak katalogu nie moze przewrocic panelu
        pass
    _CACHE = out
    return out


def nazwa(symbol: str) -> str:
    return load().get(str(symbol or "").upper(), {}).get("nazwa") or str(symbol or "").upper()


def kategoria(symbol: str) -> str:
    return load().get(str(symbol or "").upper(), {}).get("kategoria") or "Inne"


def watchlist() -> list[str]:
    """Symbole z universe.txt (kolejnosc zachowana)."""
    try:
        with open(store.UNIVERSE, encoding="utf-8") as f:
            return [l.strip().upper() for l in f if l.strip() and not l.startswith("#")]
    except OSError:
        return []


def grupy(symbole: list[str]) -> list[tuple[str, list[str]]]:
    """Grupuje symbole po kategorii, kategorie alfabetycznie."""
    buckets: dict[str, list[str]] = {}
    for s in symbole:
        buckets.setdefault(kategoria(s), []).append(s)
    return sorted(buckets.items())

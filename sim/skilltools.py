"""Uruchamianie narzędzi skilla day-trader-skill jako podprocesow.

Cala logika skanowania, planu wyjścia, wielkości pozycji i kontroli ryzyka
pochodzi z oryginalnego skilla (folder ../skills). Tu tylko go wywolujemy
z katalogu glownego repo, żeby narzędzia czytaly i pisaly pliki w trader/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from . import store

SKILLS = store.p(store.ROOT, "skills")

TOOL = {
    "scan": "trader-scanner/scan.py",
    "entry": "trader-entry/entry.py",
    "exit": "trader-exit/exit.py",
    "size": "trader-budget/size.py",
    "check": "trader-risk/check.py",
    "ticket": "trader-broker/ticket.py",
    "alerts": "trader-alerts/alerts.py",
    "news": "trader-news/news.py",
    "analyst": "trader-analyst/facts.py",
    "timemachine": "trader-timemachine/timemachine.py",
}


class SkillError(RuntimeError):
    def __init__(self, msg, rc=None, out="", err=""):
        super().__init__(msg)
        self.rc, self.out, self.err = rc, out, err


def run(tool: str, args: list[str], timeout: int = 300) -> tuple[int, str, str]:
    script = store.p(SKILLS, TOOL[tool])
    if not os.path.exists(script):
        raise SkillError("brak narzędzia skilla: %s" % script)
    cmd = [sys.executable, script] + [str(a) for a in args]
    pr = subprocess.run(
        cmd, cwd=store.ROOT, capture_output=True, text=True, timeout=timeout
    )
    return pr.returncode, pr.stdout, pr.stderr


def extract_json(text: str):
    """Wyciaga największy obiekt JSON z tekstu (narzędzia dopisuja linie postępu)."""
    best = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict):
            if best is None or len(json.dumps(obj)) > len(json.dumps(best)):
                best = obj
    return best


def extract_json_list(text: str) -> list | None:
    """Jak extract_json, ale dla narzedzi zwracajacych LISTE obiektow.

    Uwaga: extract_json() celowo przyjmuje tylko obiekt {...}, wiec narzedzie
    zwracajace liste (np. trader-analyst facts.py) dawaloby None - cicho i bez
    bledu. Stad osobna funkcja.
    """
    best, best_score = None, -1
    for i, ch in enumerate(text or ""):
        if ch != "[":
            continue
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[i:])
        except ValueError:
            continue
        if not isinstance(obj, list):
            continue
        # nie bierzemy "najdluzszej" listy: w wyjsciu narzedzia bywaja inne
        # tablice (postep, listy pol). Najpierw lista slownikow z "ticker".
        score = 0
        if obj and all(isinstance(x, dict) for x in obj):
            score = 2 + (1 if any("ticker" in x for x in obj) else 0)
        score = score * 1000 + len(obj)
        if score > best_score:
            best, best_score = obj, score
    return best


def json_run(tool: str, args: list[str], timeout: int = 300) -> tuple[int, dict | None, str]:
    rc, out, err = run(tool, list(args) + ["--json"], timeout=timeout)
    return rc, extract_json(out), (err or out).strip()


def list_run(tool: str, args: list[str], timeout: int = 300) -> tuple[int, list | None, str]:
    """Wariant json_run dla narzedzi zwracajacych liste."""
    rc, out, err = run(tool, list(args) + ["--json"], timeout=timeout)
    return rc, extract_json_list(out), (err or out).strip()

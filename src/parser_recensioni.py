"""
parser_recensioni.py
====================
Legge il file delle recensioni SCARICATO da Booking (pulsante "Scarica le recensioni")
e ne ricava: voto medio, numero di recensioni ed (se disponibili) le date.

Gestisce sia file .csv sia .xlsx. Non conosciamo in anticipo i nomi ESATTI delle
colonne di Booking, quindi il lettore prova a riconoscerle da parole chiave
(punteggio/voto/score, data/date). Quando gira, STAMPA quale colonna ha usato,
cosi' e' facile verificare che sia quella giusta.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

# Parole chiave per riconoscere le colonne (in italiano e inglese).
CHIAVI_VOTO = ["punteggio", "voto", "score", "rating", "valutazione", "review score"]
CHIAVI_DATA = ["data", "date", "soggiorno", "check", "recensione il", "reviewed"]


@dataclass
class RisultatoFile:
    voto_medio: float | None
    num_recensioni: int
    colonna_voto_usata: str | None = None
    date: list[str] = field(default_factory=list)


def _righe_da_csv(path: Path) -> list[dict]:
    """Legge un CSV riconoscendo da solo il separatore (virgola o punto e virgola)."""
    testo = path.read_text(encoding="utf-8-sig", errors="replace")
    # Provo a indovinare il separatore guardando la prima riga.
    prima = testo.splitlines()[0] if testo.splitlines() else ""
    sep = ";" if prima.count(";") >= prima.count(",") else ","
    lettore = csv.DictReader(io.StringIO(testo), delimiter=sep)
    return [dict(r) for r in lettore]


def _righe_da_xlsx(path: Path) -> list[dict]:
    """Legge un Excel .xlsx usando openpyxl (prima scheda)."""
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise RuntimeError(
            "Per leggere i file Excel serve 'openpyxl'. Installa con:\n"
            "  pip3 install openpyxl"
        ) from e
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    righe_iter = ws.iter_rows(values_only=True)
    intestazioni = [str(c).strip() if c is not None else "" for c in next(righe_iter, [])]
    out: list[dict] = []
    for valori in righe_iter:
        riga = {intestazioni[i]: valori[i] for i in range(min(len(intestazioni), len(valori)))}
        out.append(riga)
    return out


def _trova_colonna(intestazioni: list[str], chiavi: list[str]) -> str | None:
    """Trova la prima intestazione che contiene una delle parole chiave."""
    for h in intestazioni:
        basso = (h or "").lower()
        if any(k in basso for k in chiavi):
            return h
    return None


def _a_numero(valore) -> float | None:
    """Converte '8,5' o '9.0' o 8 in numero. None se non e' un numero."""
    if valore is None:
        return None
    if isinstance(valore, (int, float)):
        return float(valore)
    testo = str(valore).strip().replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", testo)
    return float(m.group(0)) if m else None


def analizza_file(path: Path) -> RisultatoFile:
    """Legge il file scaricato e calcola voto medio e numero recensioni."""
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        righe = _righe_da_xlsx(path)
    else:
        righe = _righe_da_csv(path)

    if not righe:
        return RisultatoFile(voto_medio=None, num_recensioni=0)

    intestazioni = list(righe[0].keys())
    col_voto = _trova_colonna(intestazioni, CHIAVI_VOTO)
    col_data = _trova_colonna(intestazioni, CHIAVI_DATA)

    voti: list[float] = []
    date: list[str] = []
    for r in righe:
        if col_voto is not None:
            n = _a_numero(r.get(col_voto))
            if n is not None:
                voti.append(n)
        if col_data is not None and r.get(col_data):
            date.append(str(r.get(col_data)).strip())

    voto_medio = round(sum(voti) / len(voti), 2) if voti else None
    return RisultatoFile(
        voto_medio=voto_medio,
        num_recensioni=len(voti) if voti else len(righe),
        colonna_voto_usata=col_voto,
        date=date,
    )

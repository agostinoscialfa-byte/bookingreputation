"""
storage.py
==========
Si occupa di SALVARE e LEGGERE lo storico dei punteggi.

Idea semplice: ogni giorno salviamo una riga per ogni struttura
(una "fotografia"). Tutte le righe stanno in un unico file: data/history.csv

Cosi' possiamo confrontare "oggi" con "7 giorni fa" e disegnare il grafico.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

# Cartella dove teniamo i dati. E' accanto a questo file, un livello sopra (../data).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FILE = DATA_DIR / "history.csv"

# Le colonne del file storico, in ordine.
CAMPI = ["date", "property_id", "property_name", "score", "num_reviews"]


@dataclass
class Snapshot:
    """Una singola 'fotografia': il voto di UNA struttura in UN giorno."""
    date: str            # formato AAAA-MM-GG, es. "2026-09-15"
    property_id: str
    property_name: str
    score: float         # voto Booking, scala 1-10 (es. 8.7)
    num_reviews: int     # numero totale di recensioni


def _assicura_cartella() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def leggi_storico() -> list[Snapshot]:
    """Legge tutte le fotografie salvate finora. Se non c'e' nulla, lista vuota."""
    if not HISTORY_FILE.exists():
        return []
    righe: list[Snapshot] = []
    with HISTORY_FILE.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            righe.append(
                Snapshot(
                    date=r["date"],
                    property_id=r["property_id"],
                    property_name=r["property_name"],
                    score=float(r["score"]),
                    num_reviews=int(r["num_reviews"]),
                )
            )
    return righe


def salva_snapshot(nuovi: list[Snapshot]) -> None:
    """
    Aggiunge le fotografie di OGGI allo storico.
    Se per una struttura c'e' gia' una riga con la stessa data, la SOSTITUISCE
    (cosi' se lanci il programma due volte nello stesso giorno non hai doppioni).
    """
    _assicura_cartella()
    esistenti = leggi_storico()

    # Chiave = (data, id struttura). Uso un dizionario per eliminare i doppioni.
    per_chiave: dict[tuple[str, str], Snapshot] = {
        (s.date, s.property_id): s for s in esistenti
    }
    for s in nuovi:
        per_chiave[(s.date, s.property_id)] = s

    # Riscrivo tutto il file, ordinato per data e poi per struttura.
    ordinati = sorted(per_chiave.values(), key=lambda s: (s.date, s.property_id))
    with HISTORY_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPI)
        w.writeheader()
        for s in ordinati:
            w.writerow(asdict(s))


def oggi_iso() -> str:
    """Data di oggi come testo 'AAAA-MM-GG'."""
    return date.today().isoformat()


def snapshot_piu_recenti() -> dict[str, Snapshot]:
    """Per ogni struttura, restituisce l'ultima fotografia disponibile."""
    ultimo: dict[str, Snapshot] = {}
    for s in sorted(leggi_storico(), key=lambda s: s.date):
        ultimo[s.property_id] = s  # continuo a sovrascrivere: resta il piu' recente
    return ultimo


def snapshot_di_circa_giorni_fa(property_id: str, giorni: int = 7) -> Snapshot | None:
    """
    Trova la fotografia piu' vicina a 'giorni' giorni fa per una struttura.
    Serve per il confronto "come andiamo rispetto alla settimana scorsa".
    """
    storico = [s for s in leggi_storico() if s.property_id == property_id]
    if not storico:
        return None

    oggi = datetime.strptime(oggi_iso(), "%Y-%m-%d").date()
    bersaglio = oggi - timedelta(days=giorni)

    # Prendo la fotografia con la data piu' vicina al giorno bersaglio,
    # ma non piu' recente di 'oggi meno 1 giorno' (vogliamo il passato).
    candidati = [
        s for s in storico
        if datetime.strptime(s.date, "%Y-%m-%d").date() <= bersaglio
    ]
    if not candidati:
        # Non abbiamo dati vecchi abbastanza: prendo comunque il piu' vecchio che ho.
        candidati = storico
    return min(
        candidati,
        key=lambda s: abs((datetime.strptime(s.date, "%Y-%m-%d").date() - bersaglio).days),
    )

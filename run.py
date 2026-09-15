#!/usr/bin/env python3
"""
run.py  -  Il programma principale.
===================================
Usalo dal terminale cosi':

  python3 run.py demo        -> crea dati FINTI e apre il cruscotto (per provare subito)
  python3 run.py scrape      -> entra in Booking, legge i voti e li salva nello storico
  python3 run.py dashboard   -> rigenera SOLO il cruscotto dai dati gia' salvati
  python3 run.py giornaliero -> fa tutto: scarica da Booking + salva + cruscotto (uso quotidiano)

Prima di 'scrape'/'giornaliero':
  1) copia .env.example in .env e metti le tue credenziali Booking
  2) copia config.example.json in config.json (opzionale, per i nomi delle strutture)
  3) pip3 install -r requirements.txt
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Rende importabili i moduli dentro 'src'
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src import storage, dashboard  # noqa: E402


def carica_config() -> dict:
    """Legge config.json se esiste, altrimenti config.example.json, altrimenti valori base."""
    for nome in ("config.json", "config.example.json"):
        f = BASE / nome
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    return {"login": {}, "previsione": {}, "strutture": []}


def carica_env() -> None:
    """Carica le variabili dal file .env (senza librerie esterne)."""
    import os
    env = BASE / ".env"
    if not env.exists():
        return
    for riga in env.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, _, valore = riga.partition("=")
        os.environ.setdefault(chiave.strip(), valore.strip())


def comando_demo() -> None:
    """Crea 3 settimane di dati finti per 2 strutture, cosi' vedi il cruscotto pieno."""
    print("Creo dati DEMO (finti) per farti vedere il cruscotto...")
    config = carica_config()
    strutture = config.get("strutture") or [
        {"id": "struttura-1", "nome": "Hotel Demo Mare"},
        {"id": "struttura-2", "nome": "Hotel Demo Città"},
    ]
    snapshots = []
    for s in strutture[:2] if len(strutture) >= 2 else strutture:
        base_voto = random.uniform(8.4, 9.1)
        base_rec = random.randint(180, 900)
        # 21 giorni di storico, con piccole variazioni realistiche.
        for g in range(21, -1, -1):
            giorno = (date.today() - timedelta(days=g)).isoformat()
            voto = round(base_voto + random.uniform(-0.05, 0.05) + (21 - g) * 0.004, 2)
            rec = base_rec + (21 - g) * random.randint(0, 2)
            snapshots.append(storage.Snapshot(giorno, s["id"], s["nome"], voto, rec))
    storage.salva_snapshot(snapshots)
    percorso = dashboard.genera_html(config)
    print(f"Fatto! Dati demo salvati e cruscotto creato:\n  {percorso}")
    print("Aprilo con doppio clic (o dal browser).")


def comando_scrape(genera_anche_dashboard: bool = False) -> None:
    """Entra in Booking e salva i voti di oggi nello storico."""
    carica_env()
    from src import booking_scraper  # import qui: serve playwright solo per questo comando
    config = carica_config()
    print("Mi collego a Booking (admin.booking.com)...")
    try:
        nuovi = booking_scraper.raccogli_dati(config)
    except booking_scraper.ScraperError as e:
        print("\n--- PROBLEMA DURANTE LA RACCOLTA ---")
        print(e)
        print("\nSuggerimento: la prima volta metti BOOKING_HEADLESS=false nel file .env")
        print("cosi' vedi il browser lavorare, e controlla la cartella data/debug/.")
        sys.exit(1)
    storage.salva_snapshot(nuovi)
    print(f"Salvate {len(nuovi)} fotografie nello storico.")
    if genera_anche_dashboard:
        percorso = dashboard.genera_html(config)
        print(f"Cruscotto aggiornato: {percorso}")


def comando_dashboard() -> None:
    config = carica_config()
    percorso = dashboard.genera_html(config)
    print(f"Cruscotto rigenerato dai dati salvati:\n  {percorso}")


def main() -> None:
    comando = sys.argv[1] if len(sys.argv) > 1 else "aiuto"
    if comando == "demo":
        comando_demo()
    elif comando == "scrape":
        comando_scrape(genera_anche_dashboard=False)
    elif comando == "dashboard":
        comando_dashboard()
    elif comando == "giornaliero":
        comando_scrape(genera_anche_dashboard=True)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

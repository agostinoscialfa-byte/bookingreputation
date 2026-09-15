#!/usr/bin/env python3
"""
run.py  -  Il programma principale.
===================================
Usalo dal terminale cosi':

  python3 run.py demo        -> crea dati FINTI e apre il cruscotto (per provare subito)
  python3 run.py test        -> prova UNA sola struttura (per il primo test del login)
  python3 run.py scrape      -> entra in Booking, legge i voti e li salva nello storico
  python3 run.py dashboard   -> rigenera SOLO il cruscotto dai dati gia' salvati
  python3 run.py giornaliero -> fa tutto: scarica da Booking + salva + cruscotto (uso quotidiano)

Prima di 'scrape'/'giornaliero':
  1) copia .env.example in .env e metti le tue credenziali Booking
  2) copia config.example.json in config.json (opzionale, per i nomi delle strutture)
  3) pip3 install -r requirements.txt
"""

from __future__ import annotations

import csv
import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Rende importabili i moduli dentro 'src'
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src import storage, dashboard, modello_booking  # noqa: E402


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


def _genera_csv_finto(hotel_id: str, n: int, trend: float) -> Path:
    """Crea un file recensioni finto (come l'export Booking) e lo salva in data/downloads/."""
    download_dir = storage.DATA_DIR / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    oggi = datetime.now()

    def voto(base):
        return max(4, min(10, round(random.gauss(base, 1.2))))

    righe = []
    for _ in range(n):
        giorni_fa = random.randint(0, 720)
        d = oggi - timedelta(days=giorni_fa)
        # Le recensioni recenti hanno un voto medio un filo diverso (trend +/-).
        base = 8.7 + (720 - giorni_fa) / 720 * trend
        righe.append({
            "Nome struttura": hotel_id,
            "Data della recensione": d.strftime("%Y-%m-%d"),
            "Punteggio della recensione": str(voto(base)).replace(".", ","),
            "Pulizia": voto(base + 0.1),
            "Staff": voto(base + 0.3),
            "Comfort": voto(base - 0.1),
            "Servizi": voto(base - 0.2),
            "Posizione": voto(base + 0.5),
            "Qualità/prezzo": voto(base - 0.3),
        })
    percorso = download_dir / f"{date.today().isoformat()}_{hotel_id}.csv"
    with percorso.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(righe[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(righe)
    return percorso


def comando_demo() -> None:
    """Crea recensioni finte + storico per 2 strutture, cosi' vedi il cruscotto pieno."""
    print("Creo dati DEMO (finti) per farti vedere il cruscotto...")
    config = carica_config()
    # La demo usa SEMPRE strutture chiaramente finte, per non confondersi con i dati veri.
    valide = [
        {"id": "demo-mare", "nome": "Hotel Demo Mare (esempio)", "hotel_id": "999001"},
        {"id": "demo-citta", "nome": "Hotel Demo Città (esempio)", "hotel_id": "999002"},
    ]

    snapshots = []
    for idx, s in enumerate(valide):
        hotel_id = str(s["hotel_id"])
        trend = 0.6 if idx == 0 else -0.4  # una sale, una scende, per far vedere entrambi
        n = random.randint(220, 480)
        csv_path = _genera_csv_finto(hotel_id, n, trend)

        # Ricostruisco lo storico degli ultimi 21 giorni applicando il modello "a quel giorno".
        recensioni, _ = modello_booking.carica_recensioni(csv_path)
        for g in range(21, -1, -1):
            D = datetime.now() - timedelta(days=g)
            sub = [r for r in recensioni if r.d <= D]
            if len(sub) < 5:
                continue
            calc = modello_booking.ewma(sub, D)
            w3 = modello_booking.media_finestra(sub, 90) or modello_booking.media_finestra(sub, 180)
            pace = w3[0] if w3 else calc
            recenti = [r for r in sub if r.d >= D - timedelta(days=180)]
            rate = max(1, round(len(recenti) / 6))
            snapshots.append(storage.Snapshot(
                D.date().isoformat(), s["id"], s["nome"],
                round(calc, 2), len(sub), round(pace, 2), rate,
            ))

    storage.salva_snapshot(snapshots)
    percorso = dashboard.genera_html({"strutture": valide, "previsione": config.get("previsione", {})})
    print(f"Fatto! Dati demo salvati e cruscotto creato:\n  {percorso}")
    print("Aprilo con doppio clic (o dal browser).")


def comando_scrape(genera_anche_dashboard: bool = False, solo_prima: bool = False) -> None:
    """Entra in Booking e salva i voti di oggi nello storico."""
    carica_env()
    from src import booking_scraper  # import qui: serve playwright solo per questo comando
    config = carica_config()
    if solo_prima:
        # Modalita' TEST: provo solo la prima struttura valida.
        valide = [s for s in config.get("strutture", [])
                  if s.get("hotel_id") and "METTI" not in str(s.get("hotel_id"))]
        config = {**config, "strutture": valide[:1]}
        nome = valide[0]["nome"] if valide else "?"
        print(f"MODALITA' TEST: provo solo '{nome}'.")
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
    elif comando == "test":
        comando_scrape(genera_anche_dashboard=True, solo_prima=True)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

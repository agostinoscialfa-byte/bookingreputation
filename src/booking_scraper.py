"""
booking_scraper.py
==================
Entra nell'Extranet di Booking (admin.booking.com) e legge, per ogni struttura,
il voto (review score) e il numero di recensioni.

IMPORTANTE / ONESTO:
Booking cambia ogni tanto l'aspetto delle sue pagine, quindi i "selettori"
(cioe' il modo con cui troviamo pulsanti e testi) possono richiedere piccole
correzioni. Per questo il programma:
  - la PRIMA volta e' meglio lanciarlo con browser VISIBILE (BOOKING_HEADLESS=false)
  - salva SEMPRE uno screenshot e l'HTML di ogni pagina in data/debug/
Cosi', se qualcosa non torna, si vede subito dove intervenire.

Questo file usa Playwright (sync). Non tocca nulla su Booking: solo LEGGE.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from .storage import Snapshot, oggi_iso, DATA_DIR

DEBUG_DIR = DATA_DIR / "debug"

# Percorso del browser gia' installato in questo ambiente (se presente).
_BROWSERS = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
_CHROMIUM = f"{_BROWSERS}/chromium" if _BROWSERS and Path(f"{_BROWSERS}/chromium").exists() else None


class ScraperError(Exception):
    """Errore 'gentile' con messaggio comprensibile per l'utente."""


def _salva_debug(page: Page, nome: str) -> None:
    """Salva screenshot + HTML della pagina, per capire cosa vede il programma."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{nome}.png"), full_page=True)
        (DEBUG_DIR / f"{nome}.html").write_text(page.content(), encoding="utf-8")
    except Exception as e:  # il debug non deve mai far crashare il programma
        print(f"  (nota: non sono riuscito a salvare il debug '{nome}': {e})")


def _prova_a_riempire(page: Page, selettori: list[str], valore: str) -> bool:
    """Prova piu' selettori finche' uno funziona. Restituisce True se riesce."""
    for sel in selettori:
        try:
            campo = page.locator(sel).first
            if campo.count() > 0:
                campo.fill(valore, timeout=5000)
                return True
        except Exception:
            continue
    return False


def _prova_a_cliccare(page: Page, selettori: list[str]) -> bool:
    for sel in selettori:
        try:
            bottone = page.locator(sel).first
            if bottone.count() > 0:
                bottone.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def _login(page: Page, username: str, password: str, start_url: str) -> None:
    """Esegue il login con email + password (Booking di solito lo fa in due passi)."""
    print(f"  Apro {start_url} ...")
    page.goto(start_url, wait_until="domcontentloaded", timeout=60000)
    _salva_debug(page, "01_login_iniziale")

    # Passo 1: inserisci username/email e vai avanti.
    ok = _prova_a_riempire(page, [
        'input[name="username"]',
        'input[name="loginname"]',
        'input#username',
        'input[type="email"]',
        'input[autocomplete="username"]',
    ], username)
    if not ok:
        raise ScraperError(
            "Non ho trovato il campo dove scrivere l'email/utente nella pagina di login.\n"
            "  Guarda lo screenshot in data/debug/01_login_iniziale.png per capire com'e' fatta la pagina."
        )
    _prova_a_cliccare(page, [
        'button[type="submit"]',
        'button:has-text("Avanti")',
        'button:has-text("Next")',
        'button:has-text("Continua")',
    ])
    page.wait_for_timeout(1500)
    _salva_debug(page, "02_dopo_username")

    # Passo 2: inserisci la password e conferma.
    ok = _prova_a_riempire(page, [
        'input[name="password"]',
        'input#password',
        'input[type="password"]',
        'input[autocomplete="current-password"]',
    ], password)
    if not ok:
        raise ScraperError(
            "Non ho trovato il campo password.\n"
            "  Guarda data/debug/02_dopo_username.png. Se Booking ha chiesto un CODICE (2FA),\n"
            "  l'automazione da sola non puo' proseguire: dimmelo e troviamo un'alternativa."
        )
    _prova_a_cliccare(page, [
        'button[type="submit"]',
        'button:has-text("Accedi")',
        'button:has-text("Sign in")',
        'button:has-text("Log in")',
        'button:has-text("Entra")',
    ])
    page.wait_for_timeout(3000)
    _salva_debug(page, "03_dopo_login")

    # Controllo grezzo: se vedo ancora un campo password, il login e' fallito.
    if page.locator('input[type="password"]').count() > 0:
        raise ScraperError(
            "Il login sembra non essere andato a buon fine (vedo ancora la password).\n"
            "  Possibili cause: password sbagliata, oppure Booking ha chiesto un codice di verifica (2FA).\n"
            "  Controlla data/debug/03_dopo_login.png."
        )
    print("  Login effettuato (nessun campo password residuo).")


# Cerca un voto Booking nel testo: un numero tra 1 e 10 con un decimale (es. 8,7 o 9.1)
_RE_VOTO = re.compile(r"\b(10(?:[.,]0)?|[1-9](?:[.,]\d)?)\b")
# Cerca un numero di recensioni (es. "1.234 recensioni", "532 reviews")
_RE_RECENSIONI = re.compile(r"([\d.\s]{1,7})\s*(?:recension|review)", re.IGNORECASE)


def _estrai_voto_e_recensioni(page: Page) -> tuple[float | None, int | None]:
    """
    Prova a leggere voto e numero recensioni dalla pagina 'recensioni'.
    Ritorna (voto, num_recensioni). Se non trova, None.
    Nota: e' un'euristica; con la pagina vera possiamo renderla precisa.
    """
    testo = page.inner_text("body")

    voto = None
    # Cerco vicino a parole come "punteggio"/"score" per non pescare numeri a caso.
    for riga in testo.splitlines():
        if re.search(r"punteggio|review score|voto|score", riga, re.IGNORECASE):
            m = _RE_VOTO.search(riga)
            if m:
                voto = float(m.group(1).replace(",", "."))
                break
    if voto is None:  # ripiego: primo numero "da voto" nel testo
        m = _RE_VOTO.search(testo)
        if m:
            voto = float(m.group(1).replace(",", "."))

    recensioni = None
    m = _RE_RECENSIONI.search(testo)
    if m:
        pulito = re.sub(r"[.\s]", "", m.group(1))
        if pulito.isdigit():
            recensioni = int(pulito)

    return voto, recensioni


def _cattura_ses(page: Page) -> str | None:
    """
    Dopo il login, l'URL di Booking contiene un codice di sessione 'ses=...'.
    Lo catturiamo per riusarlo quando apriamo la pagina recensioni di ogni hotel.
    """
    m = re.search(r"[?&]ses=([0-9a-zA-Z]+)", page.url)
    return m.group(1) if m else None


def _url_recensioni(start_url: str, reviews_path: str, hotel_id: str,
                    lang: str, ses: str | None) -> str:
    """Costruisce l'indirizzo della pagina recensioni per uno specifico hotel_id."""
    base = start_url.rstrip("/")
    percorso = reviews_path.lstrip("/")
    url = f"{base}/{percorso}?hotel_id={hotel_id}&lang={lang}"
    if ses:
        url += f"&ses={ses}"
    return url


def raccogli_dati(config: dict) -> list[Snapshot]:
    """
    Funzione principale: fa login, legge i dati e restituisce le fotografie di oggi.
    Le credenziali arrivano dalle variabili d'ambiente (file .env).
    """
    username = os.environ.get("BOOKING_USERNAME", "").strip()
    password = os.environ.get("BOOKING_PASSWORD", "").strip()
    if not username or not password:
        raise ScraperError(
            "Mancano le credenziali. Crea il file .env (copia da .env.example) con\n"
            "  BOOKING_USERNAME e BOOKING_PASSWORD."
        )

    headless = os.environ.get("BOOKING_HEADLESS", "false").strip().lower() == "true"
    login_cfg = config.get("login", {})
    start_url = login_cfg.get("start_url", "https://admin.booking.com/")
    reviews_path = login_cfg.get("reviews_path", "hotel/hoteladmin/extranet_ng/manage/reviews.html")
    lang = login_cfg.get("lang", "it")

    # Le strutture da leggere: servono id, nome e hotel_id.
    strutture = [
        s for s in config.get("strutture", [])
        if s.get("hotel_id") and "METTI" not in str(s.get("hotel_id", ""))
    ]
    if not strutture:
        raise ScraperError(
            "Nel config non ci sono strutture con un 'hotel_id' valido.\n"
            "  Copia config.example.json in config.json e metti gli hotel_id delle tue strutture\n"
            "  (li trovi nell'URL della pagina recensioni: ...reviews.html?hotel_id=XXXXXX)."
        )

    risultati: list[Snapshot] = []
    with sync_playwright() as p:
        launch_kwargs = {"headless": headless}
        if _CHROMIUM:
            launch_kwargs["executable_path"] = _CHROMIUM
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="it-IT",
        )
        page = context.new_page()
        try:
            _login(page, username, password, start_url)
            ses = _cattura_ses(page)
            if ses:
                print(f"  Sessione catturata (ses) per riuso sulle pagine hotel.")

            # Giro su ogni struttura usando il suo hotel_id.
            for s in strutture:
                pid = s["id"]
                nome = s.get("nome", pid)
                hotel_id = str(s["hotel_id"])
                url = _url_recensioni(start_url, reviews_path, hotel_id, lang, ses)
                print(f"  Apro recensioni di '{nome}' (hotel_id={hotel_id})...")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2500)
                except PWTimeout:
                    print("  (nota: pagina lenta, provo a leggere comunque)")

                # Se il 'ses' era scaduto/assente, Booking potrebbe averlo rigenerato: riprovo a catturarlo.
                if not ses:
                    ses = _cattura_ses(page)

                _salva_debug(page, f"recensioni_{hotel_id}")

                voto, num = _estrai_voto_e_recensioni(page)
                if voto is None:
                    print(f"  ATTENZIONE: non ho trovato il voto per '{nome}'. "
                          f"Guarda data/debug/recensioni_{hotel_id}.png / .html.")
                    continue
                risultati.append(Snapshot(
                    date=oggi_iso(),
                    property_id=pid,
                    property_name=nome,
                    score=voto,
                    num_reviews=num if num is not None else 0,
                ))
                print(f"  OK '{nome}': voto {voto}, recensioni {num}")
        finally:
            context.close()
            browser.close()

    if not risultati:
        raise ScraperError(
            "Login riuscito ma non sono riuscito a LEGGERE nessun voto.\n"
            "  Apri i file in data/debug/ (le immagini recensioni_*.png): con quelli\n"
            "  possiamo sistemare in un attimo il punto giusto da cui leggere il voto."
        )
    return risultati

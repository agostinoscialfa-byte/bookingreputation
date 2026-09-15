# Cruscotto Reputazione Booking 📊

Un piccolo programma che ogni mattina:

1. **entra** nel tuo Extranet di Booking (`admin.booking.com`) con utente e password;
2. **legge** il voto (review score) e il numero di recensioni delle tue strutture;
3. **salva lo storico** giorno per giorno;
4. **genera un cruscotto** (una pagina web) dove vedi il voto, il confronto con la
   settimana scorsa e una **previsione**: "se tengo questo livello, dove va il mio voto?".

> Pensato per chi non è esperto: i comandi sono pochi e i commenti nel codice sono in italiano.

---

## 🚀 Prova subito (modalità demo, senza Booking)

Vuoi vedere com'è fatto il cruscotto prima di collegare Booking? Usa dati finti:

```bash
pip3 install -r requirements.txt        # solo la prima volta
python3 run.py demo
```

Poi apri il file che viene creato: **`data/dashboard.html`** (doppio clic).

---

## 🔐 Collegare il tuo Booking (dati veri)

### 1) Metti le tue credenziali
Copia il file di esempio e scrivici dentro email e password di Booking:

```bash
cp .env.example .env
```

Apri `.env` con un editor di testo e compila:
```
BOOKING_USERNAME=la-tua-email@esempio.com
BOOKING_PASSWORD=la-tua-password
BOOKING_HEADLESS=false     # false = vedi il browser lavorare (consigliato la 1ª volta)
```

> 🔒 Il file `.env` **non finisce mai su GitHub** (è nel `.gitignore`). Le password restano sul tuo computer.

### 2) (Opzionale) Dai un nome alle strutture
```bash
cp config.example.json config.json
```
Apri `config.json` e scrivi i nomi delle tue strutture e le ipotesi per la previsione
(quante recensioni prendi a settimana, con che voto medio, il voto obiettivo).

### 3) Installa il browser per l'automazione (solo la 1ª volta)
```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

### 4) Lancia la raccolta
```bash
python3 run.py giornaliero
```
Questo entra in Booking, salva i voti di oggi nello storico e aggiorna il cruscotto.

---

## 🗓️ Comandi disponibili

| Comando | Cosa fa |
|---|---|
| `python3 run.py demo` | Crea dati finti e genera il cruscotto (per provare). |
| `python3 run.py scrape` | Entra in Booking e salva i voti di oggi (senza rigenerare la pagina). |
| `python3 run.py dashboard` | Rigenera solo il cruscotto dai dati già salvati. |
| `python3 run.py giornaliero` | Fa tutto: Booking → storico → cruscotto. **Uso quotidiano.** |

---

## ⏰ Farlo partire "ogni mattina" da solo

**Sul tuo computer** puoi programmarlo:

- **Mac / Linux** (con `cron`): esegui `crontab -e` e aggiungi una riga per lanciarlo, es. ogni giorno alle 8:00:
  ```
  0 8 * * *  cd /percorso/della/cartella && /usr/bin/python3 run.py giornaliero
  ```
- **Windows**: usa l'**Utilità di pianificazione** (Task Scheduler) e imposta l'azione
  `python run.py giornaliero` nella cartella del progetto.

> Nota: perché parta da solo, il computer deve essere acceso a quell'ora.
> In alternativa si può far girare su un piccolo server sempre acceso: possiamo vederlo insieme più avanti.

---

## 🧠 Come viene calcolata la previsione (modello EWMA)

Non usiamo una media "piatta", ma una **media pesata sul tempo** (EWMA), che imita il modo in cui
Booking dà meno importanza alle recensioni vecchie:

- ogni recensione pesa di più se è recente; il peso **si dimezza ogni 6 mesi**;
- il **voto calcolato** è la media dei voti pesata così → stima ciò che Booking mostra;
- il **ritmo ultimi 3 mesi** (`pace`) è la media semplice degli ultimi 90 giorni: la qualità che tieni adesso;
- la **proiezione** simula i prossimi 24 mesi aggiungendo ogni mese `rate` nuove recensioni al voto `pace`
  e ricalcolando l'EWMA: così vedi *quando* il voto toccherà ogni "gradino" (8,4 → 8,5 → …).

Lo stesso modello viene applicato anche ai **sottoreparti** (Pulizia, Personale, Comfort, …).
È un'indicazione realistica, non una garanzia. Il "cervello" del calcolo è in `src/modello_booking.py`.

---

## 📁 Com'è organizzato il progetto

```
run.py                 → il programma principale (i comandi qui sopra)
config.example.json    → esempio di configurazione (copia in config.json)
.env.example           → esempio credenziali (copia in .env)
src/
  booking_scraper.py   → entra in Booking e legge i voti (Playwright)
  storage.py           → salva/legge lo storico (data/history.csv)
  forecast.py          → calcola la previsione
  dashboard.py         → genera la pagina web (data/dashboard.html)
data/                  → dati generati (storico, cruscotto, debug). Non va su GitHub.
```

## 🆘 Se qualcosa non funziona
Ogni volta che lo scraper gira, salva screenshot e pagine in **`data/debug/`**.
Se il login o la lettura del voto non riescono, apri quei file (soprattutto le `.png`):
si capisce subito dove intervenire e si aggiustano i "selettori" in `src/booking_scraper.py`.

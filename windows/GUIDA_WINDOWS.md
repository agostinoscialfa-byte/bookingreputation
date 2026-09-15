# Guida per Windows (passo-passo) 🪟

Obiettivo: far girare il programma **ogni mattina da solo** su un PC Windows sempre acceso.

Segui le 4 parti in ordine. La prima volta ci vuole ~15 minuti; poi non tocchi più nulla.

---

## Parte 1 — Installazioni (una volta sola)

### 1.1 Installa Python
1. Vai su **https://www.python.org/downloads/** e scarica Python (pulsante giallo).
2. Avvia l'installazione e **METTI LA SPUNTA su "Add Python to PATH"** (in basso), poi *Install Now*.
   > Questa spunta è importantissima: senza, i comandi non funzionano.

### 1.2 Scarica il progetto
Modo più semplice (senza installare altro):
1. Apri questa pagina (sei già loggato su GitHub): il repository `bookingreputation`, ramo
   `claude/booking-reputation-dashboard-5c70vn`.
2. Pulsante verde **"Code" → "Download ZIP"**.
3. Estrai lo ZIP, per esempio in `C:\bookingreputation` (tasto destro → *Estrai tutto*).

### 1.3 Installa tutto con un clic
Nella cartella del progetto entra in **`windows`** e fai **doppio clic su `installa.bat`**.
- Crea l'ambiente, scarica le librerie e il browser.
- Alla fine si apre il **Blocco Note** sul file `.env`: scrivi la tua **password Booking**
  al posto di quella di esempio, poi **Salva** (Ctrl+S) e chiudi.

Il file `.env` deve contenere:
```
BOOKING_USERNAME=ascialfa
BOOKING_PASSWORD=la-tua-password-vera
BOOKING_HEADLESS=false
```

---

## Parte 2 — Prova che funzioni
Doppio clic su **`windows\prova.bat`**.
- Si apre una finestra nera e **il browser** (visibile), che entra in Booking e legge **una** struttura.
- Se vedi scritto `OK 'Acquaderni Rooms': voto ...` → **funziona!** 🎉
- Se qualcosa non va, nella cartella `data\debug` trovi degli **screenshot**: mandameli e sistemiamo.

Per vedere il cruscotto completo apri il file **`data\dashboard.html`** (doppio clic).

---

## Parte 3 — Prova completa (tutte le 7 strutture)
Apri il *Prompt dei comandi* nella cartella del progetto e lancia una volta a mano:
```
windows\esegui_giornaliero.bat
```
(oppure aspetta la prima esecuzione automatica). Questo fa tutto in modalità nascosta e
aggiorna `data\dashboard.html`. Eventuali messaggi finiscono in `data\log_giornaliero.txt`.

---

## Parte 4 — Farlo partire ogni mattina da solo ⏰
Useremo l'**Utilità di pianificazione** di Windows (Task Scheduler).

1. Premi il tasto **Start**, scrivi **"Utilità di pianificazione"** e aprila.
2. A destra clicca **"Crea attività di base…"**.
3. **Nome:** `Reputazione Booking` → Avanti.
4. **Attivazione:** scegli **"Ogni giorno"** → Avanti. Imposta l'ora, es. **08:00** → Avanti.
5. **Azione:** *Avvio programma* → Avanti.
6. Nel campo **"Programma/script"** clicca **Sfoglia** e seleziona il file:
   `...\bookingreputation\windows\esegui_giornaliero.bat`
7. Avanti → **Fine**.

### Consiglio importante
Dopo aver creato l'attività, aprila (doppio clic nella lista) e nella scheda **Generale**:
- spunta **"Esegui indipendentemente dalla connessione dell'utente"**;
- spunta **"Esegui con i privilegi più elevati"**.
Così parte anche se non hai fatto l'accesso al PC.

Fatto! Ogni mattina alle 8:00 il PC aggiornerà i dati e il cruscotto da solo.

---

## Domande frequenti

**Devo tenere il PC acceso?** Sì, all'ora impostata il PC deve essere acceso (e non in sospensione).

**Dove vedo i risultati?** Apri `data\dashboard.html`. Mostra le 7 strutture, il confronto con la
settimana scorsa e la proiezione.

**Booking mi chiede un codice quando entra?** Sul tuo PC di solito no (è un dispositivo "conosciuto").
Se dovesse capitare, scrivimelo: troviamo una soluzione.

**Come aggiorno il programma se lo miglioriamo?** Riscarichi lo ZIP aggiornato e sostituisci i file
(il tuo `.env` e la cartella `data` restano). Più avanti possiamo usare `git` per aggiornare con un comando.

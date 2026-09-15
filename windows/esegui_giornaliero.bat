@echo off
REM ============================================================
REM  ESECUZIONE GIORNALIERA (tutte le strutture, senza finestre)
REM  E' questo il file che l'Utilita' di pianificazione lancera'
REM  ogni mattina. Fa: Booking -> storico -> cruscotto.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0.."
call ".venv\Scripts\activate.bat"

REM Browser NASCOSTO (nessuna finestra che si apre)
set BOOKING_HEADLESS=true

python run.py giornaliero >> "data\log_giornaliero.txt" 2>&1

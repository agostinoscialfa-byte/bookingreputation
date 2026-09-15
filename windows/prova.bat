@echo off
REM ============================================================
REM  PROVA (test su UNA sola struttura, con browser VISIBILE)
REM  Serve per controllare che il login funzioni.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0.."
call ".venv\Scripts\activate.bat"

REM Browser VISIBILE, cosi' vedi cosa succede
set BOOKING_HEADLESS=false

echo Provo il login e la lettura recensioni della prima struttura...
python run.py test

echo.
echo Se ha funzionato, apri il cruscotto:  data\dashboard.html
echo Se c'e' stato un problema, guarda le immagini in:  data\debug
pause

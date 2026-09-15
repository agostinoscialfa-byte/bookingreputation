@echo off
REM ============================================================
REM  INSTALLAZIONE (da fare UNA VOLTA sola)
REM  Doppio clic su questo file.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0.."

echo.
echo === Controllo Python ===
python --version
if errorlevel 1 (
  echo.
  echo ERRORE: Python non trovato.
  echo Installa Python da https://www.python.org/downloads/
  echo IMPORTANTE: durante l'installazione spunta "Add Python to PATH".
  echo Poi rilancia questo file.
  pause
  exit /b 1
)

echo.
echo === Creo l'ambiente Python (cartella .venv) ===
python -m venv .venv
call ".venv\Scripts\activate.bat"

echo.
echo === Aggiorno pip e installo le librerie ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERRORE durante l'installazione delle librerie.
  pause
  exit /b 1
)

echo.
echo === Installo il browser Chromium (serve per entrare in Booking) ===
python -m playwright install chromium

echo.
echo === Preparo il file delle credenziali (.env) ===
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Ho creato il file .env: ora si apre il Blocco Note.
  echo Scrivi la tua PASSWORD di Booking al posto di quella di esempio, poi SALVA e chiudi.
  notepad ".env"
) else (
  echo Il file .env esiste gia': non lo tocco.
)

echo.
echo ============================================================
echo  FATTO! Installazione completata.
echo  Ora fai doppio clic su:  windows\prova.bat
echo ============================================================
pause

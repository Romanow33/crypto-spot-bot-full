@echo off
REM -------------------------
REM Crypto Spot Bot - Run All Interactive
REM -------------------------

REM Verificar si existe el entorno virtual
if not exist ".venv\Scripts\activate" (
    echo Entorno virtual no encontrado. Creando...
    python -m venv .venv
    echo Entorno virtual creado
    
    REM Activar e instalar dependencias
    call .venv\Scripts\activate
    echo Instalando dependencias...
    pip install -r requirements.txt
) else (
    REM Solo activar si ya existe
    call .venv\Scripts\activate
)

REM Crear carpetas necesarias
mkdir data\raw 2>nul
mkdir data\processed 2>nul
mkdir models 2>nul
mkdir db 2>nul
mkdir logs 2>nul

REM Descargar datos historicos solo si no existen
if not exist "data\raw\klines.csv" (
    echo Descargando datos historicos...
    python scripts/download_klines.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --out data/raw/klines.csv
) else (
    echo Datos historicos ya existen en data\raw\klines.csv, omitiendo descarga.
)

REM Entrenar modelo
echo Entrenando modelo ML...
python -m models.train_model --data data/raw/klines.csv --out models/model.pkl --horizon 5 --thresh 0.002

REM Preguntar por el modo
echo.
echo Selecciona el modo del bot:
echo 1 - dev (pruebas/testnet)
echo 2 - prod (produccion)
set /p mode_choice=Ingresa 1 o 2: 

if "%mode_choice%"=="1" (
    set MODE=dev
) else (
    set MODE=prod
)

REM Preguntar por el dry mode
echo.
echo Selecciona tipo de dry mode:
echo 1 - log (solo imprimir mensajes)
echo 2 - sim (simulacion completa)
echo 3 - none (ejecutar real)
set /p dry_choice=Ingresa 1, 2 o 3: 

if "%dry_choice%"=="1" (
    set DRY=log
) else if "%dry_choice%"=="2" (
    set DRY=sim
) else (
    set DRY=none
)

REM Ejecutar bot con las opciones seleccionadas
echo.
echo Iniciando bot en modo %MODE% con dry=%DRY%...
python -m bot.runner --mode %MODE% --dry %DRY%

pause

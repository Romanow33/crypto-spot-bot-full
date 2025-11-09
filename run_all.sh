#!/bin/bash
# =========================================================================
# Crypto Spot Bot - Script de Ejecución Completo (Linux/Mac)
# =========================================================================
# Este script:
#  1. Activa el entorno virtual
#  2. Crea las carpetas necesarias
#  3. Descarga datos históricos (si no existen)
#  4. Entrena el modelo ML
#  5. Permite seleccionar modo (dev/prod) y dry-run (log/sim/none)
#  6. Ejecuta el bot
#  7. Los logs se guardan con formato: YYYY-MM-DD_TEST|PROD_dev|prod.log
# =========================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =========================================================================
# 1️⃣ ACTIVAR ENTORNO VIRTUAL
# =========================================================================
echo ""
echo -e "${BLUE}[1/6] Activando entorno virtual...${NC}"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Entorno virtual no encontrado${NC}"
    echo "Creando entorno virtual..."
    python3 -m venv .venv
fi

source .venv/bin/activate

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Entorno virtual activado${NC}"
else
    echo -e "${RED}❌ Error: No se pudo activar el entorno virtual${NC}"
    exit 1
fi

# =========================================================================
# 2️⃣ CREAR CARPETAS NECESARIAS
# =========================================================================
echo ""
echo -e "${BLUE}[2/6] Creando carpetas necesarias...${NC}"

mkdir -p data/raw
mkdir -p data/processed
mkdir -p models
mkdir -p db
mkdir -p logs
mkdir -p logs_archive

echo -e "${GREEN}✅ Carpetas creadas/verificadas${NC}"

# =========================================================================
# 3️⃣ DESCARGAR DATOS HISTÓRICOS
# =========================================================================
echo ""
echo -e "${BLUE}[3/6] Verificando datos históricos...${NC}"

if [ ! -f "data/raw/klines.csv" ]; then
    echo -e "${YELLOW}⏳ Descargando datos históricos (esto puede tomar varios minutos)...${NC}"
    
    if python scripts/download_klines.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --out data/raw/klines.csv; then
        echo -e "${GREEN}✅ Datos históricos descargados${NC}"
    else
        echo -e "${YELLOW}⚠️  Advertencia: Error al descargar datos históricos${NC}"
        echo "Continuando de todas formas..."
    fi
else
    echo -e "${GREEN}✅ Datos históricos ya existen (data/raw/klines.csv)${NC}"
fi

# =========================================================================
# 4️⃣ ENTRENAR MODELO ML
# =========================================================================
echo ""
echo -e "${BLUE}[4/6] Entrenando modelo Machine Learning...${NC}"

if [ -f "data/raw/klines.csv" ]; then
    if python -m models.train_model --data data/raw/klines.csv --out models/model.pkl; then
        echo -e "${GREEN}✅ Modelo ML entrenado${NC}"
    else
        echo -e "${YELLOW}⚠️  Advertencia: Error al entrenar el modelo${NC}"
        echo "El bot continuará sin modelo ML"
    fi
else
    echo -e "${YELLOW}⚠️  Sin datos históricos, omitiendo entrenamiento de modelo${NC}"
fi

# =========================================================================
# 5️⃣ SELECCIONAR MODO DE EJECUCIÓN
# =========================================================================
echo ""
echo -e "${BLUE}[5/6] Configuración del bot${NC}"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    SELECCIONA EL MODO                         ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  1 - DEV  (Testnet de Binance - Recomendado para pruebas)    ║${NC}"
echo -e "${BLUE}║  2 - PROD (Mainnet de Binance - ¡CUIDADO! Dinero real)       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Selecciona 1 o 2 (default 1): " mode_choice

if [ "$mode_choice" = "2" ]; then
    MODE="prod"
    echo -e "${YELLOW}⚠️  MODO PRODUCCIÓN SELECCIONADO - Asegúrate de que sea intencional${NC}"
else
    MODE="dev"
    echo -e "${GREEN}✅ Modo desarrollo (testnet) seleccionado${NC}"
fi

# =========================================================================
# 6️⃣ SELECCIONAR TIPO DE EJECUCIÓN
# =========================================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 SELECCIONA TIPO DE DRY-RUN                    ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  1 - LOG (Solo imprime señales, sin ejecutar - SEGURO)        ║${NC}"
echo -e "${BLUE}║  2 - SIM (Simulador interno, sin tocar exchange - SEGURO)     ║${NC}"
echo -e "${BLUE}║  3 - NONE (Ejecución REAL en exchange - ¡PELIGRO!)           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Selecciona 1, 2 o 3 (default 2): " dry_choice

if [ "$dry_choice" = "1" ]; then
    DRY="log"
    echo -e "${GREEN}✅ Modo LOG seleccionado (sin ejecutar)${NC}"
    TEST_MODE="TEST"
elif [ "$dry_choice" = "3" ]; then
    DRY="none"
    echo -e "${YELLOW}⚠️  MODO REAL SELECCIONADO - ¡CUIDADO CON TU DINERO!${NC}"
    TEST_MODE="PROD"
else
    DRY="sim"
    echo -e "${GREEN}✅ Modo SIMULADOR seleccionado${NC}"
    TEST_MODE="TEST"
fi

# =========================================================================
# 7️⃣ OBTENER FECHA/HORA ACTUAL
# =========================================================================
MYDATE=$(date +%Y-%m-%d)
MYTIME=$(date +%H%M%S)

# =========================================================================
# 8️⃣ CREAR RESUMEN DE CONFIGURACIÓN
# =========================================================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              RESUMEN DE CONFIGURACIÓN                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📅 Fecha/Hora:  ${MYDATE} ${MYTIME}"
echo -e "🌐 Modo:        ${MODE}"
echo -e "🔄 Dry-Run:     ${DRY}"
echo -e "🧪 Tipo:        ${TEST_MODE}"
echo -e "📂 Logs:        logs/${MYDATE}_${TEST_MODE}_${MODE}.log"
echo ""
echo -e "⚙️  Variables de entorno:"
echo -e "   MODE=${MODE}"
echo -e "   DRY=${DRY}"
echo ""

# =========================================================================
# 9️⃣ INICIAR EL BOT
# =========================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        🚀 INICIANDO BOT DE TRADING CRIPTO                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Presiona Ctrl+C para detener el bot en cualquier momento"
echo "Los logs se guardarán en: logs/${MYDATE}_${TEST_MODE}_${MODE}.log"
echo ""
echo "Iniciando en 3 segundos..."
sleep 3

MODE=$MODE DRY=$DRY python -m bot.runner --mode $MODE --dry $DRY

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Bot finalizado correctamente${NC}"
else
    echo ""
    echo -e "${RED}❌ El bot se detuvo con un error${NC}"
fi

echo "Los logs están en: logs/${MYDATE}_${TEST_MODE}_${MODE}.log"
echo ""

# =========================================================================
# 🔟 OPCIÓN DE ANALIZAR LOGS
# =========================================================================
echo ""
read -p "¿Deseas analizar los logs ahora? (s/n, default n): " analyze_choice

if [ "$analyze_choice" = "s" ] || [ "$analyze_choice" = "S" ]; then
    echo ""
    echo -e "${BLUE}📊 Analizando logs...${NC}"
    python scripts/analyze_logs.py logs/${MYDATE}_${TEST_MODE}_${MODE}.log --summary
else
    echo ""
    echo -e "${GREEN}Para analizar después, ejecuta:${NC}"
    echo "  python scripts/analyze_logs.py logs/${MYDATE}_${TEST_MODE}_${MODE}.log --summary"
    echo "  python scripts/analyze_logs.py logs/${MYDATE}_${TEST_MODE}_${MODE}.log --all"
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Para ver más opciones: python scripts/manage_logs.py list    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

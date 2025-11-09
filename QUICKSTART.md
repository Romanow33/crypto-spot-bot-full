# 🚀 Crypto Spot Bot - Guía de Inicio Rápido

## 📦 Instalación Inicial

### Requisitos Previos
- Python 3.8+
- pip
- git (opcional)

### Paso 1: Clonar o descargar el repositorio
```bash
git clone <url-del-repo>
cd crypto-spot-bot-full
```

### Paso 2: Crear entorno virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar credenciales
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env y agregar tus claves:
# BINANCE_API_KEY_DEV=<tu_key>
# BINANCE_API_SECRET_DEV=<tu_secret>
```

---

## ▶️ Ejecución Rápida

### **Windows (Recomendado)**
```bash
run_all.bat
```
El script te guiará interactivamente por todos los pasos.

### **Linux/Mac**
```bash
chmod +x run_all.sh
./run_all.sh
```

### **Manual (Todas las plataformas)**
```bash
# 1. Activar entorno
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Ejecutar bot
python -m bot.runner --mode dev --dry sim
```

---

## 📋 Opciones de Ejecución

### Modos

| Modo | Descripción | Riesgo | Uso |
|------|-------------|--------|-----|
| **dev** | Testnet Binance | 🟢 Bajo | Desarrollo/Pruebas |
| **prod** | Mainnet Binance | 🔴 Alto | Producción (¡cuidado!) |

### Dry-Run Options

| Opción | Descripción | Ejecución | Logs |
|--------|-------------|-----------|------|
| **log** | Solo imprime señales | ❌ No | Sí |
| **sim** | Simulador interno | ❌ No | Sí |
| **none** | Ejecución REAL | ✅ Sí | Sí |

### Ejemplos

```bash
# Desarrollo + Simulador (RECOMENDADO para empezar)
python -m bot.runner --mode dev --dry sim

# Desarrollo + Solo logs
python -m bot.runner --mode dev --dry log

# Producción REAL (¡PELIGRO!)
python -m bot.runner --mode prod --dry none
```

---

## 📊 Análisis de Logs

### Después de ejecutar el bot, analiza los resultados

```bash
# Ver resumen rápido
python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log

# Ver TODO (trades, balance, señales)
python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log --all

# Específico
python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log --trades
python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log --balance
python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log --signals
```

---

## 🗂️ Gestionar Logs

### Listar, limpiar, archivar

```bash
# Listar todos los logs disponibles
python scripts/manage_logs.py list

# Ver estadísticas
python scripts/manage_logs.py stats

# Limpiar logs > 7 días
python scripts/manage_logs.py cleanup 7

# Archivar en subcarpetas por fecha
python scripts/manage_logs.py archive

# Ver solo logs de hoy
python scripts/manage_logs.py today
```

---

## 🧪 Flujo Recomendado

### Día 1: Validar en TEST
```bash
# 1. Ejecutar con simulador
run_all.bat  # Selecciona: 1 (dev), 2 (sim)

# 2. Analizar resultados
python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log --all

# 3. Revisar:
#    - ¿Generó señales?
#    - ¿Las señales tienen sentido?
#    - ¿Cuál fue el P&L simulado?
```

### Semana 1-2: Backtest Histórico
```bash
# Ver LOGGING.md para framework de backtesting
# Validar que la estrategia es consistentemente rentable
```

### Mes 1: Small Position Live
```bash
# Solo cuando hayas confirmado que funciona
# Usa dev (testnet) primero
# Luego pequeña posición en prod

python -m bot.runner --mode prod --dry none
```

---

## ⚙️ Configuración

Editar `.env` para personalizar:

```env
# Trading
SYMBOL=BTCUSDT          # Par a tradear
TIMEFRAME=5m            # Timeframe de análisis
TRADE_PERCENT=0.01      # 1% del balance por trade
MIN_BASE_USDT=5.0       # Monto mínimo

# API (Testnet)
BINANCE_API_KEY_DEV=<tu_key>
BINANCE_API_SECRET_DEV=<tu_secret>

# API (Mainnet - CUIDADO!)
BINANCE_API_KEY=<tu_key>
BINANCE_API_SECRET=<tu_secret>
```

---

## 📁 Estructura de Archivos

```
crypto-spot-bot-full/
├── bot/                      # Código del bot
│   ├── runner.py            # Loop principal
│   ├── strategy.py          # Lógica de trading
│   ├── exchange.py          # Conexión Binance
│   ├── logger.py            # Sistema de logs
│   └── ...
│
├── scripts/                  # Scripts auxiliares
│   ├── analyze_logs.py      # Analizador de logs
│   ├── manage_logs.py       # Gestor de logs
│   └── ...
│
├── logs/                     # Logs de ejecución
│   ├── 2025-10-08_TEST_DEV.log
│   ├── 2025-10-08_PROD_PROD.log
│   └── ...
│
├── data/                     # Datos históricos
│   ├── raw/klines.csv
│   └── processed/
│
├── models/                   # Modelos ML
│   └── model.pkl
│
├── run_all.bat              # Script Windows
├── run_all.sh               # Script Linux/Mac
├── .env.example             # Ejemplo de configuración
└── LOGGING.md               # Documentación de logs
```

---

## 🐛 Troubleshooting

### No se activa el entorno virtual
```bash
# Recrear entorno
rmdir .venv  # o rm -rf .venv (Linux/Mac)
python -m venv .venv
```

### Error: "No module named bot"
```bash
# Asegúrate de estar en el directorio correcto
cd crypto-spot-bot-full

# O agregar a Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Error: "API key not found"
```bash
# Verificar que .env existe y tiene las claves correctas
cat .env | grep BINANCE_API_KEY
```

### Los logs no se generan
```bash
# Verificar que la carpeta logs/ existe
mkdir -p logs

# Verificar permisos
chmod 755 logs  # Linux/Mac
```

---

## ✅ Checklist Antes de Producción

- [ ] Backtesting exitoso en 6+ meses de datos históricos
- [ ] P&L positivo en sim durante 2+ semanas
- [ ] Validado en testnet (dev) durante 1+ mes
- [ ] Stop-losses configurados
- [ ] Máximo drawdown aceptable
- [ ] Risk management implementado
- [ ] Logs se generan correctamente
- [ ] Análisis automático funciona

---

## 📞 Soporte

- **Logs**: Revisar `logs/` - contienen todo lo que pasó
- **Análisis**: Ver `LOGGING.md` para detalles
- **Estrategia**: Ver `bot/strategy.py` para entender la lógica
- **Exchange**: Ver `bot/exchange.py` para órdenes

---

## 🎯 Próximos Pasos

1. ✅ Ejecutar `run_all.bat` (Windows) o `run_all.sh` (Linux/Mac)
2. ✅ Analizar los logs con `analyze_logs.py`
3. ✅ Revisar la estrategia en `bot/strategy.py`
4. ✅ Leer `LOGGING.md` para más detalles
5. ✅ Implementar mejoras sugeridas en el análisis inicial

---

**¡Bienvenido al bot de trading! 🚀**

Para preguntas, revisa los comentarios en el código o la documentación en `LOGGING.md`.

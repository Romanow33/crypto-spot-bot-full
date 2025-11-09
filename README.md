# Crypto Spot Bot (Spot Trading)

## Flujo completo de setup y ejecución

### 0️⃣ Preparar entorno
1. Activar virtualenv:
```powershell
.venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Crear carpetas necesarias:
```bash
mkdir data\raw
mkdir data\processed
mkdir models
mkdir db
```

4. Configurar .env:
```env
BINANCE_API_KEY=<tu_api_key>
BINANCE_API_SECRET=<tu_api_secret>
MODE=dev      # 'dev' para testnet, 'prod' para producción
```

### 1️⃣ Descargar datos históricos
```bash
python scripts/download_klines.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --out data/raw/klines.csv
```

### 2️⃣ Entrenar modelo
```bash
python -m models.train_model --data data/raw/klines.csv --out models/model.pkl
```

### 3️⃣ Ejecutar backtest
Antes de correr el bot con dinero real, valida la estrategia con datos históricos:

```bash
# Backtest básico (todo el histórico)
python backtester/backtest.py

# Últimos 6 meses
python backtester/backtest.py --start 2024-04-01

# Guardar resultados a CSV
python backtester/backtest.py --save

# Sin ML scorer
python backtester/backtest.py --no-ml

# Capital personalizado
python backtester/backtest.py --capital 5000

# Rango específico
python backtester/backtest.py --start 2024-01-01 --end 2024-06-30 --save
```

**Métricas incluidas:**
- Total Return, Win Rate, Profit Factor
- Sharpe Ratio, Max Drawdown
- Avg Win/Loss, Best/Worst Trade
- Equity curve completa
- Historial de trades detallado

Los resultados se guardan en `backtester/results/` cuando usas `--save`.

### 4️⃣ Ejecutar bot
```bash
python -m bot.runner --mode dev --dry sim
```

**Argumentos:**

`--mode {dev,prod}`
- dev → testnet
- prod → producción

`--dry {sim,log,none}`
- sim → simulador interno (P&L, fills, fees)
- log → solo imprime logs, no ejecuta
- none → ejecuta órdenes reales

**Comportamiento según modo:**

| MODE | DRY  | Comportamiento |
|------|------|----------------|
| dev  | sim  | Simula en testnet con ledger interno |
| dev  | log  | Solo logs, no ejecuta |
| dev  | none | Ejecuta órdenes reales en testnet |
| prod | sim  | Simula en prod, no envía órdenes |
| prod | log  | Solo logs en prod |
| prod | none | **EJECUTA ÓRDENES REALES EN PRODUCCIÓN** |

---

## 🔄 Run All (Windows)

Ejecuta todo el flujo automáticamente con `run_all.bat`:

```batch
@echo off
REM Activar entorno
call .venv\Scripts\activate

REM Crear carpetas
mkdir data\raw data\processed models db

REM Descargar datos
python scripts/download_klines.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --out data/raw/klines.csv

REM Entrenar modelo
python -m models.train_model --data data/raw/klines.csv --out models/model.pkl

REM Ejecutar backtest
python backtester/backtest.py --save

REM Iniciar bot
python -m bot.runner --mode dev --dry sim

pause
```

Ejecutar: `run_all.bat`

---

## 📊 Características Implementadas

✅ **Risk Management**
- Stop loss automático (-1% configurable)
- Órdenes MAKER (fees 0.04% vs 0.06%)
- Filtro de tendencia (SMA50)
- ML scorer con threshold ajustable

✅ **Trading Features**
- Position sizing dinámico
- Min notional validation
- Step size adjustment
- Fee calculation precisa

✅ **Backtesting**
- Métricas completas de performance
- Export a CSV
- Equity curve tracking
- Trade-by-trade analysis

---

## 📝 Configuración .env

Variables principales:

```env
# Trading
SYMBOL=BTCUSDT
TRADE_PERCENT=0.01
STOP_LOSS_PERCENT=0.01

# Filtros
USE_TREND_FILTER=true
USE_ML_FILTER=true
ML_THRESHOLD=0.65

# Órdenes
USE_MAKER_ORDERS=true
MAKER_WAIT_SECONDS=5.0
MAKER_PRICE_OFFSET=0.0005
```

Ver `.env.example` para lista completa.

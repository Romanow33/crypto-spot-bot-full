# Sistema de Logging - Crypto Spot Bot

## Descripción

El nuevo sistema de logging centralizado mejora la legibilidad, rastreabilidad y debugging del bot.

## Cambios Principales

### 1. **Nuevo archivo: `bot/logger.py`** 
   - Logging centralizado con timestamp automático
   - Diferencia entre modo TEST y PROD
   - Funciones especializadas para cada tipo de evento

### 2. **Nombres de archivos de log mejorados**
   - **Antes**: `2025-10-06.log` (confuso)
   - **Ahora**: `2025-10-06_TEST_DEV.log` (claro)
   - **Formato**: `YYYY-MM-DD_MODE_ENVIRONMENT.log`
   - Ejemplo: `2025-10-08_PROD_PROD.log`

### 3. **Estructura de logs mejorada**
   ```
   [2025-10-08 01:01:27] [INFO] [crypto_bot] [BALANCE] USDT=47.51 | BTC=0.000007 | Source=periodic_monitor
   [2025-10-08 01:02:15] [INFO] [crypto_bot] [SIGNAL] Type=BUY | Price=65420.50 | EMA9=65250.00 | EMA21=65100.00 | RSI=45.30
   [2025-10-08 01:03:00] [INFO] [crypto_bot] [TRADE] Type=BUY | Symbol=BTCUSDT | Qty=0.0001 | Price=65420.50 | USDT=6.54 | Status=SIMULATED
   ```

## Funciones Disponibles

### Balance Logging
```python
from bot.logger import log_balance

log_balance(usdt=47.51, btc=0.000007, source="periodic_monitor")
```

### Signal Logging
```python
from bot.logger import log_signal

log_signal(signal=1, price=65420.50, ema9=65250.00, ema21=65100.00, rsi=45.30)
```

### Trade Logging
```python
from bot.logger import log_trade

log_trade(
    trade_type="BUY",
    symbol="BTCUSDT",
    quantity="0.0001",
    price=65420.50,
    amount_usdt=6.54,
    status="EXECUTED"
)
```

### Error/Warning Logging
```python
from bot.logger import log_error, log_warning, log_info

log_error("Conexión rechazada", context="exchange")
log_warning("Balance bajo", context="risk_management")
log_info("Bot iniciado correctamente", context="startup")
```

## Variables de Entorno

El modo se detecta automáticamente:
- `MODE` env var → "dev" o "prod"
- `DRY` env var → "log", "sim" o "none"
- **TEST_MODE** se asigna automáticamente:
  - Si `DRY` es "log" o "sim" → **TEST**
  - Si `DRY` es "none" → **PROD**

## Ubicación de Logs

- **Directorio**: `./logs/`
- **Nombres**:
  - Test en dev: `2025-10-08_TEST_DEV.log`
  - Prod en prod: `2025-10-08_PROD_PROD.log`
  - Test en prod: `2025-10-08_TEST_PROD.log`

## Beneficios

✅ **Timestamps automáticos** - Cada log incluye fecha/hora exacta
✅ **TEST vs PROD** - Diferencia clara en nombres de archivo
✅ **Contexto estructurado** - Sección [BALANCE], [SIGNAL], [TRADE]
✅ **Sin duplicados** - Monitor ya no crea logs manuales
✅ **Rastreable** - Fácil encontrar errores en logs
✅ **Congruente** - Nombres y formatos consistentes

## Próximas Mejoras

- [ ] Agregar nivel de severidad por módulo
- [ ] Crear parser de logs para análisis
- [ ] Generar reportes de trading diarios
- [ ] Dashboard web con logs en tiempo real

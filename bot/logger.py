"""
Módulo de logging centralizado para el bot de trading
Maneja todos los logs del sistema con timestamp y contexto TEST/PROD
"""

import os
import logging
from datetime import datetime
from pathlib import Path

# Configurar directorio de logs
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Obtener modo de ejecución (TEST/PROD)
MODE = os.getenv("MODE", "dev").upper()
DRY = os.getenv("DRY", "log").upper()
TEST_MODE = "TEST" if DRY in ["LOG", "SIM"] else "PROD"

# Nombre del archivo de log con fecha y modo
current_date = datetime.now().strftime("%Y-%m-%d")
log_filename = f"{current_date}_{TEST_MODE}_{MODE}.log"
log_filepath = LOGS_DIR / log_filename

# Crear logger principal
logger = logging.getLogger("crypto_bot")
logger.setLevel(logging.DEBUG)

# Formato detallado con timestamp
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler para archivo
file_handler = logging.FileHandler(log_filepath)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Handler para consola (info y superior)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def log_balance(usdt: float, btc: float, source: str = "balance_monitor"):
    """Log del balance actual con contexto"""
    logger.info(f"[BALANCE] USDT={usdt:.2f} | BTC={btc:.6f} | Source={source}")


def log_signal(signal: int, price: float, ema9: float, ema21: float, rsi: float):
    """Log de señal de trading con contexto"""
    signal_text = {1: "BUY", -1: "SELL", 0: "HOLD"}[signal]
    logger.info(
        f"[SIGNAL] Type={signal_text} | Price={price:.2f} | "
        f"EMA9={ema9:.2f} | EMA21={ema21:.2f} | RSI={rsi:.2f}"
    )


def log_trade(trade_type: str, symbol: str, quantity: str, price: float, amount_usdt: float, status: str):
    """Log de ejecución de trade"""
    logger.info(
        f"[TRADE] Type={trade_type} | Symbol={symbol} | Qty={quantity} | "
        f"Price={price:.2f} | USDT={amount_usdt:.2f} | Status={status}"
    )


def log_error(error_msg: str, context: str = "unknown"):
    """Log de errores con contexto"""
    logger.error(f"[ERROR] Context={context} | Message={error_msg}")


def log_warning(warning_msg: str, context: str = "unknown"):
    """Log de advertencias"""
    logger.warning(f"[WARNING] Context={context} | Message={warning_msg}")


def log_info(message: str, context: str = "info"):
    """Log de información general"""
    logger.info(f"[{context.upper()}] {message}")


def get_logger():
    """Retorna el logger para uso directo si es necesario"""
    return logger


def get_log_filepath():
    """Retorna la ruta del archivo de log actual"""
    return str(log_filepath)


def get_test_mode():
    """Retorna el modo actual (TEST/PROD)"""
    return TEST_MODE

def log_stop_loss(symbol: str, entry_price: float, exit_price: float, loss_pct: float):
    """Log de stop loss activado"""
    logger.warning(
        f"[STOP_LOSS] Symbol={symbol} | Entry=${entry_price:.2f} | "
        f"Exit=${exit_price:.2f} | Loss={loss_pct:.2f}%"
    )
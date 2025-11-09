"""Monitor de balances periódico del exchange"""

import asyncio
from bot.logger import log_balance, log_error, get_test_mode


async def print_balances_periodic(exchange, interval=60):
    """Monitorea y registra el balance del exchange cada X segundos
    
    Args:
        exchange: Instancia del Exchange
        interval: Segundos entre chequeos (default 60)
    """
    while True:
        try:
            b = await exchange.get_balances()
            usdt = b.get('USDT', 0.0)
            btc = b.get('BTC', 0.0)
            log_balance(usdt, btc, source="periodic_monitor")
        except Exception as e:
            log_error(f"Failed to fetch balances: {str(e)}", context="balance_monitor")
        await asyncio.sleep(interval)

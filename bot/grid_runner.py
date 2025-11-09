"""
Grid Trading Bot Runner
Ejecuta estrategia de grid trading automático
"""

import argparse
import asyncio
import os
from dotenv import load_dotenv
from bot.exchange import Exchange
from bot.strategies.grid_trading import GridStrategy, create_grid_from_current_price
from bot.monitor import print_balances_periodic
from bot.logger import log_info, log_trade, log_error
from datetime import datetime

load_dotenv()


async def grid_trading_loop(args):
    """Loop principal de grid trading"""
    
    ex = Exchange(dry=args.dry if args.dry != "none" else "off")
    monitor = asyncio.create_task(print_balances_periodic(ex, interval=60))
    
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    
    log_info(f"Grid Trading Bot iniciado | Mode: {args.mode} | Dry: {args.dry}", context="grid_startup")
    
    try:
        # Obtener precio actual para crear grid
        log_info("Obteniendo precio actual...", context="grid_init")
        pr = await ex._run(ex.client.ticker_price, symbol)
        current_price = float(pr["price"]) if isinstance(pr, dict) else float(pr)
        
        log_info(f"Precio actual: ${current_price:.2f}", context="grid_init")
        
        # Crear grid
        grid_range_pct = float(os.getenv("GRID_RANGE_PCT", "0.05"))  # ±5%
        num_grids = int(os.getenv("GRID_LEVELS", "10"))
        
        grid = create_grid_from_current_price(
            current_price=current_price,
            grid_range_pct=grid_range_pct,
            num_grids=num_grids
        )
        
        status = grid.get_status()
        log_info(
            f"Grid creado: {status['grid_range']} | Niveles: {status['total_levels']} | Step: {status['grid_step']}",
            context="grid_init"
        )
        
        # Loop principal
        while True:
            # Obtener precio actual
            pr = await ex._run(ex.client.ticker_price, symbol)
            price = float(pr["price"]) if isinstance(pr, dict) else float(pr)
            
            # Obtener señal del grid
            signal, target_level, reason = grid.get_signal(price)
            
            if signal != 0:
                log_info(f"Señal: {reason}", context="grid_signal")
            
            # Ejecutar trades
            if signal == 1:  # BUY
                size_usdt = float(os.getenv("GRID_INVESTMENT_PER_LEVEL", "10.0"))
                
                if args.dry == "sim":
                    log_info(f"[SIM] Comprando ${size_usdt:.2f} en nivel {target_level:.2f}", context="grid_trade")
                    grid.execute_buy(target_level)
                    log_trade(
                        trade_type="BUY",
                        symbol=symbol,
                        quantity="simulated",
                        price=price,
                        amount_usdt=size_usdt,
                        status="SIMULATED_GRID"
                    )
                else:
                    try:
                        await ex.limit_buy(symbol, size_usdt)
                        grid.execute_buy(target_level)
                        log_trade(
                            trade_type="BUY",
                            symbol=symbol,
                            quantity="variable",
                            price=price,
                            amount_usdt=size_usdt,
                            status="EXECUTED_GRID"
                        )
                    except Exception as e:
                        log_error(f"Grid buy failed: {str(e)}", context="grid_trade")
            
            elif signal == -1:  # SELL
                # Calcular cantidad a vender del nivel
                bals = await ex.get_balances()
                btc_balance = bals.get("BTC", 0.0)
                
                # Vender porción proporcional al grid
                qty_to_sell = btc_balance / max(1, sum(1 for v in grid.positions.values() if v))
                
                if qty_to_sell > 0:
                    if args.dry == "sim":
                        log_info(f"[SIM] Vendiendo {qty_to_sell:.6f} BTC en nivel {target_level:.2f}", context="grid_trade")
                        grid.execute_sell(target_level)
                        log_trade(
                            trade_type="SELL",
                            symbol=symbol,
                            quantity=str(qty_to_sell),
                            price=price,
                            amount_usdt=qty_to_sell * price,
                            status="SIMULATED_GRID"
                        )
                    else:
                        try:
                            await ex.limit_sell(symbol, qty_to_sell)
                            grid.execute_sell(target_level)
                            log_trade(
                                trade_type="SELL",
                                symbol=symbol,
                                quantity=str(qty_to_sell),
                                price=price,
                                amount_usdt=qty_to_sell * price,
                                status="EXECUTED_GRID"
                            )
                        except Exception as e:
                            log_error(f"Grid sell failed: {str(e)}", context="grid_trade")
            
            # Log status periódicamente
            if datetime.now().second == 0:
                status = grid.get_status()
                log_info(
                    f"Grid status: {status['active_positions']}/{status['total_levels']} posiciones activas | Precio: ${price:.2f}",
                    context="grid_status"
                )
            
            await asyncio.sleep(5)  # Check cada 5 segundos
            
    finally:
        monitor.cancel()
        await asyncio.gather(monitor, return_exceptions=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Grid Trading Bot")
    p.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default=os.getenv("MODE", "dev"),
        help="Modo: dev=testnet, prod=mainnet"
    )
    p.add_argument(
        "--dry",
        choices=["none", "log", "sim"],
        default=os.getenv("DRY", "sim"),
        help="Dry-run: none=real, log=solo logs, sim=simulador"
    )
    args = p.parse_args()
    
    log_info("=== GRID TRADING BOT START ===", context="grid_startup")
    log_info(f"Mode: {args.mode} | Dry: {args.dry}", context="grid_startup")
    
    try:
        asyncio.run(grid_trading_loop(args))
    except KeyboardInterrupt:
        log_info("Grid bot detenido por usuario", context="grid_shutdown")
    except Exception as e:
        log_error(f"Error crítico: {str(e)}", context="grid_fatal")

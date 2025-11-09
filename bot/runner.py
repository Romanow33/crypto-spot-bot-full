# === file: runner.py ===
"""Runner principal del bot de trading cripto
Maneja la ejecución del loop estratégico en modo TEST/PROD
"""

import argparse
import asyncio
import os
import pandas as pd
from dotenv import load_dotenv
from bot.exchange import Exchange
from bot.strategy import build_signals, compute_features
from bot.ml_scorer import MLScorer
from bot.monitor import print_balances_periodic
from bot.simulator import Simulator
from bot.logger import (
    log_signal, log_trade, log_error, log_info, 
    get_test_mode, get_log_filepath
)
from datetime import datetime
from bot.data_source import get_latest_klines

load_dotenv()


async def strategy_loop(args):
    """Loop principal de estrategia de trading
    
    Args:
        args: Argumentos de línea de comandos (mode, dry)
    """
    ex = Exchange(dry=args.dry if args.dry != "none" else "off")
    sim = Simulator(start_usdt=1000.0) if args.dry == "sim" else None
    monitor = asyncio.create_task(print_balances_periodic(ex, interval=60))
    ml = MLScorer(os.getenv("MODEL_PATH"))
    
    test_mode = get_test_mode()
    log_info(
        f"Bot iniciado en modo {test_mode} | Enviroment: {args.mode} | Dry: {args.dry}",
        context="startup"
    )
    
    try:
        data_path = "data/raw/klines.csv"
        while True:
            if not os.path.exists(data_path):
                log_info(f"Esperando datos en {data_path}", context="data_source")
                await asyncio.sleep(5)
                continue
            
            df = get_latest_klines(symbol=os.getenv("SYMBOL", "BTCUSDT"), interval="5m")
            if df.empty:
                await asyncio.sleep(5)
                continue
            
            feats = compute_features(df)
            if len(feats) == 0:
                await asyncio.sleep(5)
                continue
            
            ml_scores = ml.predict(feats)
            sig_df = build_signals(df, ml_scores=ml_scores)
            last = sig_df.iloc[-1]
            sig = int(last["final"])
            price = float(last["close"])
            ema9 = float(last["ema9"])
            ema21 = float(last["ema21"])
            rsi = float(last["rsi14"])
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            symbol = os.getenv("SYMBOL", "BTCUSDT")
            
            # ---------------------------
            # VERIFICAR STOP LOSS PRIMERO (antes de señales)
            # ---------------------------
            if args.dry == "sim":
                has_position = sim.btc > 0
                # Verificar stop loss en simulador
                if has_position and sim.check_stop_loss(price):
                    log_info(
                        f"Stop loss activado en {symbol} a ${price:.2f}",
                        context="stop_loss"
                    )
                    r = sim.sell_market(price, sim.btc)
                    log_trade(
                        trade_type="SELL",
                        symbol=symbol,
                        quantity=str(r.get('qty', 0)),
                        price=price,
                        amount_usdt=r.get('usdt', 0),
                        status="SIMULATED_STOP_LOSS"
                    )
                    await asyncio.sleep(60)
                    continue
            elif args.dry != "log":
                # Verificar stop loss en modo real
                bals = await ex.get_balances()
                has_position = bals.get("BTC", 0.0) > 0
                if has_position and ex.check_stop_loss(symbol, price):
                    log_info(
                        f"Stop loss activado en {symbol} a ${price:.2f}",
                        context="stop_loss"
                    )
                    btc_bal = bals.get("BTC", 0.0)
                    await ex.market_sell(symbol, btc_bal)
                    log_trade(
                        trade_type="SELL",
                        symbol=symbol,
                        quantity=str(btc_bal),
                        price=price,
                        amount_usdt=btc_bal * price,
                        status="EXECUTED_STOP_LOSS"
                    )
                    await asyncio.sleep(60)
                    continue
            
            # Log de señal (después de verificar stop loss)
            if sig != 0:
                log_signal(sig, price, ema9, ema21, rsi)

            # ---------------------------
            # TEST LOG: solo imprimir señal (sin ejecutar)
            # ---------------------------
            if args.dry == "log":
                if sig != 0:
                    log_info(
                        f"Signal={sig} Price={price:.2f} [NO EXECUTION]",
                        context="test_log_only"
                    )
                await asyncio.sleep(60)
                continue  # saltar ejecución

            # ---------------------------
            # TEST SIMULATOR: Simulación interna (sin tocar exchange real)
            # ---------------------------
            elif args.dry == "sim":
                if sig == 1:
                    size_usdt, reason = await ex.compute_buy_usdt(
                        symbol=os.getenv("SYMBOL", "BTCUSDT"), 
                        usdt_balance=sim.usdt
                    )
                    if size_usdt is None:
                        log_info(f"Buy skip: {reason}", context="test_simulator")
                    else:
                        r = sim.buy_market(price, size_usdt)
                        log_trade(
                            trade_type="BUY",
                            symbol=os.getenv("SYMBOL", "BTCUSDT"),
                            quantity=str(r.get('qty', 0)),
                            price=price,
                            amount_usdt=size_usdt,
                            status="SIMULATED"
                        )
                elif sig == -1 and sim.btc > 0:
                    r = sim.sell_market(price, sim.btc)
                    log_trade(
                        trade_type="SELL",
                        symbol=os.getenv("SYMBOL", "BTCUSDT"),
                        quantity=str(r.get('qty', 0)),
                        price=price,
                        amount_usdt=r.get('usdt', 0),
                        status="SIMULATED"
                    )

            # ---------------------------
            # PRODUCCIÓN: Ejecución real en exchange
            # ---------------------------
            else:
                if sig == 1:
                    size_usdt, reason = await ex.compute_buy_usdt(
                        symbol=os.getenv("SYMBOL", "BTCUSDT")
                    )
                    if size_usdt is None:
                        log_error(f"Buy rejected: {reason}", context="prod_trade")
                    else:
                        try:
                            await ex.limit_buy(os.getenv("SYMBOL", "BTCUSDT"), size_usdt)
                            log_trade(
                                trade_type="BUY",
                                symbol=os.getenv("SYMBOL", "BTCUSDT"),
                                quantity="variable",
                                price=price,
                                amount_usdt=size_usdt,
                                status="EXECUTED"
                            )
                        except Exception as e:
                            log_error(f"Buy execution failed: {str(e)}", context="prod_buy")
                
                elif sig == -1:
                    bals = await ex.get_balances()
                    btc_bal = bals.get("BTC", 0.0)
                    if btc_bal <= 0:
                        log_info("No BTC to sell", context="prod_trade")
                    else:
                        try:
                            await ex.limit_sell(os.getenv("SYMBOL", "BTCUSDT"), btc_bal)
                            log_trade(
                                trade_type="SELL",
                                symbol=os.getenv("SYMBOL", "BTCUSDT"),
                                quantity=str(btc_bal),
                                price=price,
                                amount_usdt=btc_bal * price,
                                status="EXECUTED"
                            )
                        except Exception as e:
                            log_error(f"Sell execution failed: {str(e)}", context="prod_sell")

            await asyncio.sleep(60)
    finally:
        # cancelar el monitor al terminar
        monitor.cancel()
        await asyncio.gather(monitor, return_exceptions=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Bot de Trading Crypto - Ejecución del loop estratégico"
    )
    p.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default=os.getenv("MODE", "dev"),
        help="Modo de ejecución: dev=testnet, prod=mainnet"
    )
    p.add_argument(
        "--dry",
        choices=["none", "log", "sim"],
        default=os.getenv("DRY", "log"),
        help="Modo dry-run: none=real, log=solo logs, sim=simulador"
    )
    args = p.parse_args()

    # Log de inicialización
    log_info(
        f"=== INICIO DE BOT ===",
        context="runner_startup"
    )
    log_info(
        f"Modo: {args.mode} | Dry-run: {args.dry}",
        context="runner_startup"
    )

    try:
        asyncio.run(strategy_loop(args))
    except KeyboardInterrupt:
        log_info("Bot detenido por usuario (Ctrl+C)", context="runner_shutdown")
    except Exception as e:
        log_error(f"Error crítico: {str(e)}", context="runner_fatal")
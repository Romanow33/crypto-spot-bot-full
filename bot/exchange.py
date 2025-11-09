# === file: exchange.py ===
import os
import asyncio
import math
from decimal import Decimal, getcontext, ROUND_UP
from dotenv import load_dotenv

load_dotenv()

try:
    # SDK oficial reciente de Binance
    from binance.spot import Spot as BinanceClient
except ImportError as e:
    raise RuntimeError(
        "Binance SDK no encontrado. Instalá con: pip install binance-connector"
    ) from e

# -----------------------------
# CONFIGURACIÓN GLOBAL
# -----------------------------
MODE = os.getenv("MODE", "dev")
API_SECRET = (
    os.getenv("BINANCE_API_SECRET_DEV")
    if MODE == "dev"
    else os.getenv("BINANCE_API_SECRET")
)
API_KEY = (
    os.getenv("BINANCE_API_KEY_DEV") if MODE == "dev" else os.getenv("BINANCE_API_KEY")
)
TESTNET_URL = "https://testnet.binance.vision"

# Parámetros ajustables por environment
TRADE_PERCENT = float(os.getenv("TRADE_PERCENT", 0.01))  # 1% por defecto
TRADE_FEE_RATE = float(os.getenv("TRADE_FEE_RATE", 0.001))  # 0.1% por defecto
MIN_BASE_USDT = float(os.getenv("MIN_BASE_USDT", 5.0))
MIN_MARGIN_USDT = float(os.getenv("MIN_MARGIN_USDT", 1.0))
SAFETY_MARGIN = float(os.getenv("SAFETY_MARGIN", 1.02))  # 2% buffer para slippage/fees
USE_MAKER_ORDERS = os.getenv("USE_MAKER_ORDERS", "true").lower() == "true"
MAKER_WAIT_SECONDS = float(os.getenv("MAKER_WAIT_SECONDS", 5.0))
MAKER_PRICE_OFFSET = float(os.getenv("MAKER_PRICE_OFFSET", 0.0005))  # 0.05% mejor que mercado

# Aumentar precisión decimal para cálculos con Decimal
getcontext().prec = 28


class Exchange:
    def __init__(self, dry="off"):
        """
        dry puede ser:
            - "off": ejecutar órdenes reales
            - "log": solo imprimir
            - "sim": simulación sin enviar órdenes
        """
        self.dry = dry
        self.entry_prices = {}

        if MODE == "dev":
            self.client = BinanceClient(API_KEY, API_SECRET, base_url=TESTNET_URL)
        else:
            self.client = BinanceClient(API_KEY, API_SECRET)

    async def _run(self, func, *args, **kwargs):
        """Ejecuta funciones del cliente en un thread async-safe."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # -----------------------------
    # BALANCES
    # -----------------------------
    async def get_balances(self):
        acct = await self._run(self.client.account)
        bal = {b["asset"]: float(b["free"]) for b in acct.get("balances", [])}
        return {
            "USDT": bal.get("USDT", 0.0),
            "BTC": bal.get("BTC", 0.0),
        }

    # -----------------------------
    # CÁLCULO CENTRALIZADO DE SIZING
    # -----------------------------
    async def compute_buy_usdt(self, symbol="BTCUSDT", usdt_balance: float = None):
        """
        Política:
         - Intentar usar TRADE_PERCENT (ej. 1%) del balance.
         - Si ese 1% alcanza el umbral (MIN_BASE_USDT + comisión + MIN_MARGIN_USDT) -> usar el 1% (siempre).
         - Si 1% NO alcanza -> usar FALLBACK_USDT (por defecto 7) si hay suficiente balance.
         - Si no hay FALLBACK_USDT disponible -> skipear.
         - Verifica min_notional y que candidate <= usdt_balance.
        Retorna (usdt_amount, reason).
        """
        try:
            if usdt_balance is None:
                bals = await self.get_balances()
                usdt_balance = bals.get("USDT", 0.0)

            symbol = symbol or os.getenv("SYMBOL", "BTCUSDT")

            if usdt_balance <= 0:
                return None, "USDT balance <= 0"

            FALLBACK_USDT = float(os.getenv("FALLBACK_USDT", 7.0))

            # candidate = 1% del balance (o TRADE_PERCENT)
            candidate = usdt_balance * TRADE_PERCENT

            # comisión estimada sobre candidate
            commission = candidate * TRADE_FEE_RATE

            # umbral requerido
            threshold = MIN_BASE_USDT + commission + MIN_MARGIN_USDT

            # Si 1% alcanza el umbral -> lo usamos (sin tocarlo)
            if candidate >= threshold:
                chosen = candidate
            else:
                # 1% no alcanza -> usar fallback fijo si hay suficiente balance
                if usdt_balance < FALLBACK_USDT:
                    return None, (
                        f"1% ({candidate:.2f}) < umbral ({threshold:.2f}) y balance ({usdt_balance:.2f}) < FALLBACK ({FALLBACK_USDT:.2f})."
                    )
                chosen = FALLBACK_USDT
                # recomputar comisión/threshold sobre chosen
                commission = chosen * TRADE_FEE_RATE
                threshold = MIN_BASE_USDT + commission + MIN_MARGIN_USDT
                if chosen < threshold:
                    return None, (
                        f"FALLBACK ({chosen:.2f}) no alcanza el umbral ({threshold:.2f})."
                    )

            # Verificar min_notional del símbolo
            info = await self._run(self.client.exchange_info, symbol=symbol)
            filters = {f["filterType"]: f for f in info["symbols"][0]["filters"]}
            min_notional = float(filters["NOTIONAL"]["minNotional"])

            if chosen < min_notional:
                return None, (
                    f"Cantidad ({chosen:.2f} USDT) < minNotional del símbolo ({min_notional:.2f} USDT)."
                )

            if chosen > usdt_balance:
                return (
                    None,
                    f"Candidate ({chosen:.2f}) > USDT disponible ({usdt_balance:.2f}).",
                )

            return chosen, "OK"

        except Exception as e:
            return None, f"compute_buy_usdt error: {e}"

    # -----------------------------
    # ORDEN DE COMPRA
    # -----------------------------
    async def market_buy(self, symbol, usdt_amount: float = None):
        """
        Ejecuta una orden de compra de mercado con una cantidad en USDT.
        Si usdt_amount es None, lo calcula con compute_buy_usdt.
        Ajusta automáticamente al stepSize, asegura min_notional,
        y no realiza la compra si no es posible respetar las reglas sin exceder saldo.
        """
        try:
            # Si no se pasó monto, calcularlo centralizadamente
            if usdt_amount is None:
                usdt_amount, reason = await self.compute_buy_usdt(symbol=symbol)
                if usdt_amount is None:
                    print(f"[SKIP] market_buy: {reason}")
                    return None

            # obtener saldo real de USDT para no pasarnos (y evitar circularidad con compute)
            bals = await self.get_balances()
            usdt_balance = bals.get("USDT", 0.0)

            if usdt_amount > usdt_balance:
                print(
                    f"[SKIP] market_buy: candidate {usdt_amount:.2f} > USDT disponible {usdt_balance:.2f}"
                )
                return None

            # precio actual
            pr = await self._run(self.client.ticker_price, symbol)
            price = float(pr["price"]) if isinstance(pr, dict) else float(pr)

            # filtros del símbolo
            info = await self._run(self.client.exchange_info, symbol=symbol)
            filters = {f["filterType"]: f for f in info["symbols"][0]["filters"]}
            step_size_str = filters["LOT_SIZE"]["stepSize"]
            step_size = Decimal(step_size_str)
            min_notional = float(filters["NOTIONAL"]["minNotional"])

            # aplicar safety margin al monto que intentaremos usar para crear qty,
            # pero NO podemos exceder el balance real.
            usdt_with_margin = Decimal(str(usdt_amount)) * Decimal(str(SAFETY_MARGIN))
            usdt_with_margin = min(usdt_with_margin, Decimal(str(usdt_balance)))

            # calcular qty en Decimal para evitar errores de float
            price_d = Decimal(str(price))
            qty = usdt_with_margin / price_d

            # ajustar qty al múltiplo de step_size (floor)
            qty_adjusted = (qty // step_size) * step_size

            # si por redondeo qty_adjusted queda en 0, intentar elevar al step_size mínimo
            if qty_adjusted <= Decimal("0"):
                qty_adjusted = step_size

            # formatear cantidad según step_size decimal places
            if "." in step_size_str:
                step_decimals = len(step_size_str.rstrip("0").split(".")[1])
            else:
                step_decimals = 0

            # asegurar que qty_adjusted no exceda lo que compraremos con usdt_balance
            # (caso borde por min_notional ajuste)
            # calcular order_value actual
            qty_str = format(
                qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f"
            )
            if "." in qty_str:
                qty_str = qty_str.rstrip("0").rstrip(".")
            order_value = float(Decimal(qty_str) * price_d)

            # si el valor está por debajo del min_notional, forzar al mínimo requerido
            if order_value < min_notional:
                min_qty = Decimal(str(min_notional)) / price_d
                times = (min_qty / step_size).to_integral_value(rounding=ROUND_UP)
                qty_adjusted = times * step_size

                qty_str = format(
                    qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f"
                )
                if "." in qty_str:
                    qty_str = qty_str.rstrip("0").rstrip(".")
                order_value = float(Decimal(qty_str) * price_d)

                print(
                    f"[WARN] Ajustado a min_notional: qty={qty_str} (≈{order_value:.2f} USDT)"
                )

            # finalmente: si el USDT requerido para esta qty excede el balance -> recortar hacia abajo
            usdt_needed = Decimal(qty_str) * price_d
            if usdt_needed > Decimal(str(usdt_balance)):
                # recortar al máximo que se puede comprar con el saldo disponible
                max_qty = (
                    (Decimal(str(usdt_balance)) / price_d) // step_size * step_size
                )
                if max_qty <= Decimal("0"):
                    print(
                        f"[SKIP] No hay suficiente balance para comprar la mínima cantidad (step_size)."
                    )
                    return None
                qty_adjusted = max_qty
                qty_str = format(
                    qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f"
                )
                if "." in qty_str:
                    qty_str = qty_str.rstrip("0").rstrip(".")
                order_value = float(Decimal(qty_str) * price_d)
                print(
                    f"[INFO] Recortado qty por saldo: qty={qty_str} (≈{order_value:.2f} USDT)"
                )

            # último chequeo min_notional
            if order_value < min_notional:
                print(
                    f"[SKIP] order_value {order_value:.2f} < min_notional {min_notional:.2f} tras ajustes."
                )
                return None

            print(
                f"[INFO] BUY -> qty={qty_str} (≈{order_value:.2f} USDT) step_size={step_size_str}"
            )

            # dry run
            if self.dry in ["log", "sim"]:
                print(
                    f"[DRY-{self.dry.upper()}] Simulated BUY for {symbol} qty={qty_str} value≈{order_value:.2f} USDT"
                )
                return None

            # Ejecutar orden real (usando quantity).
            order = await self._run(
                self.client.new_order,
                symbol=symbol,
                side="BUY",
                type="MARKET",
                quantity=qty_str,
            )

            print(f"[TRADE] Market BUY executed: {order}")
            # Solo guardar entry price si la orden fue exitosa
            if order and order.get("status") in ["FILLED", "NEW"]:
                self.entry_prices[symbol] = price
                print(f"[ENTRY] {symbol} entry_price guardado: ${price:.2f}")

            return order

        except Exception as e:
            print(f"[ERROR] market_buy failed: {e}")
            return None

    # -----------------------------
    # ORDEN DE VENTA
    # -----------------------------
    async def market_sell(self, symbol, qty):
        """
        Ejecuta una orden de venta de mercado.
        Ajusta automáticamente la cantidad al mínimo permitido y usa
        todo el balance si se pide más del disponible (para asegurar ejecución).
        """
        try:
            # obtener precio actual
            pr = await self._run(self.client.ticker_price, symbol)
            price = float(pr["price"]) if isinstance(pr, dict) else float(pr)

            # Obtener filtros del exchange info
            info = await self._run(self.client.exchange_info, symbol=symbol)
            filters = {f["filterType"]: f for f in info["symbols"][0]["filters"]}
            step_size_str = filters["LOT_SIZE"]["stepSize"]
            step_size = Decimal(step_size_str)
            min_notional = float(filters["NOTIONAL"]["minNotional"])

            # obtener balance real de la moneda base (ej. BTC)
            bals = await self.get_balances()
            base_asset = symbol.replace("USDT", "")
            available_qty = Decimal(str(bals.get(base_asset, 0.0)))

            qty_d = Decimal(str(qty))

            # si piden vender más de lo disponible, usar lo disponible
            if qty_d > available_qty:
                qty_d = available_qty

            # ajustar cantidad al múltiplo del step_size (floor)
            qty_adjusted = (qty_d // step_size) * step_size

            # si tras floor queda 0, intentar usar step_size si hay suficiente balance
            if qty_adjusted <= Decimal("0"):
                if available_qty >= step_size:
                    qty_adjusted = step_size
                else:
                    print(
                        f"[SKIP] No hay suficiente {base_asset} para vender la mínima cantidad (step_size)."
                    )
                    return None

            # formatear qty
            if "." in step_size_str:
                step_decimals = len(step_size_str.rstrip("0").split(".")[1])
            else:
                step_decimals = 0

            qty_str = format(
                qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f"
            )
            if "." in qty_str:
                qty_str = qty_str.rstrip("0").rstrip(".")

            order_value = float(qty_adjusted * Decimal(str(price)))

            # Si el valor total < min_notional, intentar elevar qty al mínimo notional
            if order_value < min_notional:
                min_qty = Decimal(str(min_notional)) / Decimal(str(price))
                times = (min_qty / step_size).to_integral_value(rounding=ROUND_UP)
                needed_qty = times * step_size

                # si no tenemos suficiente balance para el needed_qty -> skip
                if needed_qty > available_qty:
                    print(
                        f"[SKIP] Necesitaríamos {needed_qty} {base_asset} para alcanzar min_notional, disponible {available_qty}."
                    )
                    return None

                qty_adjusted = needed_qty
                qty_str = format(
                    qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f"
                )
                if "." in qty_str:
                    qty_str = qty_str.rstrip("0").rstrip(".")
                order_value = float(qty_adjusted * Decimal(str(price)))
                print(
                    f"[WARN] SELL ajustado a min_notional: qty={qty_str} (≈{order_value:.2f} USDT)"
                )

            # dry run
            if self.dry in ["log", "sim"]:
                print(
                    f"[DRY-{self.dry.upper()}] Simulated SELL for {symbol} qty={qty_str} value≈{order_value:.2f} USDT"
                )
                return None

            order = await self._run(
                self.client.new_order,
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=str(qty_adjusted),
            )

            print(f"[TRADE] Market SELL executed: {order}")
            # Solo limpiar entry price si la orden fue exitosa
            if order and order.get("status") in ["FILLED", "NEW"]:
                self.entry_prices.pop(symbol, None)
                print(f"[EXIT] {symbol} entry_price limpiado")

            return order

        except Exception as e:
            print(f"[ERROR] market_sell failed: {e}")
            return None

    
    # -----------------------------
    # ÓRDENES LIMIT (MAKER)
    # -----------------------------
    async def limit_buy(self, symbol, usdt_amount: float = None):
        """Intenta compra LIMIT (maker). Si no se llena en MAKER_WAIT_SECONDS, cancela y usa MARKET."""
        if not USE_MAKER_ORDERS:
            return await self.market_buy(symbol, usdt_amount)
        
        try:
            if usdt_amount is None:
                usdt_amount, reason = await self.compute_buy_usdt(symbol=symbol)
                if usdt_amount is None:
                    print(f"[SKIP] limit_buy: {reason}")
                    return None
            
            # Precio actual y precio limit (0.05% mejor para ser maker)
            pr = await self._run(self.client.ticker_price, symbol)
            market_price = float(pr["price"]) if isinstance(pr, dict) else float(pr)
            limit_price = market_price * (1 - MAKER_PRICE_OFFSET)
            
            # Calcular qty igual que market_buy
            bals = await self.get_balances()
            usdt_balance = bals.get("USDT", 0.0)
            if usdt_amount > usdt_balance:
                print(f"[SKIP] limit_buy: {usdt_amount:.2f} > balance {usdt_balance:.2f}")
                return None
            
            info = await self._run(self.client.exchange_info, symbol=symbol)
            filters = {f["filterType"]: f for f in info["symbols"][0]["filters"]}
            step_size_str = filters["LOT_SIZE"]["stepSize"]
            step_size = Decimal(step_size_str)
            price_filter = filters["PRICE_FILTER"]
            tick_size = Decimal(price_filter["tickSize"])
            
            # Ajustar limit_price al tick_size
            limit_price_d = Decimal(str(limit_price))
            limit_price_d = (limit_price_d // tick_size) * tick_size
            limit_price = float(limit_price_d)
            
            usdt_with_margin = Decimal(str(usdt_amount)) * Decimal(str(SAFETY_MARGIN))
            usdt_with_margin = min(usdt_with_margin, Decimal(str(usdt_balance)))
            qty = usdt_with_margin / Decimal(str(limit_price))
            qty_adjusted = (qty // step_size) * step_size
            
            if qty_adjusted <= Decimal("0"):
                qty_adjusted = step_size
            
            if "." in step_size_str:
                step_decimals = len(step_size_str.rstrip("0").split(".")[1])
            else:
                step_decimals = 0
            
            qty_str = format(qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f")
            if "." in qty_str:
                qty_str = qty_str.rstrip("0").rstrip(".")
            
            if self.dry in ["log", "sim"]:
                print(f"[DRY-{self.dry.upper()}] Simulated LIMIT BUY {symbol} qty={qty_str} price={limit_price:.2f}")
                return None
            
            # Enviar orden LIMIT
            print(f"[LIMIT] Colocando BUY {symbol} qty={qty_str} @ ${limit_price:.2f}")
            order = await self._run(
                self.client.new_order,
                symbol=symbol,
                side="BUY",
                type="LIMIT",
                timeInForce="GTC",
                quantity=qty_str,
                price=str(limit_price)
            )
            
            order_id = order["orderId"]
            
            # Esperar MAKER_WAIT_SECONDS
            await asyncio.sleep(MAKER_WAIT_SECONDS)
            
            # Verificar estado
            status = await self._run(self.client.get_order, symbol=symbol, orderId=order_id)
            
            if status["status"] == "FILLED":
                print(f"[LIMIT] BUY ejecutada como MAKER: {order}")
                if status.get("status") in ["FILLED"]:
                    self.entry_prices[symbol] = limit_price
                    print(f"[ENTRY] {symbol} entry_price guardado: ${limit_price:.2f}")
                return order
            else:
                # Cancelar y usar MARKET
                print(f"[LIMIT] Orden no llenada, cancelando y usando MARKET")
                await self._run(self.client.cancel_order, symbol=symbol, orderId=order_id)
                return await self.market_buy(symbol, usdt_amount)
                
        except Exception as e:
            print(f"[ERROR] limit_buy failed: {e}, fallback a MARKET")
            return await self.market_buy(symbol, usdt_amount)
    
    async def limit_sell(self, symbol, qty):
        """Intenta venta LIMIT (maker). Si no se llena en MAKER_WAIT_SECONDS, cancela y usa MARKET."""
        if not USE_MAKER_ORDERS:
            return await self.market_sell(symbol, qty)
        
        try:
            # Precio actual y precio limit (0.05% mejor para ser maker)
            pr = await self._run(self.client.ticker_price, symbol)
            market_price = float(pr["price"]) if isinstance(pr, dict) else float(pr)
            limit_price = market_price * (1 + MAKER_PRICE_OFFSET)
            
            bals = await self.get_balances()
            base_asset = symbol.replace("USDT", "")
            available_qty = Decimal(str(bals.get(base_asset, 0.0)))
            qty_d = Decimal(str(qty))
            
            if qty_d > available_qty:
                qty_d = available_qty
            
            info = await self._run(self.client.exchange_info, symbol=symbol)
            filters = {f["filterType"]: f for f in info["symbols"][0]["filters"]}
            step_size_str = filters["LOT_SIZE"]["stepSize"]
            step_size = Decimal(step_size_str)
            price_filter = filters["PRICE_FILTER"]
            tick_size = Decimal(price_filter["tickSize"])
            
            # Ajustar limit_price al tick_size
            limit_price_d = Decimal(str(limit_price))
            limit_price_d = (limit_price_d // tick_size) * tick_size
            limit_price = float(limit_price_d)
            
            qty_adjusted = (qty_d // step_size) * step_size
            
            if qty_adjusted <= Decimal("0"):
                if available_qty >= step_size:
                    qty_adjusted = step_size
                else:
                    print(f"[SKIP] No hay suficiente {base_asset} para vender")
                    return None
            
            if "." in step_size_str:
                step_decimals = len(step_size_str.rstrip("0").split(".")[1])
            else:
                step_decimals = 0
            
            qty_str = format(qty_adjusted.quantize(Decimal(1).scaleb(-step_decimals)), "f")
            if "." in qty_str:
                qty_str = qty_str.rstrip("0").rstrip(".")
            
            if self.dry in ["log", "sim"]:
                print(f"[DRY-{self.dry.upper()}] Simulated LIMIT SELL {symbol} qty={qty_str} price={limit_price:.2f}")
                return None
            
            # Enviar orden LIMIT
            print(f"[LIMIT] Colocando SELL {symbol} qty={qty_str} @ ${limit_price:.2f}")
            order = await self._run(
                self.client.new_order,
                symbol=symbol,
                side="SELL",
                type="LIMIT",
                timeInForce="GTC",
                quantity=qty_str,
                price=str(limit_price)
            )
            
            order_id = order["orderId"]
            
            # Esperar MAKER_WAIT_SECONDS
            await asyncio.sleep(MAKER_WAIT_SECONDS)
            
            # Verificar estado
            status = await self._run(self.client.get_order, symbol=symbol, orderId=order_id)
            
            if status["status"] == "FILLED":
                print(f"[LIMIT] SELL ejecutada como MAKER: {order}")
                if status.get("status") in ["FILLED"]:
                    self.entry_prices.pop(symbol, None)
                    print(f"[EXIT] {symbol} entry_price limpiado")
                return order
            else:
                # Cancelar y usar MARKET
                print(f"[LIMIT] Orden no llenada, cancelando y usando MARKET")
                await self._run(self.client.cancel_order, symbol=symbol, orderId=order_id)
                return await self.market_sell(symbol, qty)
                
        except Exception as e:
            print(f"[ERROR] limit_sell failed: {e}, fallback a MARKET")
            return await self.market_sell(symbol, qty)

    # -----------------------------
    # CALCULO STOPLOSS
    # -----------------------------
    def check_stop_loss(self, symbol, current_price):
        """
        Verifica si el precio actual ha alcanzado el stop loss
        
        Args:
            symbol: Par a verificar (ej: BTCUSDT)
            current_price: Precio actual de mercado
        
        Returns:
            bool: True si debe ejecutar stop loss, False si no
        """
        if symbol not in self.entry_prices:
            return False  # No hay posición abierta
        
        entry_price = self.entry_prices[symbol]
        stop_loss_pct = float(os.getenv("STOP_LOSS_PERCENT", "0.01"))
        
        # Validar que el stop loss percent esté configurado correctamente
        if stop_loss_pct <= 0 or stop_loss_pct >= 1:
            print(f"[WARN] STOP_LOSS_PERCENT inválido ({stop_loss_pct}), usando default 0.01")
            stop_loss_pct = 0.01
        
        # Calcular precio de stop loss
        stop_loss_price = entry_price * (1 - stop_loss_pct)
        
        # Verificar si el precio cayó por debajo del stop
        if current_price <= stop_loss_price:
            loss_pct = ((current_price - entry_price) / entry_price) * 100
            print(f"[STOP LOSS] {symbol}: Entrada=${entry_price:.2f} | Actual=${current_price:.2f} | Pérdida={loss_pct:.2f}%")
            return True
        
        return False
import time
import os
from dotenv import load_dotenv

load_dotenv()

class Simulator:
    def __init__(self, start_usdt=1000.0, fee_pct=0.0006):
        self.usdt = start_usdt
        self.btc = 0.0
        self.fee = fee_pct
        self.history = []
        self.entry_price = None

    def buy_market(self, price, usdt_amount):
        qty = (usdt_amount * (1 - self.fee)) / price
        self.btc += qty
        self.usdt -= usdt_amount
        self.entry_price = price
        self.history.append(('buy', time.time(), price, qty, usdt_amount))
        return {'price': price, 'qty': qty}

    def sell_market(self, price, qty):
        usdt_gain = qty * price * (1 - self.fee)
        self.btc -= qty
        self.usdt += usdt_gain
        self.entry_price = None
        self.history.append(('sell', time.time(), price, qty, usdt_gain))
        return {'price': price, 'qty': qty, 'usdt': usdt_gain}

    def check_stop_loss(self, current_price):
        """Verifica si debe activar stop loss
        
        Args:
            current_price: Precio actual de mercado
            
        Returns:
            bool: True si debe ejecutar stop loss, False si no
        """
        if self.entry_price is None or self.btc <= 0:
            return False
        
        # Leer configuración desde .env (igual que en Exchange)
        stop_loss_pct = float(os.getenv("STOP_LOSS_PERCENT", "0.01"))
        
        # Validar que el stop loss percent esté configurado correctamente
        if stop_loss_pct <= 0 or stop_loss_pct >= 1:
            print(f"[WARN] STOP_LOSS_PERCENT inválido ({stop_loss_pct}), usando default 0.01")
            stop_loss_pct = 0.01
        
        stop_loss_price = self.entry_price * (1 - stop_loss_pct)
        
        if current_price <= stop_loss_price:
            loss_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            print(f"[SIMULATOR STOP LOSS] Entrada=${self.entry_price:.2f} | Actual=${current_price:.2f} | Pérdida={loss_pct:.2f}%")
            return True
        
        return False
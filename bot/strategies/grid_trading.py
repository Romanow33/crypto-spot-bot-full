"""
Grid Trading Strategy
Coloca órdenes de compra/venta en una grilla de precios
"""

import os
from dotenv import load_dotenv

load_dotenv()


class GridStrategy:
    def __init__(
        self,
        lower_price: float,
        upper_price: float,
        num_grids: int = 10,
        investment_per_grid: float = 100.0
    ):
        """
        Args:
            lower_price: Precio mínimo del grid
            upper_price: Precio máximo del grid
            num_grids: Número de niveles en el grid
            investment_per_grid: USDT por cada nivel
        """
        self.lower_price = lower_price
        self.upper_price = upper_price
        self.num_grids = num_grids
        self.investment_per_grid = investment_per_grid
        
        # Calcular niveles del grid
        self.grid_step = (upper_price - lower_price) / (num_grids - 1)
        self.grid_levels = [
            lower_price + (i * self.grid_step) 
            for i in range(num_grids)
        ]
        
        # Estado: qué niveles tienen posición abierta
        self.positions = {level: False for level in self.grid_levels}
        
    def get_signal(self, current_price: float):
        """
        Retorna señal basada en precio actual
        
        Returns:
            tuple: (signal, target_level, reason)
                signal: 1=buy, -1=sell, 0=hold
                target_level: precio del grid a ejecutar
                reason: descripción
        """
        # Verificar si precio está fuera del rango
        if current_price < self.lower_price:
            return 0, None, f"Precio {current_price:.2f} por debajo del grid ({self.lower_price:.2f})"
        
        if current_price > self.upper_price:
            return 0, None, f"Precio {current_price:.2f} por encima del grid ({self.upper_price:.2f})"
        
        # Encontrar nivel más cercano
        closest_level = min(self.grid_levels, key=lambda x: abs(x - current_price))
        distance = abs(current_price - closest_level)
        
        # Si está muy cerca del nivel (dentro de 0.1% del step)
        threshold = self.grid_step * 0.001
        
        if distance < threshold:
            # Comprar en niveles sin posición
            if not self.positions[closest_level]:
                return 1, closest_level, f"BUY at grid level {closest_level:.2f}"
            
            # Vender en niveles con posición (cuando precio sube a nivel superior)
            next_level_up = closest_level + self.grid_step
            if next_level_up in self.grid_levels and self.positions[closest_level]:
                return -1, closest_level, f"SELL at grid level {closest_level:.2f} (profit target)"
        
        return 0, None, "No action - waiting for grid level"
    
    def execute_buy(self, level: float):
        """Marca nivel como comprado"""
        if level in self.positions:
            self.positions[level] = True
            return True
        return False
    
    def execute_sell(self, level: float):
        """Marca nivel como vendido"""
        if level in self.positions:
            self.positions[level] = False
            return True
        return False
    
    def get_status(self):
        """Retorna estado actual del grid"""
        active_positions = sum(1 for v in self.positions.values() if v)
        return {
            'total_levels': self.num_grids,
            'active_positions': active_positions,
            'grid_range': f"${self.lower_price:.2f} - ${self.upper_price:.2f}",
            'grid_step': f"${self.grid_step:.2f}",
            'positions': self.positions
        }


def create_grid_from_current_price(
    current_price: float,
    grid_range_pct: float = 0.10,  # ±10% del precio actual
    num_grids: int = 10
):
    """
    Crea grid centrado en precio actual
    
    Args:
        current_price: Precio actual de mercado
        grid_range_pct: Rango del grid como % del precio (0.10 = ±10%)
        num_grids: Número de niveles
    
    Returns:
        GridStrategy instance
    """
    lower_price = current_price * (1 - grid_range_pct)
    upper_price = current_price * (1 + grid_range_pct)
    
    return GridStrategy(
        lower_price=lower_price,
        upper_price=upper_price,
        num_grids=num_grids
    )

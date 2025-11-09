"""
Grid Trading Backtester
Simula estrategia de grid trading sobre datos históricos
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.strategies.grid_trading import GridStrategy, create_grid_from_current_price
from dotenv import load_dotenv

load_dotenv()


class GridBacktester:
    def __init__(self, initial_capital=1000.0, fee_rate=0.0004):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.usdt = initial_capital
        self.btc = 0.0
        self.trades = []
        self.equity_curve = []
        
    def run(self, df, grid_range_pct=0.05, num_grids=10, investment_per_level=10.0):
        """Ejecutar backtest de grid trading"""
        
        # Crear grid basado en primer precio
        first_price = float(df.iloc[0]['close'])
        grid = create_grid_from_current_price(first_price, grid_range_pct, num_grids)
        
        print(f"\nGrid configurado:")
        print(f"  Rango: ${grid.lower_price:.2f} - ${grid.upper_price:.2f}")
        print(f"  Niveles: {num_grids}")
        print(f"  Step: ${grid.grid_step:.2f}")
        print(f"  Investment por nivel: ${investment_per_level:.2f}")
        
        # Simular sobre cada precio
        for i, row in df.iterrows():
            price = float(row['close'])
            timestamp = row['open_time'] if 'open_time' in row else i
            
            signal, target_level, reason = grid.get_signal(price)
            
            if signal == 1:  # BUY
                if self.usdt >= investment_per_level:
                    qty = (investment_per_level * (1 - self.fee_rate)) / price
                    self.btc += qty
                    self.usdt -= investment_per_level
                    grid.execute_buy(target_level)
                    
                    self.trades.append({
                        'timestamp': timestamp,
                        'type': 'BUY',
                        'price': price,
                        'qty': qty,
                        'usdt': investment_per_level,
                        'grid_level': target_level,
                        'fee': investment_per_level * self.fee_rate
                    })
            
            elif signal == -1:  # SELL
                # Vender porción del grid level
                active_positions = sum(1 for v in grid.positions.values() if v)
                if active_positions > 0 and self.btc > 0:
                    qty_to_sell = self.btc / active_positions
                    usdt_gain = qty_to_sell * price * (1 - self.fee_rate)
                    
                    self.usdt += usdt_gain
                    self.btc -= qty_to_sell
                    grid.execute_sell(target_level)
                    
                    self.trades.append({
                        'timestamp': timestamp,
                        'type': 'SELL',
                        'price': price,
                        'qty': qty_to_sell,
                        'usdt': usdt_gain,
                        'grid_level': target_level,
                        'fee': qty_to_sell * price * self.fee_rate
                    })
            
            # Registrar equity
            equity = self.usdt + (self.btc * price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'price': price,
                'equity': equity,
                'usdt': self.usdt,
                'btc': self.btc
            })
        
        return self.calculate_metrics(grid)
    
    def calculate_metrics(self, grid):
        """Calcular métricas de performance"""
        
        final_equity = self.usdt + (self.btc * float(self.equity_curve[-1]['price']))
        total_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        buys = [t for t in self.trades if t['type'] == 'BUY']
        sells = [t for t in self.trades if t['type'] == 'SELL']
        
        # Profit por trade completado
        completed_profits = []
        for sell in sells:
            # Buscar compra previa en mismo nivel
            matching_buys = [b for b in buys if b['grid_level'] == sell['grid_level']]
            if matching_buys:
                buy = matching_buys[-1]
                profit = sell['usdt'] - buy['usdt']
                profit_pct = (profit / buy['usdt']) * 100
                completed_profits.append(profit_pct)
        
        avg_profit_per_trade = np.mean(completed_profits) if completed_profits else 0
        
        # Max drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        # Sharpe
        returns = equity_df['equity'].pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        
        total_fees = sum([t['fee'] for t in self.trades])
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return_pct': total_return,
            'total_trades': len(self.trades),
            'buy_orders': len(buys),
            'sell_orders': len(sells),
            'completed_cycles': len(completed_profits),
            'avg_profit_per_cycle_pct': avg_profit_per_trade,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe,
            'total_fees': total_fees,
            'final_usdt': self.usdt,
            'final_btc': self.btc
        }


def print_grid_report(metrics):
    """Imprimir reporte de grid trading"""
    print("\n" + "="*60)
    print("GRID TRADING BACKTEST RESULTS")
    print("="*60)
    
    print(f"\n💰 CAPITAL")
    print(f"  Initial:       ${metrics['initial_capital']:,.2f}")
    print(f"  Final Equity:  ${metrics['final_equity']:,.2f}")
    print(f"  Final USDT:    ${metrics['final_usdt']:,.2f}")
    print(f"  Final BTC:     {metrics['final_btc']:.6f}")
    print(f"  Total Return:  {metrics['total_return_pct']:+.2f}%")
    
    print(f"\n📊 TRADING ACTIVITY")
    print(f"  Total Orders:      {metrics['total_trades']}")
    print(f"  Buy Orders:        {metrics['buy_orders']}")
    print(f"  Sell Orders:       {metrics['sell_orders']}")
    print(f"  Completed Cycles:  {metrics['completed_cycles']}")
    
    print(f"\n🎯 PERFORMANCE")
    print(f"  Avg Profit/Cycle:  {metrics['avg_profit_per_cycle_pct']:+.2f}%")
    print(f"  Max Drawdown:      {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio:      {metrics['sharpe_ratio']:.2f}")
    print(f"  Total Fees:        ${metrics['total_fees']:.2f}")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Grid Trading Backtester')
    parser.add_argument('--data', default='data/raw/klines.csv')
    parser.add_argument('--capital', type=float, default=1000.0)
    parser.add_argument('--range', type=float, default=0.05, help='Grid range % (0.05 = 5%)')
    parser.add_argument('--levels', type=int, default=10)
    parser.add_argument('--invest', type=float, default=10.0, help='USDT per level')
    parser.add_argument('--start', help='Start date YYYY-MM-DD')
    parser.add_argument('--end', help='End date YYYY-MM-DD')
    
    args = parser.parse_args()
    
    print(f"🚀 Loading data: {args.data}")
    df = pd.read_csv(args.data)
    
    if 'open_time' in df.columns:
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        if args.start:
            df = df[df['open_time'] >= args.start]
        if args.end:
            df = df[df['open_time'] <= args.end]
    
    print(f"✓ Loaded {len(df)} periods")
    if 'open_time' in df.columns:
        print(f"  Range: {df['open_time'].min()} - {df['open_time'].max()}")
    
    print(f"\n⚙️  Configuration:")
    print(f"  Capital: ${args.capital:,.2f}")
    print(f"  Grid range: ±{args.range*100:.1f}%")
    print(f"  Grid levels: {args.levels}")
    print(f"  Investment/level: ${args.invest:.2f}")
    
    print("\n📊 Running grid backtest...")
    
    backtester = GridBacktester(
        initial_capital=args.capital,
        fee_rate=float(os.getenv('TRADE_FEE_RATE', 0.0004))
    )
    
    metrics = backtester.run(
        df,
        grid_range_pct=args.range,
        num_grids=args.levels,
        investment_per_level=args.invest
    )
    
    print_grid_report(metrics)
    print("\n✅ Grid backtest completed\n")

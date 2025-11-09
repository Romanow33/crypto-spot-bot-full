"""
Backtester completo para estrategia de trading
Incluye métricas detalladas, manejo de fees, y reportes
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from pathlib import Path

# Agregar path del bot para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.strategy import compute_features, build_signals
from bot.ml_scorer import MLScorer
from dotenv import load_dotenv

load_dotenv()


class Backtester:
    def __init__(self, initial_capital=1000.0, fee_rate=0.0004, trade_percent=0.01):
        """
        Args:
            initial_capital: Capital inicial en USDT
            fee_rate: Tasa de comisión (0.0004 = 0.04% maker)
            trade_percent: Porcentaje del balance por trade (0.01 = 1%)
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.trade_percent = trade_percent
        
        # Estado actual
        self.usdt = initial_capital
        self.btc = 0.0
        self.entry_price = None
        
        # Historial
        self.trades = []
        self.equity_curve = []
        
    def reset(self):
        """Resetear backtester a estado inicial"""
        self.usdt = self.initial_capital
        self.btc = 0.0
        self.entry_price = None
        self.trades = []
        self.equity_curve = []
    
    def execute_buy(self, price, timestamp):
        """Ejecutar compra"""
        if self.btc > 0:  # Ya tiene posición
            return None
        
        usdt_amount = self.usdt * self.trade_percent
        if usdt_amount < 5.0:  # Min notional
            return None
        
        qty = (usdt_amount * (1 - self.fee_rate)) / price
        self.btc = qty
        self.usdt -= usdt_amount
        self.entry_price = price
        
        trade = {
            'timestamp': timestamp,
            'type': 'BUY',
            'price': price,
            'qty': qty,
            'usdt': usdt_amount,
            'fee': usdt_amount * self.fee_rate
        }
        self.trades.append(trade)
        return trade
    
    def execute_sell(self, price, timestamp):
        """Ejecutar venta"""
        if self.btc <= 0:  # No tiene posición
            return None
        
        usdt_gain = self.btc * price * (1 - self.fee_rate)
        pnl = usdt_gain - (self.btc * self.entry_price)
        pnl_pct = (price - self.entry_price) / self.entry_price * 100
        
        trade = {
            'timestamp': timestamp,
            'type': 'SELL',
            'price': price,
            'qty': self.btc,
            'usdt': usdt_gain,
            'fee': self.btc * price * self.fee_rate,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_price': self.entry_price
        }
        
        self.usdt += usdt_gain
        self.btc = 0.0
        self.entry_price = None
        self.trades.append(trade)
        return trade
    
    def get_equity(self, current_price):
        """Calcular equity total"""
        return self.usdt + (self.btc * current_price)
    
    def run(self, df, use_ml=True):
        """
        Ejecutar backtest sobre datos históricos
        
        Args:
            df: DataFrame con OHLCV data
            use_ml: Si usar ML scorer
        
        Returns:
            dict con resultados
        """
        self.reset()
        
        # Cargar ML scorer si está habilitado
        ml_scores = None
        if use_ml:
            try:
                ml = MLScorer(os.getenv("MODEL_PATH", "./models/model.pkl"))
                feats = compute_features(df.copy())
                if len(feats) > 0:
                    ml_scores = ml.predict(feats)
                else:
                    print(f"[WARN] No features computed, skipping ML")
                    use_ml = False
            except Exception as e:
                print(f"[WARN] ML scorer failed: {e}, continuando sin ML")
                use_ml = False
        
        # Generar señales
        sig_df = build_signals(df.copy(), ml_scores=ml_scores)
        
        # Simular trading
        print(f"[DEBUG] sig_df shape: {sig_df.shape}")
        print(f"[DEBUG] Signal counts: {sig_df['final'].value_counts().to_dict()}")
        
        # Verificar filtros
        buy_candidates = sig_df[(sig_df['ema_diff'] > 0) & (sig_df['rsi14'] < 70)]
        print(f"[DEBUG] Buy candidates (EMA+RSI): {len(buy_candidates)}")
        
        trend_pass = buy_candidates[buy_candidates['close'] > buy_candidates['sma50']]
        print(f"[DEBUG] Pass trend filter: {len(trend_pass)}")
        
        ml_pass = trend_pass[trend_pass['ml_score'] >= 0.65]
        print(f"[DEBUG] Pass ML filter (>=0.65): {len(ml_pass)}")
        
        print(f"[DEBUG] ML scores range: {sig_df['ml_score'].min():.3f} - {sig_df['ml_score'].max():.3f}")
        print(f"[DEBUG] ML scores mean: {sig_df['ml_score'].mean():.3f}")
        print(f"[DEBUG] ML scores >0.5: {len(sig_df[sig_df['ml_score'] > 0.5])}")
        print(f"[DEBUG] ML scores >0.6: {len(sig_df[sig_df['ml_score'] > 0.6])}")
        
        for i, row in sig_df.iterrows():
            price = float(row['close'])
            timestamp = df.iloc[i]['open_time'] if 'open_time' in df.columns else i
            sig = int(row['final'])
            
            # Ejecutar trades
            if sig == 1:
                self.execute_buy(price, timestamp)
            elif sig == -1:
                self.execute_sell(price, timestamp)
            
            # Guardar equity
            equity = self.get_equity(price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'price': price,
                'equity': equity,
                'usdt': self.usdt,
                'btc': self.btc
            })
        
        # Cerrar posición final si existe
        if self.btc > 0:
            final_price = float(sig_df.iloc[-1]['close'])
            final_timestamp = df.iloc[-1]['open_time'] if 'open_time' in df.columns else len(df)-1
            self.execute_sell(final_price, final_timestamp)
        
        return self.calculate_metrics()
    
    def calculate_metrics(self):
        """Calcular métricas de performance"""
        if len(self.trades) == 0:
            return {
                'error': 'No trades executed',
                'initial_capital': self.initial_capital,
                'final_capital': self.usdt
            }
        
        # Capital final
        final_capital = self.usdt
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        # Trades ganadores/perdedores
        sells = [t for t in self.trades if t['type'] == 'SELL']
        if len(sells) == 0:
            return {
                'error': 'No completed trades (sells)',
                'total_signals': len(self.trades),
                'initial_capital': self.initial_capital,
                'final_capital': final_capital
            }
        
        winners = [t for t in sells if t.get('pnl', 0) > 0]
        losers = [t for t in sells if t.get('pnl', 0) < 0]
        
        win_rate = (len(winners) / len(sells)) * 100 if sells else 0
        avg_win = np.mean([t['pnl_pct'] for t in winners]) if winners else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losers]) if losers else 0
        
        # Profit factor
        total_wins = sum([t['pnl'] for t in winners]) if winners else 0
        total_losses = abs(sum([t['pnl'] for t in losers])) if losers else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Max drawdown
        equity_curve = pd.DataFrame(self.equity_curve)
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak'] * 100
        max_drawdown = equity_curve['drawdown'].min()
        
        # Sharpe ratio (simplificado)
        returns = equity_curve['equity'].pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        
        # Total fees
        total_fees = sum([t.get('fee', 0) for t in self.trades])
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_return_pct': total_return,
            'total_trades': len(self.trades),
            'buy_signals': len([t for t in self.trades if t['type'] == 'BUY']),
            'sell_signals': len(sells),
            'completed_trades': len(sells),
            'win_rate': win_rate,
            'winners': len(winners),
            'losers': len(losers),
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'best_trade_pct': max([t['pnl_pct'] for t in sells]) if sells else 0,
            'worst_trade_pct': min([t['pnl_pct'] for t in sells]) if sells else 0,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe,
            'total_fees': total_fees,
            'avg_trade_duration': 'N/A'  # Requiere timestamps
        }
    
    def save_results(self, metrics, output_dir='backtester/results'):
        """Guardar resultados a archivos"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar métricas
        metrics_df = pd.DataFrame([metrics])
        metrics_path = f"{output_dir}/metrics_{timestamp}.csv"
        metrics_df.to_csv(metrics_path, index=False)
        
        # Guardar trades
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            trades_path = f"{output_dir}/trades_{timestamp}.csv"
            trades_df.to_csv(trades_path, index=False)
        
        # Guardar equity curve
        if self.equity_curve:
            equity_df = pd.DataFrame(self.equity_curve)
            equity_path = f"{output_dir}/equity_{timestamp}.csv"
            equity_df.to_csv(equity_path, index=False)
        
        return {
            'metrics': metrics_path,
            'trades': trades_path if self.trades else None,
            'equity': equity_path if self.equity_curve else None
        }


def load_historical_data(csv_path, start_date=None, end_date=None):
    """Cargar datos históricos con filtro opcional de fechas"""
    df = pd.read_csv(csv_path)
    
    # Convertir open_time a datetime si existe
    if 'open_time' in df.columns:
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        
        if start_date:
            df = df[df['open_time'] >= start_date]
        if end_date:
            df = df[df['open_time'] <= end_date]
    
    return df


def print_report(metrics):
    """Imprimir reporte formateado"""
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    if 'error' in metrics:
        print(f"\n⚠️  ERROR: {metrics['error']}")
        print(f"Total signals: {metrics.get('total_signals', 0)}")
        print(f"Initial: ${metrics['initial_capital']:.2f}")
        print(f"Final: ${metrics['final_capital']:.2f}")
        return
    
    print(f"\n💰 CAPITAL")
    print(f"  Initial:       ${metrics['initial_capital']:,.2f}")
    print(f"  Final:         ${metrics['final_capital']:,.2f}")
    print(f"  Total Return:  {metrics['total_return']:+.2f}%")
    
    print(f"\n📊 TRADING ACTIVITY")
    print(f"  Total Trades:     {metrics['total_trades']}")
    print(f"  Completed:        {metrics['completed_trades']}")
    print(f"  Buy Signals:      {metrics['buy_signals']}")
    print(f"  Sell Signals:     {metrics['sell_signals']}")
    
    print(f"\n🎯 PERFORMANCE")
    print(f"  Win Rate:         {metrics['win_rate']:.1f}%")
    print(f"  Winners:          {metrics['winners']}")
    print(f"  Losers:           {metrics['losers']}")
    print(f"  Avg Win:          {metrics['avg_win_pct']:+.2f}%")
    print(f"  Avg Loss:         {metrics['avg_loss_pct']:+.2f}%")
    print(f"  Best Trade:       {metrics['best_trade_pct']:+.2f}%")
    print(f"  Worst Trade:      {metrics['worst_trade_pct']:+.2f}%")
    
    print(f"\n📈 METRICS")
    print(f"  Profit Factor:    {metrics['profit_factor']:.2f}")
    print(f"  Max Drawdown:     {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
    print(f"  Total Fees:       ${metrics['total_fees']:.2f}")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtester de estrategia de trading')
    parser.add_argument('--data', default='data/raw/klines.csv', help='Path al CSV de datos')
    parser.add_argument('--capital', type=float, default=1000.0, help='Capital inicial')
    parser.add_argument('--start', help='Fecha inicio (YYYY-MM-DD)')
    parser.add_argument('--end', help='Fecha fin (YYYY-MM-DD)')
    parser.add_argument('--no-ml', action='store_true', help='Deshabilitar ML scorer')
    parser.add_argument('--save', action='store_true', help='Guardar resultados a archivos')
    
    args = parser.parse_args()
    
    print(f"\n🚀 Cargando datos desde: {args.data}")
    df = load_historical_data(args.data, start_date=args.start, end_date=args.end)
    print(f"✓ Cargados {len(df)} períodos")
    
    if 'open_time' in df.columns:
        print(f"  Rango: {df['open_time'].min()} - {df['open_time'].max()}")
    
    print(f"\n⚙️  Configuración:")
    print(f"  Capital inicial: ${args.capital:,.2f}")
    print(f"  Usar ML: {'No' if args.no_ml else 'Sí'}")
    print(f"  Fee rate: {float(os.getenv('TRADE_FEE_RATE', 0.0004)) * 100}%")
    
    print("\n📊 Ejecutando backtest...")
    backtester = Backtester(
        initial_capital=args.capital,
        fee_rate=float(os.getenv('TRADE_FEE_RATE', 0.0004)),
        trade_percent=float(os.getenv('TRADE_PERCENT', 0.01))
    )
    
    metrics = backtester.run(df, use_ml=not args.no_ml)
    print_report(metrics)
    
    if args.save:
        print("\n💾 Guardando resultados...")
        paths = backtester.save_results(metrics)
        print(f"  Métricas: {paths['metrics']}")
        if paths['trades']:
            print(f"  Trades: {paths['trades']}")
        if paths['equity']:
            print(f"  Equity curve: {paths['equity']}")
    
    print("\n✅ Backtest completado\n")

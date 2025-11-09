#!/usr/bin/env python3
"""
Analizador de logs para el bot de trading
Proporciona estadísticas y análisis de trades y balances
"""

import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class LogAnalyzer:
    def __init__(self, log_file):
        self.log_file = Path(log_file)
        self.balances = []
        self.signals = []
        self.trades = []
        self.errors = []
        
        if not self.log_file.exists():
            raise FileNotFoundError(f"Log file not found: {log_file}")
        
        self._parse_logs()
    
    def _parse_logs(self):
        """Parsea el archivo de logs"""
        with open(self.log_file, 'r') as f:
            for line in f:
                self._parse_line(line)
    
    def _parse_line(self, line):
        """Parsea una línea individual del log"""
        try:
            # Extraer timestamp
            timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if not timestamp_match:
                return
            
            timestamp = timestamp_match.group(1)
            
            # Balance log
            if '[BALANCE]' in line:
                match = re.search(r'USDT=([\d.]+) \| BTC=([\d.]+)', line)
                if match:
                    self.balances.append({
                        'timestamp': timestamp,
                        'usdt': float(match.group(1)),
                        'btc': float(match.group(2))
                    })
            
            # Signal log
            elif '[SIGNAL]' in line:
                match = re.search(
                    r'Type=(\w+) \| Price=([\d.]+) \| EMA9=([\d.]+) \| EMA21=([\d.]+) \| RSI=([\d.]+)',
                    line
                )
                if match:
                    self.signals.append({
                        'timestamp': timestamp,
                        'type': match.group(1),
                        'price': float(match.group(2)),
                        'ema9': float(match.group(3)),
                        'ema21': float(match.group(4)),
                        'rsi': float(match.group(5))
                    })
            
            # Trade log
            elif '[TRADE]' in line:
                match = re.search(
                    r'Type=(\w+) \| Symbol=(\w+) \| Qty=([\w.]+) \| Price=([\d.]+) \| USDT=([\d.]+) \| Status=(\w+)',
                    line
                )
                if match:
                    self.trades.append({
                        'timestamp': timestamp,
                        'type': match.group(1),
                        'symbol': match.group(2),
                        'quantity': match.group(3),
                        'price': float(match.group(4)),
                        'usdt': float(match.group(5)),
                        'status': match.group(6)
                    })
            
            # Error log
            elif '[ERROR]' in line:
                self.errors.append({'timestamp': timestamp, 'message': line.strip()})
        
        except Exception as e:
            pass  # Ignorar líneas que no parseen correctamente
    
    def get_summary(self):
        """Retorna un resumen de las estadísticas"""
        if not self.balances:
            return "No balance data found"
        
        initial_balance = self.balances[0]
        final_balance = self.balances[-1]
        
        # Calcular P&L en USDT
        pnl_usdt = final_balance['usdt'] - initial_balance['usdt']
        pnl_percent = (pnl_usdt / initial_balance['usdt'] * 100) if initial_balance['usdt'] > 0 else 0
        
        # Estadísticas de trades
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        simulated_trades = [t for t in self.trades if t['status'] == 'SIMULATED']
        executed_trades = [t for t in self.trades if t['status'] == 'EXECUTED']
        
        # Estadísticas de señales
        buy_signals = [s for s in self.signals if s['type'] == 'BUY']
        sell_signals = [s for s in self.signals if s['type'] == 'SELL']
        
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║           RESUMEN DE ANÁLISIS DE LOGS - BOT TRADING            ║
╚════════════════════════════════════════════════════════════════╝

📊 PERIODO DE EJECUCIÓN:
   Inicio:           {initial_balance['timestamp']}
   Final:            {final_balance['timestamp']}
   Snapshots:        {len(self.balances)} registros

💰 BALANCE & P&L:
   USDT Inicial:     ${initial_balance['usdt']:.2f}
   USDT Final:       ${final_balance['usdt']:.2f}
   BTC Inicial:      {initial_balance['btc']:.6f}
   BTC Final:        {final_balance['btc']:.6f}
   P&L USDT:         ${pnl_usdt:+.2f}
   P&L %:            {pnl_percent:+.2f}%
   
   {"🟢 GANANCIA" if pnl_usdt >= 0 else "🔴 PÉRDIDA"}

📈 SEÑALES GENERADAS:
   BUY Signals:      {len(buy_signals)}
   SELL Signals:     {len(sell_signals)}
   Total Signals:    {len(self.signals)}

🔄 TRADES EJECUTADOS:
   Total Trades:     {len(self.trades)}
   BUY Orders:       {len(buy_trades)}
   SELL Orders:      {len(sell_trades)}
   Simulados:        {len(simulated_trades)}
   Ejecutados:       {len(executed_trades)}
   
   USDT Total Traded: ${sum(t['usdt'] for t in self.trades):.2f}

⚠️  ERRORES:
   Total Errors:     {len(self.errors)}
"""
        
        if self.errors:
            summary += "\n   Primeros 3 errores:\n"
            for err in self.errors[:3]:
                summary += f"   - {err['timestamp']}: {err['message'][:80]}...\n"
        
        summary += "\n╚════════════════════════════════════════════════════════════════╝\n"
        return summary
    
    def get_detailed_trades(self):
        """Retorna detalle de todos los trades"""
        if not self.trades:
            return "No trades found"
        
        report = "\n📋 DETALLE DE TRADES:\n"
        report += "─" * 100 + "\n"
        report += f"{'#':<4} {'Timestamp':<20} {'Type':<6} {'Symbol':<8} {'Qty':<12} {'Price':<10} {'USDT':<10} {'Status':<10}\n"
        report += "─" * 100 + "\n"
        
        for i, trade in enumerate(self.trades, 1):
            report += f"{i:<4} {trade['timestamp']:<20} {trade['type']:<6} {trade['symbol']:<8} "
            report += f"{trade['quantity']:<12} ${trade['price']:<9.2f} ${trade['usdt']:<9.2f} {trade['status']:<10}\n"
        
        report += "─" * 100 + "\n"
        return report
    
    def get_balance_evolution(self):
        """Retorna la evolución del balance"""
        if not self.balances:
            return "No balance data"
        
        report = "\n💹 EVOLUCIÓN DE BALANCE:\n"
        report += "─" * 70 + "\n"
        report += f"{'Timestamp':<20} {'USDT':<15} {'BTC':<15} {'Cambio':<15}\n"
        report += "─" * 70 + "\n"
        
        prev_usdt = self.balances[0]['usdt']
        
        # Mostrar cada 10 registros para no saturar
        step = max(1, len(self.balances) // 20)
        
        for i, bal in enumerate(self.balances):
            if i % step == 0 or i == len(self.balances) - 1:
                change = bal['usdt'] - prev_usdt
                report += f"{bal['timestamp']:<20} ${bal['usdt']:<14.2f} {bal['btc']:<15.6f} ${change:+.2f}\n"
                prev_usdt = bal['usdt']
        
        report += "─" * 70 + "\n"
        return report
    
    def get_signals_analysis(self):
        """Retorna análisis de señales"""
        if not self.signals:
            return "No signals found"
        
        report = "\n🎯 ANÁLISIS DE SEÑALES:\n"
        report += "─" * 80 + "\n"
        report += f"{'Timestamp':<20} {'Type':<6} {'Price':<10} {'EMA9':<10} {'EMA21':<10} {'RSI':<8}\n"
        report += "─" * 80 + "\n"
        
        # Mostrar cada 5 señales
        step = max(1, len(self.signals) // 15)
        
        for i, sig in enumerate(self.signals):
            if i % step == 0 or i == len(self.signals) - 1:
                report += f"{sig['timestamp']:<20} {sig['type']:<6} ${sig['price']:<9.2f} "
                report += f"{sig['ema9']:<10.2f} {sig['ema21']:<10.2f} {sig['rsi']:<8.2f}\n"
        
        report += "─" * 80 + "\n"
        return report


def main():
    """Función principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python scripts/analyze_logs.py <log_file> [--summary|--trades|--balance|--signals|--all]")
        print("\nEjemplos:")
        print("  python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log")
        print("  python scripts/analyze_logs.py logs/2025-10-08_TEST_DEV.log --all")
        return
    
    log_file = sys.argv[1]
    report_type = sys.argv[2] if len(sys.argv) > 2 else "--summary"
    
    try:
        analyzer = LogAnalyzer(log_file)
        
        print(f"\n📂 Analizando: {log_file}\n")
        
        if report_type in ["--summary", "--all"]:
            print(analyzer.get_summary())
        
        if report_type in ["--trades", "--all"]:
            print(analyzer.get_detailed_trades())
        
        if report_type in ["--balance", "--all"]:
            print(analyzer.get_balance_evolution())
        
        if report_type in ["--signals", "--all"]:
            print(analyzer.get_signals_analysis())
        
        if report_type == "--summary":
            print("\n💡 Tip: Usa --all para ver todos los reportes, o especifica uno:")
            print("   --trades    para ver detalle de trades")
            print("   --balance   para ver evolución de balance")
            print("   --signals   para ver análisis de señales\n")
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error al analizar logs: {e}")


if __name__ == "__main__":
    main()

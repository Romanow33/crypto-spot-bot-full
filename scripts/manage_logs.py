#!/usr/bin/env python3
"""
Gestor de logs - Limpia y organiza archivos de logs
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta


class LogManager:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(exist_ok=True)
    
    def list_logs(self):
        """Lista todos los logs disponibles"""
        logs = sorted(self.logs_dir.glob("*.log"))
        
        if not logs:
            print("❌ No logs found")
            return []
        
        print(f"\n📋 Logs disponibles ({len(logs)} archivos):\n")
        
        for i, log_file in enumerate(logs, 1):
            size_kb = log_file.stat().st_size / 1024
            mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            print(f"  {i}. {log_file.name:<40} ({size_kb:>8.2f} KB) - {mod_time.strftime('%Y-%m-%d %H:%M')}")
        
        return logs
    
    def cleanup_old_logs(self, days=7):
        """Limpia logs más antiguos que X días"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted = 0
        
        print(f"\n🧹 Limpiando logs más antiguos a {days} días...\n")
        
        for log_file in self.logs_dir.glob("*.log"):
            mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if mod_time < cutoff_date:
                try:
                    log_file.unlink()
                    print(f"  ✓ Eliminado: {log_file.name}")
                    deleted += 1
                except Exception as e:
                    print(f"  ✗ Error al eliminar {log_file.name}: {e}")
        
        print(f"\n✅ Se eliminaron {deleted} logs antiguos")
    
    def archive_logs(self, archive_dir="logs_archive"):
        """Archiva logs en subcarpeta por fecha"""
        archive_path = Path(archive_dir)
        archive_path.mkdir(exist_ok=True)
        
        archived = 0
        
        print(f"\n📦 Archivando logs en {archive_dir}...\n")
        
        for log_file in self.logs_dir.glob("*.log"):
            # Extraer fecha del nombre: 2025-10-08_TEST_DEV.log
            try:
                date_str = log_file.name.split('_')[0]  # 2025-10-08
                date_folder = archive_path / date_str
                date_folder.mkdir(exist_ok=True)
                
                dest = date_folder / log_file.name
                shutil.move(str(log_file), str(dest))
                print(f"  ✓ Archivado: {log_file.name} → {date_str}/")
                archived += 1
            except Exception as e:
                print(f"  ✗ Error al archivar {log_file.name}: {e}")
        
        print(f"\n✅ Se archivaron {archived} logs")
    
    def get_today_logs(self):
        """Retorna logs de hoy"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_logs = list(self.logs_dir.glob(f"{today}_*.log"))
        
        return today_logs
    
    def get_statistics(self):
        """Muestra estadísticas de logs"""
        logs = list(self.logs_dir.glob("*.log"))
        
        if not logs:
            print("❌ No logs found")
            return
        
        total_size = sum(f.stat().st_size for f in logs)
        total_size_mb = total_size / (1024 * 1024)
        
        # Agrupar por modo (TEST/PROD)
        test_logs = [f for f in logs if 'TEST' in f.name]
        prod_logs = [f for f in logs if 'PROD' in f.name]
        
        print(f"""
╔════════════════════════════════════════════════════════════════╗
║              ESTADÍSTICAS DE LOGS                             ║
╚════════════════════════════════════════════════════════════════╝

📊 GENERAL:
   Total logs:       {len(logs)}
   Tamaño total:     {total_size_mb:.2f} MB
   Logs por día:     {len(logs) / (len(set(f.name.split('_')[0] for f in logs)) or 1):.1f}

🧪 TEST:
   Archivos:         {len(test_logs)}
   Tamaño:           {sum(f.stat().st_size for f in test_logs) / 1024:.2f} KB

🚀 PRODUCCIÓN:
   Archivos:         {len(prod_logs)}
   Tamaño:           {sum(f.stat().st_size for f in prod_logs) / 1024:.2f} KB

📅 POR ENTORNO:
   DEV:              {len([f for f in logs if '_DEV' in f.name])} logs
   PROD:             {len([f for f in logs if '_PROD' in f.name])} logs

╚════════════════════════════════════════════════════════════════╝
""")


def main():
    """Función principal"""
    import sys
    
    manager = LogManager()
    
    if len(sys.argv) < 2:
        print("""
📋 GESTOR DE LOGS - Bot Trading

Uso: python scripts/manage_logs.py <comando> [opciones]

Comandos:
   list              - Listar todos los logs
   stats             - Ver estadísticas de logs
   cleanup [días]    - Limpiar logs antiguos (default: 7 días)
   archive           - Archivar logs en subcarpetas
   today             - Ver logs de hoy

Ejemplos:
   python scripts/manage_logs.py list
   python scripts/manage_logs.py stats
   python scripts/manage_logs.py cleanup 30
   python scripts/manage_logs.py archive
   python scripts/manage_logs.py today
""")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "list":
            manager.list_logs()
        
        elif command == "stats":
            manager.get_statistics()
        
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            manager.cleanup_old_logs(days)
        
        elif command == "archive":
            manager.archive_logs()
        
        elif command == "today":
            today_logs = manager.get_today_logs()
            if today_logs:
                print(f"\n📅 Logs de hoy ({len(today_logs)} archivos):\n")
                for log in today_logs:
                    size_kb = log.stat().st_size / 1024
                    print(f"   • {log.name:<40} ({size_kb:>8.2f} KB)")
            else:
                print("\n❌ No logs para hoy")
        
        else:
            print(f"❌ Comando desconocido: {command}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

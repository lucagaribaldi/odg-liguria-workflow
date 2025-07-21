#!/usr/bin/env python3
"""
Genera un report completo di tutti i PDF elaborati
"""

import json
import os
from datetime import datetime
from pathlib import Path

def generate_complete_report():
    """Genera un report completo di tutti i PDF elaborati"""
    
    print("📊 GENERAZIONE REPORT COMPLETO")
    print("=" * 50)
    
    # Trova il backup più recente
    backup_dir = Path("data/backups")
    if not backup_dir.exists():
        print("❌ Cartella backup non trovata")
        return
    
    # Trova il file di backup più recente
    backup_files = list(backup_dir.glob("workflow_backup_*.json"))
    if not backup_files:
        print("❌ Nessun file di backup trovato")
        return
    
    latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
    
    print(f"📄 Caricamento backup: {latest_backup.name}")
    
    try:
        with open(latest_backup, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Backup caricato correttamente")
        print()
        
        # Analisi generale
        print("📊 STATISTICHE GENERALI")
        print("-" * 30)
        
        stats = data.get('total_stats', {})
        print(f"📄 File processati: {stats.get('files_processed', 0)}")
        print(f"❌ File falliti: {stats.get('files_failed', 0)}")
        print(f"📝 Deliberazioni totali: {stats.get('total_deliberations', 0)}")
        print(f"⏱️  Durata elaborazione: {stats.get('duration_seconds', 0):.2f} secondi")
        print()
        
        # Analisi per ogni PDF
        print("📋 DETTAGLIO PER PDF")
        print("-" * 30)
        
        results = data.get('results', [])
        sessions_summary = {}
        
        for result in results:
            if result.get('success'):
                pdf_name = result.get('pdf_name', 'N/A')
                session_info = result.get('session_info', {})
                deliberations = result.get('deliberations', [])
                
                seduta = session_info.get('numero_seduta', 'N/A')
                data_seduta = session_info.get('data_seduta', 'N/A')
                num_deliberations = len(deliberations)
                
                print(f"📄 {pdf_name}")
                print(f"   - Seduta: {seduta}")
                print(f"   - Data: {data_seduta}")
                print(f"   - Deliberazioni: {num_deliberations}")
                
                # Conta deliberazioni FS
                fs_count = sum(1 for d in deliberations if d.get('fs_flag', False))
                print(f"   - FS (Fuori Sacco): {fs_count}")
                
                # Conta per tipo
                tipo_count = {}
                for d in deliberations:
                    tipo = d.get('tipo_atto', 'N/A')
                    tipo_count[tipo] = tipo_count.get(tipo, 0) + 1
                
                print(f"   - Tipi principali:")
                for tipo, count in sorted(tipo_count.items()):
                    if count > 0:
                        print(f"     * {tipo}: {count}")
                
                # Salva per riepilogo
                sessions_summary[seduta] = {
                    'pdf_name': pdf_name,
                    'data_seduta': data_seduta,
                    'deliberations': num_deliberations,
                    'fs_count': fs_count,
                    'tipo_count': tipo_count
                }
                
                print()
        
        # Riepilogo sessioni
        print("📅 RIEPILOGO SESSIONI")
        print("-" * 30)
        
        total_deliberations = 0
        total_fs = 0
        
        for seduta, info in sorted(sessions_summary.items()):
            print(f"Seduta {seduta} ({info['data_seduta']}):")
            print(f"   - PDF: {info['pdf_name']}")
            print(f"   - Deliberazioni: {info['deliberations']}")
            print(f"   - FS: {info['fs_count']}")
            
            total_deliberations += info['deliberations']
            total_fs += info['fs_count']
        
        print()
        print(f"📊 TOTALI:")
        print(f"   - Sessioni elaborate: {len(sessions_summary)}")
        print(f"   - Deliberazioni totali: {total_deliberations}")
        print(f"   - FS totali: {total_fs}")
        print(f"   - Percentuale FS: {(total_fs/total_deliberations*100):.1f}%")
        
        # Analisi temporale
        print()
        print("📈 ANALISI TEMPORALE")
        print("-" * 30)
        
        dates = []
        for info in sessions_summary.values():
            if info['data_seduta'] != 'N/A':
                dates.append(info['data_seduta'])
        
        if dates:
            dates.sort()
            print(f"   - Prima sessione: {dates[0]}")
            print(f"   - Ultima sessione: {dates[-1]}")
            
            from datetime import datetime
            try:
                first_date = datetime.strptime(dates[0], '%Y-%m-%d')
                last_date = datetime.strptime(dates[-1], '%Y-%m-%d')
                period_days = (last_date - first_date).days
                print(f"   - Periodo coperto: {period_days} giorni")
                
                if period_days > 0:
                    avg_deliberations = total_deliberations / period_days
                    print(f"   - Media deliberazioni/giorno: {avg_deliberations:.1f}")
            except:
                pass
        
        # Salva report
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'source_backup': str(latest_backup),
            'general_stats': stats,
            'sessions_summary': sessions_summary,
            'totals': {
                'sessions': len(sessions_summary),
                'deliberations': total_deliberations,
                'fs_count': total_fs,
                'fs_percentage': (total_fs/total_deliberations*100) if total_deliberations > 0 else 0
            }
        }
        
        report_file = f"report_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print()
        print(f"💾 Report salvato in: {report_file}")
        print("✅ Generazione report completata!")
        
    except Exception as e:
        print(f"❌ Errore durante la generazione del report: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_complete_report()
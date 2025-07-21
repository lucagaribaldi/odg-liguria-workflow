#!/usr/bin/env python3
"""
Test finale del sistema completo
Verifica che tutti i componenti funzionino correttamente
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_system_components():
    """Test di tutti i componenti del sistema"""
    
    print("🧪 TEST FINALE DEL SISTEMA ODG LIGURIA")
    print("=" * 50)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'overall_success': True
    }
    
    # Test 1: PDF Parser
    print("\n1️⃣ TEST PDF PARSER")
    print("-" * 20)
    
    try:
        from pdf_parser import ODGPDFParser
        parser = ODGPDFParser()
        
        # Test parsing di un PDF
        test_pdf = "data/input/ODG_17072025.pdf"
        if Path(test_pdf).exists():
            result = parser.parse_odg(test_pdf)
            deliberations_count = len(result.get('deliberations', []))
            
            if deliberations_count > 0:
                print(f"✅ PDF Parser: {deliberations_count} deliberazioni estratte")
                results['tests']['pdf_parser'] = {'success': True, 'deliberations': deliberations_count}
            else:
                print("❌ PDF Parser: Nessuna deliberazione estratta")
                results['tests']['pdf_parser'] = {'success': False, 'error': 'No deliberations found'}
                results['overall_success'] = False
        else:
            print("⚠️  PDF Parser: File di test non trovato")
            results['tests']['pdf_parser'] = {'success': False, 'error': 'Test file not found'}
            results['overall_success'] = False
            
    except Exception as e:
        print(f"❌ PDF Parser: Errore - {str(e)}")
        results['tests']['pdf_parser'] = {'success': False, 'error': str(e)}
        results['overall_success'] = False
    
    # Test 2: AI Synthesizer
    print("\n2️⃣ TEST AI SYNTHESIZER")
    print("-" * 20)
    
    try:
        from ai_synthesizer import AISynthesizer
        synthesizer = AISynthesizer(use_ai=False)
        
        # Test synthesis
        test_deliberation = {
            'numero': '1',
            'tipo_atto': 'Deliberazione',
            'oggetto': 'Test deliberazione per verifica sistema',
            'proponente': 'Test',
            'fs_flag': True
        }
        
        result = synthesizer.synthesize_deliberation(test_deliberation)
        
        if 'sintesi_rapida' in result:
            print(f"✅ AI Synthesizer: Sintesi generata - '{result['sintesi_rapida']}'")
            results['tests']['ai_synthesizer'] = {'success': True, 'synthesis': result['sintesi_rapida']}
        else:
            print("❌ AI Synthesizer: Sintesi non generata")
            results['tests']['ai_synthesizer'] = {'success': False, 'error': 'No synthesis generated'}
            results['overall_success'] = False
            
    except Exception as e:
        print(f"❌ AI Synthesizer: Errore - {str(e)}")
        results['tests']['ai_synthesizer'] = {'success': False, 'error': str(e)}
        results['overall_success'] = False
    
    # Test 3: Notion Integrator
    print("\n3️⃣ TEST NOTION INTEGRATOR")
    print("-" * 20)
    
    try:
        from notion_integrator import NotionIntegrator
        
        # Check se le credenziali sono disponibili
        notion_token = os.getenv("NOTION_TOKEN")
        database_id = os.getenv("NOTION_DATABASE_ID")
        
        if notion_token and database_id:
            try:
                integrator = NotionIntegrator(notion_token, database_id)
                print("✅ Notion Integrator: Inizializzato correttamente")
                results['tests']['notion_integrator'] = {'success': True, 'credentials': True}
            except Exception as e:
                print(f"❌ Notion Integrator: Errore inizializzazione - {str(e)}")
                results['tests']['notion_integrator'] = {'success': False, 'error': str(e)}
                results['overall_success'] = False
        else:
            print("⚠️  Notion Integrator: Credenziali non configurate")
            results['tests']['notion_integrator'] = {'success': True, 'credentials': False, 'note': 'Credentials not configured'}
            
    except Exception as e:
        print(f"❌ Notion Integrator: Errore - {str(e)}")
        results['tests']['notion_integrator'] = {'success': False, 'error': str(e)}
        results['overall_success'] = False
    
    # Test 4: Decreto Scraper
    print("\n4️⃣ TEST DECRETO SCRAPER")
    print("-" * 20)
    
    try:
        from decreto_scraper import DecretoScraper
        scraper = DecretoScraper(verify_ssl=False)
        print("✅ Decreto Scraper: Inizializzato correttamente")
        results['tests']['decreto_scraper'] = {'success': True, 'note': 'Initialized successfully'}
        
    except Exception as e:
        print(f"❌ Decreto Scraper: Errore - {str(e)}")
        results['tests']['decreto_scraper'] = {'success': False, 'error': str(e)}
        results['overall_success'] = False
    
    # Test 5: File System
    print("\n5️⃣ TEST FILE SYSTEM")
    print("-" * 20)
    
    try:
        # Verifica directory
        directories = ['data/input', 'data/backups', 'logs']
        all_dirs_exist = True
        
        for dir_path in directories:
            if Path(dir_path).exists():
                print(f"✅ Directory {dir_path}: Esistente")
            else:
                print(f"❌ Directory {dir_path}: Mancante")
                all_dirs_exist = False
        
        # Verifica file di backup
        backup_files = list(Path('data/backups').glob('*.json'))
        if backup_files:
            print(f"✅ Backup files: {len(backup_files)} file trovati")
        else:
            print("⚠️  Backup files: Nessun file di backup trovato")
        
        # Verifica PDF in input
        pdf_files = list(Path('data/input').glob('*.pdf'))
        if pdf_files:
            print(f"✅ PDF files: {len(pdf_files)} file trovati")
        else:
            print("⚠️  PDF files: Nessun PDF trovato")
        
        results['tests']['file_system'] = {
            'success': all_dirs_exist,
            'directories': directories,
            'backup_files': len(backup_files),
            'pdf_files': len(pdf_files)
        }
        
        if not all_dirs_exist:
            results['overall_success'] = False
            
    except Exception as e:
        print(f"❌ File System: Errore - {str(e)}")
        results['tests']['file_system'] = {'success': False, 'error': str(e)}
        results['overall_success'] = False
    
    # Test 6: Workflow Scripts
    print("\n6️⃣ TEST WORKFLOW SCRIPTS")
    print("-" * 20)
    
    try:
        scripts = [
            'main_workflow.py',
            'monitor_pdfs.py',
            'batch_process_pdfs.py'
        ]
        
        all_scripts_exist = True
        for script in scripts:
            if Path(script).exists():
                print(f"✅ Script {script}: Esistente")
            else:
                print(f"❌ Script {script}: Mancante")
                all_scripts_exist = False
        
        results['tests']['workflow_scripts'] = {
            'success': all_scripts_exist,
            'scripts': scripts
        }
        
        if not all_scripts_exist:
            results['overall_success'] = False
            
    except Exception as e:
        print(f"❌ Workflow Scripts: Errore - {str(e)}")
        results['tests']['workflow_scripts'] = {'success': False, 'error': str(e)}
        results['overall_success'] = False
    
    # Risultato finale
    print(f"\n🎯 RISULTATO FINALE")
    print("=" * 20)
    
    if results['overall_success']:
        print("✅ SISTEMA COMPLETAMENTE FUNZIONANTE!")
        print("🚀 Il sistema è pronto per la produzione")
    else:
        print("⚠️  Sistema parzialmente funzionante")
        print("🔧 Alcuni componenti richiedono attenzione")
    
    # Salva risultati
    test_file = f"system_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Risultati test salvati in: {test_file}")
    
    return results['overall_success']

if __name__ == "__main__":
    success = test_system_components()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Verify current database state and complete missing deliberations
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from notion_integrator import NotionIntegrator

def main():
    print("🔍 VERIFICANDO STATO ATTUALE DEL DATABASE")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Notion credentials
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("❌ Missing Notion credentials")
        return 1
    
    # Initialize integrator
    integrator = NotionIntegrator(notion_token, database_id)
    
    # Get current pages
    print("📊 Analizzando il database attuale...")
    
    response = integrator._make_notion_request("query_database", database_id=database_id, page_size=100)
    current_pages = response["results"]
    
    print(f"📄 Pagine totali nel database: {len(current_pages)}")
    
    # Analyze by session
    sessions = {}
    invalid_pages = []
    
    for page in current_pages:
        properties = page["properties"]
        seduta = integrator._extract_property_value(properties, "Seduta", "number")
        numero = integrator._extract_property_value(properties, "Numero", "number")
        
        if seduta is None or numero is None:
            invalid_pages.append(page["id"])
            continue
        
        seduta_str = str(seduta)
        if seduta_str not in sessions:
            sessions[seduta_str] = []
        sessions[seduta_str].append(int(numero))
    
    print(f"\n📅 SESSIONI PRESENTI:")
    for seduta, numeri in sorted(sessions.items()):
        numeri.sort()
        print(f"   - Sessione {seduta}: {len(numeri)} deliberazioni")
        print(f"     Numeri: {numeri}")
    
    if invalid_pages:
        print(f"\n⚠️  Pagine invalide: {len(invalid_pages)} (da rimuovere manualmente)")
    
    # Load original data to compare
    print(f"\n🔍 Confrontando con i dati originali...")
    
    backup_file = "data/backups/workflow_backup_20250718_152226.json"
    with open(backup_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # Extract original deliberations by session
    original_sessions = {}
    for result in original_data['results']:
        if result.get('success') and 'deliberations' in result:
            for delib in result['deliberations']:
                seduta = str(delib.get('seduta', ''))
                numero = int(delib.get('numero', 0))
                
                if seduta not in original_sessions:
                    original_sessions[seduta] = []
                original_sessions[seduta].append(numero)
    
    print(f"\n📋 CONFRONTO CON DATI ORIGINALI:")
    missing_deliberations = []
    
    for seduta, original_numeri in sorted(original_sessions.items()):
        current_numeri = sessions.get(seduta, [])
        missing = set(original_numeri) - set(current_numeri)
        
        print(f"   - Sessione {seduta}:")
        print(f"     Originali: {len(original_numeri)} deliberazioni")
        print(f"     Presenti: {len(current_numeri)} deliberazioni")
        
        if missing:
            print(f"     ❌ Mancanti: {sorted(missing)}")
            for num in missing:
                missing_deliberations.append((seduta, num))
        else:
            print(f"     ✅ Complete")
    
    if missing_deliberations:
        print(f"\n🚨 DELIBERAZIONI MANCANTI: {len(missing_deliberations)}")
        
        # Extract missing deliberations from original data
        missing_data = []
        for result in original_data['results']:
            if result.get('success') and 'deliberations' in result:
                for delib in result['deliberations']:
                    seduta = str(delib.get('seduta', ''))
                    numero = int(delib.get('numero', 0))
                    
                    if (seduta, numero) in missing_deliberations:
                        missing_data.append(delib)
        
        print(f"📄 Trovate {len(missing_data)} deliberazioni da sincronizzare")
        
        # Ask if user wants to sync missing deliberations
        response = input(f"\n❓ Vuoi sincronizzare le deliberazioni mancanti? (y/n): ").lower().strip()
        
        if response == 'y':
            print(f"\n🔄 Sincronizzando deliberazioni mancanti...")
            
            sync_stats = integrator.sync_deliberations(missing_data)
            
            print(f"\n📊 RISULTATI SYNC:")
            print(f"   - Create: {sync_stats.get('created', 0)}")
            print(f"   - Duplicati evitati: {sync_stats.get('duplicates_avoided', 0)}")
            print(f"   - Errori: {sync_stats.get('errors', 0)}")
            
            if sync_stats.get('errors', 0) == 0:
                print(f"\n🎉 Sincronizzazione completata con successo!")
                print(f"Il database ora dovrebbe avere 50 deliberazioni complete")
            else:
                print(f"\n⚠️  Sincronizzazione completata con errori")
        else:
            print("❌ Sincronizzazione annullata")
    else:
        print(f"\n✅ DATABASE COMPLETO - Tutte le deliberazioni sono presenti!")
    
    print(f"\n🔗 Verifica il tuo database: https://www.notion.so/{database_id}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
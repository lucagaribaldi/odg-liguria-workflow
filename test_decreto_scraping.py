#!/usr/bin/env python3
"""
Test decreto scraping on real deliberations from Notion database
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from notion_integrator import NotionIntegrator
from decreto_scraper import DecretoScraper

def main():
    print("🔍 TEST DECRETO SCRAPING SU DELIBERAZIONI REALI")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Notion credentials
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("❌ Missing Notion credentials")
        return 1
    
    try:
        # Initialize components
        integrator = NotionIntegrator(notion_token, database_id)
        scraper = DecretoScraper(verify_ssl=False)
        
        print("🔄 Recuperando deliberazioni dal database Notion...")
        
        # Get some deliberations from Notion
        response = integrator._make_notion_request(
            "query_database", 
            database_id=database_id, 
            page_size=10
        )
        
        pages = response["results"]
        print(f"📄 Trovate {len(pages)} deliberazioni nel database")
        
        # Extract deliberation data from first few pages
        test_deliberations = []
        
        for i, page in enumerate(pages[:5]):  # Test first 5 deliberations
            properties = page["properties"]
            
            seduta = integrator._extract_property_value(properties, "Seduta", "number")
            numero = integrator._extract_property_value(properties, "Numero", "number")
            oggetto = integrator._extract_property_value(properties, "Oggetto", "rich_text")
            data_seduta = integrator._extract_property_value(properties, "Data_Seduta", "date")
            proponente = integrator._extract_property_value(properties, "Proponente", "rich_text")
            
            if seduta and numero:
                test_deliberations.append({
                    "page_id": page["id"],
                    "seduta": str(seduta),
                    "numero": str(numero),
                    "oggetto": oggetto or "N/A",
                    "data_seduta": data_seduta or "N/A",
                    "proponente": proponente or "N/A"
                })
        
        if not test_deliberations:
            print("❌ Nessuna deliberazione valida trovata nel database")
            return 1
        
        print(f"\n🧪 Testando lo scraping su {len(test_deliberations)} deliberazioni:")
        print("-" * 50)
        
        results = []
        
        for i, delib in enumerate(test_deliberations, 1):
            print(f"\n{i}. Testing deliberazione {delib['seduta']}/{delib['numero']}")
            print(f"   Oggetto: {delib['oggetto'][:80]}...")
            print(f"   Data: {delib['data_seduta']}")
            print(f"   Proponente: {delib['proponente']}")
            
            try:
                # Perform decreto scraping
                result = scraper.verify_decreto_publication(
                    seduta=delib['seduta'],
                    numero=delib['numero'],
                    oggetto=delib['oggetto'],
                    data_seduta=delib['data_seduta']
                )
                
                # Add page info to result
                result['page_id'] = delib['page_id']
                result['deliberation_info'] = delib
                results.append(result)
                
                if result.get('found'):
                    print(f"   ✅ TROVATO! URL: {result.get('url', 'N/A')}")
                    print(f"   📅 Data pubblicazione: {result.get('data_pubblicazione', 'N/A')}")
                    print(f"   🔍 Metodo: {result.get('search_method', 'N/A')}")
                else:
                    print(f"   ❌ Non trovato")
                    if result.get('error'):
                        print(f"   ⚠️  Errore: {result['error']}")
                
            except Exception as e:
                print(f"   💥 Errore durante lo scraping: {str(e)}")
                results.append({
                    'page_id': delib['page_id'],
                    'deliberation_info': delib,
                    'found': False,
                    'error': str(e)
                })
        
        # Summary
        print(f"\n📊 RIEPILOGO RISULTATI:")
        print("-" * 30)
        
        found_count = len([r for r in results if r.get('found')])
        not_found_count = len([r for r in results if not r.get('found') and not r.get('error')])
        error_count = len([r for r in results if r.get('error')])
        
        print(f"✅ Trovati: {found_count}/{len(results)} ({found_count/len(results)*100:.1f}%)")
        print(f"❌ Non trovati: {not_found_count}/{len(results)} ({not_found_count/len(results)*100:.1f}%)")
        print(f"💥 Errori: {error_count}/{len(results)} ({error_count/len(results)*100:.1f}%)")
        
        # Show found decreti details
        if found_count > 0:
            print(f"\n📋 DECRETI TROVATI:")
            for result in results:
                if result.get('found'):
                    delib = result['deliberation_info']
                    print(f"   - Seduta {delib['seduta']}, N.{delib['numero']}")
                    print(f"     URL: {result.get('url', 'N/A')}")
                    print(f"     Data: {result.get('data_pubblicazione', 'N/A')}")
        
        # Ask if user wants to update Notion with results
        if found_count > 0:
            print(f"\n❓ Vuoi aggiornare il database Notion con i risultati dello scraping? (y/n): ", end="")
            response = input().lower().strip()
            
            if response == 'y':
                print(f"\n🔄 Aggiornando database Notion...")
                
                updated_count = 0
                for result in results:
                    if result.get('found'):
                        try:
                            # Update the Notion page with publication info
                            page_id = result['page_id']
                            
                            properties = {
                                "Pubblicato": {"select": {"name": "Pubblicato"}},
                                "URL_Decreto": {"url": result.get('url', '')},
                            }
                            
                            if result.get('data_pubblicazione'):
                                properties["Data_Pubblicazione"] = {
                                    "date": {"start": result['data_pubblicazione']}
                                }
                            
                            integrator._make_notion_request(
                                "update_page",
                                page_id=page_id,
                                properties=properties
                            )
                            
                            updated_count += 1
                            print(f"   ✅ Aggiornata deliberazione {result['deliberation_info']['seduta']}/{result['deliberation_info']['numero']}")
                            
                        except Exception as e:
                            print(f"   ❌ Errore aggiornamento {result['deliberation_info']['seduta']}/{result['deliberation_info']['numero']}: {str(e)}")
                
                print(f"\n🎉 Aggiornamento completato! {updated_count} deliberazioni aggiornate.")
            else:
                print("❌ Aggiornamento Notion annullato")
        
        # Save results
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tested": len(results),
            "found": found_count,
            "not_found": not_found_count,
            "errors": error_count,
            "success_rate": f"{found_count/len(results)*100:.1f}%",
            "results": results
        }
        
        report_file = f"decreto_scraping_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report salvato: {report_file}")
        print(f"🔗 Verifica il database: https://www.notion.so/{database_id}")
        
        return 0
        
    except Exception as e:
        print(f"\n💥 Errore fatale: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
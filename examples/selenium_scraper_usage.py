#!/usr/bin/env python3
"""
Esempi di utilizzo di SeleniumDecretoScraper
Dimostra come utilizzare il sistema di browser automation per form JavaScript-heavy.
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from selenium_scraper import SeleniumDecretoScraper, LogLevel, SearchParameters


def example_basic_usage():
    """Esempio utilizzo base con browser headless."""
    print("🔍 Esempio utilizzo base SeleniumDecretoScraper\n")
    
    # Configurazione base per produzione
    with SeleniumDecretoScraper(
        headless=True,          # Browser nascosto
        debug_mode=False,       # No screenshot overhead
        implicit_wait=10,       # Timeout elementi
        log_level=LogLevel.INFO
    ) as scraper:
        
        print("🚀 Avvio ricerca decreto...")
        
        found, url, confidence = scraper.search_decreto_selenium(
            seduta="3929",
            numero="17", 
            oggetto="Approvazione piano triennale lavori pubblici"
        )
        
        print(f"Risultato ricerca:")
        print(f"  Trovato: {found}")
        print(f"  URL: {url}")
        print(f"  Confidence: {confidence:.2f}")
        
        # Statistiche performance
        stats = scraper.get_performance_stats()
        print(f"\nStatistiche:")
        print(f"  Operazioni totali: {stats['total_operations']}")
        print(f"  Operazioni riuscite: {stats['successful_operations']}")
        print(f"  Tasso successo: {stats['success_rate']:.1%}")
        print(f"  Tempo medio: {stats['average_execution_time']:.2f}s")


def example_visual_debug():
    """Esempio con debug visuale - browser visibile."""
    print("\n🔍 Esempio debug visuale con browser visibile\n")
    
    # Configurazione debug con browser visibile
    with SeleniumDecretoScraper(
        headless=False,         # Browser visibile
        debug_mode=True,        # Screenshot automatici
        implicit_wait=15,       # Timeout generoso per osservazione
        log_level=LogLevel.DEBUG
    ) as scraper:
        
        print("👁️  Browser si aprirà visualmente...")
        print("📷 Screenshot automatici salvati in debug/")
        
        found, url, confidence = scraper.search_decreto_selenium(
            seduta="3929",
            numero="17",
            oggetto="Approvazione piano triennale lavori pubblici"
        )
        
        print(f"\nRisultato debug:")
        print(f"  Found: {found}")
        print(f"  URL: {url}")
        print(f"  Confidence: {confidence:.2f}")
        
        # Screenshot manuale aggiuntivo
        screenshot_path = scraper.take_screenshot("esempio_debug_finale")
        print(f"  Screenshot finale: {screenshot_path}")
        
        # Pausa per osservazione (in debug mode)
        if not scraper.headless:
            print("\n⏸️  Premi Invio per continuare...")
            input()


def example_multiple_searches():
    """Esempio ricerche multiple con stesso scraper."""
    print("\n🔍 Esempio ricerche multiple\n")
    
    test_cases = [
        {
            "seduta": "3929",
            "numero": "17",
            "oggetto": "Approvazione piano triennale lavori pubblici",
            "anno": "2025"
        },
        {
            "seduta": "3930", 
            "numero": "5",
            "oggetto": "Regolamento comunale parcheggi",
            "anno": "2025"
        },
        {
            "seduta": "3931",
            "numero": "12", 
            "oggetto": "Autorizzazione spesa manutenzione strade",
            "anno": "2025"
        }
    ]
    
    # Usa stesso scraper per efficienza
    with SeleniumDecretoScraper(headless=True, debug_mode=False) as scraper:
        risultati = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"🔍 Test {i}: {case['oggetto'][:40]}...")
            
            found, url, confidence = scraper.search_decreto_selenium(
                seduta=case['seduta'],
                numero=case['numero'],
                oggetto=case['oggetto'],
                anno=case.get('anno')
            )
            
            risultati.append({
                'case': case,
                'found': found, 
                'url': url,
                'confidence': confidence
            })
            
            status = "✅" if found else "❌"
            print(f"  {status} Risultato: {found} (confidence: {confidence:.2f})")
            
            # Pausa tra ricerche per evitare rate limiting
            time.sleep(1)
        
        # Riepilogo finale
        print(f"\n📊 Riepilogo {len(test_cases)} ricerche:")
        successi = sum(1 for r in risultati if r['found'])
        print(f"  Successi: {successi}/{len(test_cases)} ({successi/len(test_cases):.1%})")
        
        # Statistiche scraper
        stats = scraper.get_performance_stats()
        print(f"  Operazioni totali: {stats['total_operations']}")
        print(f"  Tasso successo complessivo: {stats['success_rate']:.1%}")


def example_advanced_configuration():
    """Esempio configurazione avanzata con custom options."""
    print("\n⚙️ Esempio configurazione avanzata\n")
    
    # Configurazione personalizzata
    scraper = SeleniumDecretoScraper(
        base_url="https://decretidigitali.regione.liguria.it",
        headless=True,
        implicit_wait=12,       # Timeout custom
        debug_mode=True,        # Screenshot per analisi
        log_level=LogLevel.DEBUG,
        max_retries=5           # Più retry per robustezza
    )
    
    print("Configurazione avanzata:")
    print(f"  Base URL: {scraper.base_url}")
    print(f"  Modalità headless: {scraper.headless}")
    print(f"  Timeout implicito: {scraper.implicit_wait}s")
    print(f"  Debug mode: {scraper.debug_mode}")
    print(f"  Max retry: {scraper.max_retries}")
    
    # Test con configurazione custom
    with scraper:
        print("\n🧪 Test con configurazione custom...")
        
        found, url, confidence = scraper.search_decreto_selenium(
            seduta="3929",
            numero="17",
            oggetto="Test configurazione avanzata"
        )
        
        print(f"Test result: Found={found}, Confidence={confidence:.2f}")


def example_error_handling():
    """Esempio gestione errori robusto."""
    print("\n🚨 Esempio gestione errori\n")
    
    def safe_decreto_search(seduta, numero, oggetto):
        """Ricerca sicura con gestione errori completa."""
        
        try:
            with SeleniumDecretoScraper(
                headless=True,
                debug_mode=False,
                implicit_wait=10
            ) as scraper:
                
                return scraper.search_decreto_selenium(seduta, numero, oggetto)
                
        except Exception as e:
            print(f"❌ Errore durante ricerca: {e}")
            return False, None, 0.0
    
    # Test casi normali e edge case
    test_cases = [
        ("3929", "17", "Decreto valido"),           # Caso normale
        ("9999", "999", "Decreto inesistente"),    # Caso non trovato
        ("", "", ""),                               # Caso edge
    ]
    
    for seduta, numero, oggetto in test_cases:
        print(f"🔍 Test: seduta={seduta}, numero={numero}, oggetto={oggetto[:20]}...")
        
        found, url, confidence = safe_decreto_search(seduta, numero, oggetto)
        
        status = "✅" if found else "❌"
        print(f"  {status} Risultato: {found} (confidence: {confidence:.2f})")


def example_dropdown_testing():
    """Esempio test selezione dropdown."""
    print("\n📋 Esempio test selezione dropdown\n")
    
    with SeleniumDecretoScraper(
        headless=False,     # Visibile per osservare dropdown
        debug_mode=True,    # Screenshot delle selezioni
        implicit_wait=15
    ) as scraper:
        
        print("🔧 Test estrazione e selezione dropdown...")
        
        # Setup driver e navigazione
        scraper.setup_driver()
        scraper.navigate_to_search()
        
        # Simula estrazione opzioni dropdown
        try:
            # Cerca dropdown anno
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import Select
            
            # Esempio estrazione dropdown (se presente)
            dropdowns = scraper.driver.find_elements(By.TAG_NAME, "select")
            
            for i, dropdown in enumerate(dropdowns):
                print(f"Dropdown {i+1}:")
                options = scraper.extract_dropdown_options(dropdown)
                print(f"  Opzioni trovate: {len(options)}")
                
                # Mostra prime 3 opzioni
                for value, text in list(options.items())[:3]:
                    print(f"    {value}: {text}")
                    
                if len(options) > 3:
                    print(f"    ... e altre {len(options)-3} opzioni")
                
        except Exception as e:
            print(f"Test dropdown: {e}")
        
        print("📷 Screenshot salvati per analisi dropdown")


def example_performance_comparison():
    """Esempio comparazione performance Selenium vs requests."""
    print("\n⚡ Esempio comparazione performance\n")
    
    # Import del scraper requests per confronto
    try:
        from decreto_scraper import DecretoScraperAdvanced
        has_requests_scraper = True
    except ImportError:
        has_requests_scraper = False
        print("⚠️ DecretoScraperAdvanced non disponibile per confronto")
    
    search_params = {
        "seduta": "3929",
        "numero": "17", 
        "oggetto": "Test performance comparison"
    }
    
    # Test Selenium
    print("🔧 Test SeleniumDecretoScraper...")
    start_time = time.time()
    
    with SeleniumDecretoScraper(headless=True, debug_mode=False) as selenium_scraper:
        selenium_found, selenium_url, selenium_conf = selenium_scraper.search_decreto_selenium(**search_params)
        selenium_stats = selenium_scraper.get_performance_stats()
    
    selenium_time = time.time() - start_time
    
    print(f"  Selenium: {selenium_time:.2f}s")
    print(f"  Found: {selenium_found}, Confidence: {selenium_conf:.2f}")
    
    # Test requests scraper (se disponibile)
    if has_requests_scraper:
        print("\n🔧 Test DecretoScraperAdvanced...")
        start_time = time.time()
        
        with DecretoScraperAdvanced(debug_mode=False) as requests_scraper:
            requests_found, requests_url, requests_conf = requests_scraper.verify_decreto_publication(**search_params)
            requests_stats = requests_scraper.get_performance_stats()
        
        requests_time = time.time() - start_time
        
        print(f"  Requests: {requests_time:.2f}s")
        print(f"  Found: {requests_found}, Confidence: {requests_conf:.2f}")
        
        # Confronto
        speed_ratio = selenium_time / requests_time if requests_time > 0 else 0
        print(f"\n📊 Confronto:")
        print(f"  Selenium è {speed_ratio:.1f}x più lento di requests")
        print(f"  Ma gestisce JavaScript e form complessi")
    
    print(f"\n💡 Raccomandazione:")
    print(f"  - Usa Selenium per form JavaScript-heavy")
    print(f"  - Usa requests per form semplici (più veloce)")


def example_production_setup():
    """Esempio setup ottimizzato per produzione."""
    print("\n🚀 Esempio setup produzione\n")
    
    def create_production_scraper():
        """Crea scraper ottimizzato per produzione."""
        return SeleniumDecretoScraper(
            headless=True,              # Sempre headless in produzione
            debug_mode=False,           # No screenshot overhead
            implicit_wait=8,            # Timeout bilanciato
            log_level=LogLevel.WARN,    # Log solo warning/errori
            max_retries=2               # Retry limitati per velocità
        )
    
    def production_decreto_search(seduta, numero, oggetto):
        """Workflow produzione con monitoring."""
        
        with create_production_scraper() as scraper:
            try:
                # Esegui ricerca
                found, url, confidence = scraper.search_decreto_selenium(
                    seduta, numero, oggetto
                )
                
                # Verifica qualità risultato
                if found and confidence < 0.7:
                    print(f"⚠️ Warning: Low confidence {confidence:.2f}")
                
                # Monitoring performance
                stats = scraper.get_performance_stats()
                if stats['average_execution_time'] > 30:
                    print(f"⚠️ Warning: Slow execution {stats['average_execution_time']:.1f}s")
                
                return found, url, confidence
                
            except Exception as e:
                print(f"❌ Production error: {e}")
                return False, None, 0.0
    
    # Test workflow produzione
    print("🔧 Test workflow produzione...")
    
    found, url, confidence = production_decreto_search(
        seduta="3929",
        numero="17",
        oggetto="Test produzione"
    )
    
    print(f"Produzione result:")
    print(f"  Found: {found}")
    print(f"  URL: {url}")  
    print(f"  Confidence: {confidence:.2f}")
    
    print(f"\n✅ Setup produzione configurato correttamente!")


def main():
    """Esegue tutti gli esempi."""
    print("📚 SeleniumDecretoScraper - Esempi di utilizzo")
    print("=" * 60)
    
    try:
        # Esempi base
        example_basic_usage()
        
        # Debug visuale (opzionale - richiede interazione)
        print("\n" + "=" * 60)
        risposta = input("\n🤔 Vuoi eseguire l'esempio di debug visuale? (y/n): ")
        if risposta.lower() in ['y', 'yes', 's', 'si']:
            example_visual_debug()
        
        # Altri esempi
        example_multiple_searches()
        example_advanced_configuration() 
        example_error_handling()
        
        # Test dropdown (opzionale - richiede interazione)
        print("\n" + "=" * 60)
        risposta = input("\n🤔 Vuoi testare la selezione dropdown? (y/n): ")
        if risposta.lower() in ['y', 'yes', 's', 'si']:
            example_dropdown_testing()
        
        example_performance_comparison()
        example_production_setup()
        
        print("\n" + "=" * 60)
        print("🎉 Tutti gli esempi completati!")
        
        print("\n📖 Guida rapida SeleniumDecretoScraper:")
        print("1. Installa Chrome browser nel sistema")
        print("2. Installa dipendenze: pip install selenium webdriver-manager")
        print("3. Usa context manager: with SeleniumDecretoScraper() as scraper:")
        print("4. Chiama search_decreto_selenium() con parametri")
        print("5. Ottieni risultati con confidence scoring")
        
        print("\n🔧 Configurazioni raccomandate:")
        print("- Sviluppo: headless=False, debug_mode=True")
        print("- Test: headless=True, debug_mode=True") 
        print("- Produzione: headless=True, debug_mode=False")
        
        print("\n💡 Quando usare Selenium:")
        print("- Form con JavaScript o validazioni client-side")
        print("- Dropdown dinamici caricati via AJAX")
        print("- Siti che bloccano requests automatici")
        print("- Debugging visuale necessario")
        
        print("\n⚡ Quando usare DecretoScraperAdvanced:")
        print("- Form semplici senza JavaScript")
        print("- Performance critiche")
        print("- Ricerche batch ad alto volume")
        
    except KeyboardInterrupt:
        print("\n❌ Esempi interrotti dall'utente")
    except Exception as e:
        print(f"\n❌ Errore negli esempi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script per cercare portali alternativi della Regione Liguria
dove potrebbero essere pubblicati i decreti recenti (2021-2025)
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import logging
import time
from urllib.parse import urljoin, urlparse
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AlternativePortalFinder:
    """Finder per portali alternativi della Regione Liguria."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"
        })
        
        self.logger = logging.getLogger(__name__)
        
        # Potential alternative portals and search terms
        self.base_domains = [
            "regione.liguria.it",
            "governo.it",
            "albo.regione.liguria.it",
            "trasparenza.regione.liguria.it", 
            "amministrazionetrasparente.regione.liguria.it",
            "bur.regione.liguria.it",  # Bollettino Ufficiale Regionale
            "opendata.regione.liguria.it"
        ]
        
        self.search_terms = [
            "decreti digitali",
            "decreti giunta",
            "deliberazioni",
            "atti amministrativi",
            "pubblicazioni",
            "atti giunta regionale",
            "decreto",
            "DGR"
        ]
    
    def find_alternative_portals(self):
        """Cerca portali alternativi."""
        print("\n" + "="*70)
        print("🔍 RICERCA PORTALI ALTERNATIVI REGIONE LIGURIA")
        print("="*70)
        
        results = {
            "found_portals": [],
            "potential_urls": [],
            "decree_sections": [],
            "recent_references": []
        }
        
        # 1. Cerca nel sito principale della Regione
        self._search_main_regional_site(results)
        
        # 2. Cerca nei domini alternativi
        self._search_alternative_domains(results)
        
        # 3. Cerca riferimenti a decreti 2021-2025
        self._search_recent_decree_references(results)
        
        # 4. Mostra risultati
        self._display_results(results)
        
        return results
    
    def _search_main_regional_site(self, results):
        """Cerca nel sito principale della Regione Liguria."""
        print("\n📍 Analizzando sito principale regione.liguria.it...")
        
        try:
            main_url = "https://www.regione.liguria.it"
            response = self._safe_get(main_url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Cerca link a sezioni decreti/deliberazioni
                relevant_links = []
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '').lower()
                    text = link.get_text(strip=True).lower()
                    
                    if any(term in href or term in text for term in 
                           ['decreto', 'delibera', 'atto', 'giunta', 'pubblicazioni', 'trasparenza']):
                        full_url = urljoin(main_url, link.get('href'))
                        relevant_links.append({
                            'url': full_url,
                            'text': link.get_text(strip=True)[:100],
                            'relevance': self._calculate_relevance(href + " " + text)
                        })
                
                # Ordina per rilevanza
                relevant_links.sort(key=lambda x: x['relevance'], reverse=True)
                results['potential_urls'].extend(relevant_links[:10])
                
                print(f"   ✓ Trovati {len(relevant_links)} link potenzialmente rilevanti")
                
        except Exception as e:
            self.logger.error(f"Errore ricerca sito principale: {e}")
    
    def _search_alternative_domains(self, results):
        """Cerca nei domini alternativi."""
        print("\n🌐 Testando domini alternativi...")
        
        for domain in self.base_domains:
            try:
                print(f"   📡 Testando {domain}...")
                
                # Test HTTPS first, then HTTP
                for protocol in ['https', 'http']:
                    url = f"{protocol}://{domain}"
                    
                    response = self._safe_get(url, timeout=10)
                    if response and response.status_code == 200:
                        print(f"      ✓ {url} - ATTIVO")
                        
                        # Analizza il contenuto per riferimenti a decreti
                        self._analyze_site_for_decrees(url, response, results)
                        break
                else:
                    print(f"      ❌ {domain} - NON RAGGIUNGIBILE")
                    
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                self.logger.debug(f"Errore testing {domain}: {e}")
    
    def _analyze_site_for_decrees(self, url, response, results):
        """Analizza un sito per riferimenti a decreti."""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cerca link e testo relativo a decreti/deliberazioni
            decree_indicators = 0
            recent_year_indicators = 0
            
            # Cerca nel testo
            page_text = soup.get_text().lower()
            
            for term in ['decreto', 'delibera', 'dgr', 'atti']:
                decree_indicators += page_text.count(term)
            
            for year in ['2021', '2022', '2023', '2024', '2025']:
                recent_year_indicators += page_text.count(year)
            
            # Cerca form di ricerca
            search_forms = soup.find_all('form')
            has_search = len([f for f in search_forms if 
                            any(term in str(f).lower() for term in ['search', 'cerca', 'ricerca'])]) > 0
            
            # Calcola score
            score = decree_indicators + (recent_year_indicators * 2) + (10 if has_search else 0)
            
            if score > 5:  # Soglia minima di rilevanza
                results['found_portals'].append({
                    'url': url,
                    'score': score,
                    'decree_indicators': decree_indicators,
                    'recent_year_indicators': recent_year_indicators,
                    'has_search': has_search,
                    'title': soup.find('title').get_text(strip=True) if soup.find('title') else 'N/A'
                })
                
                print(f"      🎯 RILEVANTE (score: {score}) - {decree_indicators} decreti, {recent_year_indicators} anni recenti")
            
        except Exception as e:
            self.logger.debug(f"Errore analisi {url}: {e}")
    
    def _search_recent_decree_references(self, results):
        """Cerca riferimenti specifici a decreti 2021-2025."""
        print("\n🔍 Cercando riferimenti a decreti recenti...")
        
        # Search queries da testare
        search_queries = [
            "decreto giunta regionale liguria 2025",
            "DGR Liguria 2024",
            "deliberazioni giunta liguria 2023",
            "atti amministrativi liguria 2025"
        ]
        
        # Testa anche ricerche dirette su Google per siti della Regione
        for query in search_queries[:2]:  # Limita per non sovraccaricare
            try:
                print(f"   🔎 Query: {query}")
                
                # Costruisci URL di ricerca per il sito regionale
                site_search_url = f"https://www.regione.liguria.it/ricerca?q={query.replace(' ', '+')}"
                
                response = self._safe_get(site_search_url, timeout=15)
                if response:
                    # Analizza risultati ricerca
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Cerca risultati con anni recenti
                    for link in soup.find_all('a', href=True):
                        text = link.get_text(strip=True)
                        if any(year in text for year in ['2021', '2022', '2023', '2024', '2025']):
                            results['recent_references'].append({
                                'url': urljoin(site_search_url, link.get('href')),
                                'text': text[:150],
                                'query': query
                            })
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.debug(f"Errore ricerca query '{query}': {e}")
    
    def _calculate_relevance(self, text):
        """Calcola rilevanza di un link/testo."""
        score = 0
        
        # Termini ad alta rilevanza
        high_relevance = ['decreto', 'delibera', 'dgr', 'giunta', 'atti']
        for term in high_relevance:
            score += text.count(term) * 3
        
        # Termini a media rilevanza  
        medium_relevance = ['amministrativ', 'pubblicaz', 'trasparenza', 'albo']
        for term in medium_relevance:
            score += text.count(term) * 2
        
        # Anni recenti
        for year in ['2021', '2022', '2023', '2024', '2025']:
            score += text.count(year) * 5
        
        return score
    
    def _safe_get(self, url, timeout=20):
        """Esegue GET con gestione errori."""
        try:
            response = self.session.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
        except Exception as e:
            self.logger.debug(f"GET failed for {url}: {e}")
        return None
    
    def _display_results(self, results):
        """Mostra i risultati trovati."""
        print("\n" + "="*70)
        print("📊 RISULTATI RICERCA")
        print("="*70)
        
        # Portali trovati
        if results['found_portals']:
            print(f"\n🎯 PORTALI RILEVANTI TROVATI ({len(results['found_portals'])}):")
            results['found_portals'].sort(key=lambda x: x['score'], reverse=True)
            
            for i, portal in enumerate(results['found_portals'][:5], 1):
                print(f"\n{i}. {portal['url']}")
                print(f"   📊 Score: {portal['score']}")
                print(f"   📄 Titolo: {portal['title'][:80]}...")
                print(f"   🔍 Indicatori: {portal['decree_indicators']} decreti, {portal['recent_year_indicators']} anni recenti")
                print(f"   🔎 Ricerca: {'✓' if portal['has_search'] else '❌'}")
        
        # URL potenziali
        if results['potential_urls']:
            print(f"\n🔗 URL POTENZIALMENTE UTILI ({len(results['potential_urls'])}):")
            for i, url_info in enumerate(results['potential_urls'][:5], 1):
                print(f"{i}. {url_info['url']}")
                print(f"   📝 {url_info['text'][:80]}...")
        
        # Riferimenti recenti
        if results['recent_references']:
            print(f"\n📅 RIFERIMENTI A DECRETI RECENTI ({len(results['recent_references'])}):")
            for i, ref in enumerate(results['recent_references'][:3], 1):
                print(f"{i}. {ref['text'][:100]}...")
                print(f"   🔗 {ref['url']}")
        
        if not any(results.values()):
            print("\n❌ Nessun portale alternativo rilevante trovato")
            print("\n💡 RACCOMANDAZIONI:")
            print("   1. Contattare direttamente la Regione Liguria")
            print("   2. Verificare Bollettino Ufficiale Regionale (BUR)")
            print("   3. Cercare in sezioni 'Amministrazione Trasparente'")
            print("   4. Controllare se esistono portali tematici specifici")

def main():
    """Funzione principale."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    finder = AlternativePortalFinder()
    results = finder.find_alternative_portals()
    
    print("\n" + "="*70)
    print("✅ RICERCA COMPLETATA")
    print("="*70)
    
    return results

if __name__ == "__main__":
    main()
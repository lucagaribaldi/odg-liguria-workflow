#!/usr/bin/env python3
"""
Script per esplorare in dettaglio la sezione "atti di notifica" 
che sembra contenere molti riferimenti ad anni recenti
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import logging
import time
from urllib.parse import urljoin, urlparse
import re
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AttiNotificaExplorer:
    """Explorer per la sezione atti di notifica."""
    
    def __init__(self):
        self.base_url = "https://www.regione.liguria.it"
        self.target_url = "https://www.regione.liguria.it/homepage-attivita-istituzionale/atti-di-notifica/avvisi-atti-notifica.html"
        
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"
        })
        
        self.logger = logging.getLogger(__name__)
        
    def explore_atti_notifica(self):
        """Esplora la sezione atti di notifica."""
        print("\n" + "="*80)
        print("🎯 ESPLORAZIONE SEZIONE 'ATTI DI NOTIFICA'")
        print("="*80)
        print(f"🔗 URL: {self.target_url}")
        
        results = {
            "page_analysis": {},
            "year_2025_references": [],
            "year_2024_references": [],
            "decree_references": [],
            "deliberation_references": [],
            "search_functionality": {},
            "related_links": []
        }
        
        # 1. Analizza la pagina principale
        print("\n📍 Analizzando pagina principale...")
        self._analyze_main_page(results)
        
        # 2. Cerca riferimenti specifici agli anni recenti
        print("\n📅 Cercando riferimenti agli anni 2024-2025...")
        self._find_recent_year_references(results)
        
        # 3. Cerca decreti e deliberazioni
        print("\n📜 Cercando decreti e deliberazioni...")
        self._find_decree_references(results)
        
        # 4. Analizza funzionalità di ricerca
        print("\n🔍 Analizzando funzionalità di ricerca...")
        self._analyze_search_features(results)
        
        # 5. Esplora link correlati
        print("\n🔗 Esplorando link correlati...")
        self._explore_related_links(results)
        
        # 6. Mostra risultati
        self._display_results(results)
        
        # 7. Salva risultati
        self._save_results(results)
        
        return results
    
    def _analyze_main_page(self, results):
        """Analizza la pagina principale degli atti di notifica."""
        try:
            response = self._safe_get(self.target_url)
            if not response:
                print("   ❌ Impossibile accedere alla pagina")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Analisi generale della pagina
            page_info = {
                'title': soup.find('title').get_text(strip=True) if soup.find('title') else 'N/A',
                'total_links': len(soup.find_all('a', href=True)),
                'total_text_length': len(soup.get_text()),
                'has_tables': len(soup.find_all('table')) > 0,
                'has_lists': len(soup.find_all(['ul', 'ol'])) > 0,
                'has_forms': len(soup.find_all('form')) > 0
            }
            
            # Cerca strutture che potrebbero contenere atti
            structural_elements = {
                'tables': len(soup.find_all('table')),
                'divs_with_date': len(soup.find_all('div', text=re.compile(r'202[0-9]'))),
                'lists': len(soup.find_all(['ul', 'ol'])),
                'articles': len(soup.find_all('article')),
                'sections': len(soup.find_all('section'))
            }
            
            page_info['structural_elements'] = structural_elements
            results['page_analysis'] = page_info
            
            print(f"   ✓ Titolo: {page_info['title']}")
            print(f"   ✓ Link totali: {page_info['total_links']}")
            print(f"   ✓ Tabelle: {structural_elements['tables']}")
            print(f"   ✓ Liste: {structural_elements['lists']}")
            print(f"   ✓ Form: {'✓' if page_info['has_forms'] else '❌'}")
            
        except Exception as e:
            self.logger.error(f"Errore analisi pagina principale: {e}")
    
    def _find_recent_year_references(self, results):
        """Cerca riferimenti specifici agli anni 2024-2025."""
        try:
            response = self._safe_get(self.target_url)
            if not response:
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Cerca riferimenti al 2025
            year_2025_contexts = []
            for match in re.finditer(r'\\b2025\\b', page_text):
                start = max(0, match.start() - 150)
                end = min(len(page_text), match.end() + 150)
                context = page_text[start:end].strip()
                
                # Verifica se il contesto è rilevante
                if any(term in context.lower() for term in 
                       ['deliber', 'decreto', 'dgr', 'giunta', 'atto', 'seduta', 'numero']):
                    year_2025_contexts.append({
                        'context': context,
                        'relevance_score': self._calculate_context_relevance(context)
                    })
            
            # Cerca riferimenti al 2024
            year_2024_contexts = []
            for match in re.finditer(r'\\b2024\\b', page_text):
                start = max(0, match.start() - 150)
                end = min(len(page_text), match.end() + 150)
                context = page_text[start:end].strip()
                
                if any(term in context.lower() for term in 
                       ['deliber', 'decreto', 'dgr', 'giunta', 'atto', 'seduta', 'numero']):
                    year_2024_contexts.append({
                        'context': context,
                        'relevance_score': self._calculate_context_relevance(context)
                    })
            
            # Ordina per rilevanza
            year_2025_contexts.sort(key=lambda x: x['relevance_score'], reverse=True)
            year_2024_contexts.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            results['year_2025_references'] = year_2025_contexts[:10]  # Top 10
            results['year_2024_references'] = year_2024_contexts[:10]  # Top 10
            
            print(f"   ✓ Riferimenti 2025: {len(year_2025_contexts)}")
            print(f"   ✓ Riferimenti 2024: {len(year_2024_contexts)}")
            
            # Mostra alcuni esempi
            if year_2025_contexts:
                print(f"   💡 Esempio 2025: \"{year_2025_contexts[0]['context'][:100]}...\"")
            
            if year_2024_contexts:
                print(f"   💡 Esempio 2024: \"{year_2024_contexts[0]['context'][:100]}...\"")
            
        except Exception as e:
            self.logger.error(f"Errore ricerca anni recenti: {e}")
    
    def _find_decree_references(self, results):
        """Cerca riferimenti a decreti e deliberazioni."""
        try:
            response = self._safe_get(self.target_url)
            if not response:
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cerca link e testo che contengono termini rilevanti
            decree_terms = ['decreto', 'delibera', 'dgr', 'dcr', 'giunta']
            
            decree_links = []
            for link in soup.find_all('a', href=True):
                link_text = link.get_text(strip=True)
                link_href = link.get('href', '').lower()
                
                # Controlla se il link è rilevante
                relevance = 0
                for term in decree_terms:
                    if term in link_text.lower():
                        relevance += 2
                    if term in link_href:
                        relevance += 1
                
                # Controlla anni recenti
                recent_years_in_text = sum(1 for year in ['2021', '2022', '2023', '2024', '2025'] 
                                         if year in link_text)
                relevance += recent_years_in_text * 3
                
                if relevance > 0:
                    decree_links.append({
                        'url': urljoin(self.target_url, link.get('href')),
                        'text': link_text,
                        'relevance_score': relevance,
                        'has_recent_years': recent_years_in_text > 0
                    })
            
            # Ordina per rilevanza
            decree_links.sort(key=lambda x: x['relevance_score'], reverse=True)
            results['decree_references'] = decree_links[:15]  # Top 15
            
            print(f"   ✓ Link decreti/deliberazioni: {len(decree_links)}")
            
            # Mostra i più rilevanti
            for i, link in enumerate(decree_links[:3], 1):
                print(f"   {i}. {link['text'][:60]}... (score: {link['relevance_score']})")
            
        except Exception as e:
            self.logger.error(f"Errore ricerca decreti: {e}")
    
    def _analyze_search_features(self, results):
        """Analizza le funzionalità di ricerca disponibili."""
        try:
            response = self._safe_get(self.target_url)
            if not response:
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cerca form di ricerca
            search_forms = []
            for form in soup.find_all('form'):
                form_info = {
                    'action': form.get('action', ''),
                    'method': form.get('method', 'GET'),
                    'fields': []
                }
                
                # Analizza campi
                for field in form.find_all(['input', 'select', 'textarea']):
                    field_info = {
                        'name': field.get('name', ''),
                        'type': field.get('type', field.name),
                        'placeholder': field.get('placeholder', ''),
                        'id': field.get('id', ''),
                        'value': field.get('value', '')
                    }
                    form_info['fields'].append(field_info)
                
                if form_info['fields']:  # Solo se ha campi
                    search_forms.append(form_info)
            
            # Cerca altri elementi di ricerca (come link di filtro)
            filter_elements = []
            for element in soup.find_all(['a', 'button'], text=re.compile(r'(cerca|search|filtra|filter)', re.I)):
                filter_elements.append({
                    'tag': element.name,
                    'text': element.get_text(strip=True),
                    'href': element.get('href', '') if element.name == 'a' else '',
                    'onclick': element.get('onclick', '')
                })
            
            results['search_functionality'] = {
                'forms': search_forms,
                'filter_elements': filter_elements,
                'has_search': len(search_forms) > 0 or len(filter_elements) > 0
            }
            
            print(f"   ✓ Form di ricerca: {len(search_forms)}")
            print(f"   ✓ Elementi filtro: {len(filter_elements)}")
            
        except Exception as e:
            self.logger.error(f"Errore analisi ricerca: {e}")
    
    def _explore_related_links(self, results):
        """Esplora link correlati che potrebbero contenere decreti."""
        try:
            # Link correlati dalla sezione decreti trovata
            related_candidates = []
            
            for decree_ref in results.get('decree_references', [])[:5]:  # Top 5
                if decree_ref['has_recent_years']:
                    related_candidates.append(decree_ref['url'])
            
            # Esplora ogni link
            related_results = []
            for url in related_candidates:
                try:
                    print(f"   🔍 Esplorando: {urlparse(url).path}")
                    
                    response = self._safe_get(url, timeout=10)
                    if response:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Analizza contenuto
                        page_text = soup.get_text()
                        year_2025_count = page_text.count('2025')
                        year_2024_count = page_text.count('2024')
                        
                        if year_2025_count > 0 or year_2024_count > 0:
                            related_results.append({
                                'url': url,
                                'title': soup.find('title').get_text(strip=True) if soup.find('title') else 'N/A',
                                'year_2025_count': year_2025_count,
                                'year_2024_count': year_2024_count,
                                'total_relevance': year_2025_count * 2 + year_2024_count
                            })
                            
                            print(f"      ✓ {year_2025_count} ref. 2025, {year_2024_count} ref. 2024")
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    self.logger.debug(f"Errore esplorazione {url}: {e}")
            
            results['related_links'] = related_results
            
            print(f"   ✓ Link correlati esplorati: {len(related_results)}")
            
        except Exception as e:
            self.logger.error(f"Errore esplorazione link correlati: {e}")
    
    def _calculate_context_relevance(self, context):
        """Calcola la rilevanza di un contesto."""
        score = 0
        context_lower = context.lower()
        
        # Termini ad alta rilevanza
        high_terms = ['deliberazione', 'decreto', 'dgr', 'dcr']
        for term in high_terms:
            score += context_lower.count(term) * 5
        
        # Termini a media rilevanza
        medium_terms = ['giunta', 'seduta', 'numero', 'atto']
        for term in medium_terms:
            score += context_lower.count(term) * 2
        
        # Presenza di numeri (possibili numeri di decreto)
        numbers = re.findall(r'\\b\\d{1,4}\\b', context)
        score += len(numbers)
        
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
        """Mostra i risultati dell'esplorazione."""
        print("\n" + "="*80)
        print("📊 RISULTATI ESPLORAZIONE 'ATTI DI NOTIFICA'")
        print("="*80)
        
        # Analisi pagina
        page_analysis = results.get('page_analysis', {})
        if page_analysis:
            print(f"\n📄 ANALISI PAGINA:")
            print(f"   📝 Titolo: {page_analysis['title']}")
            print(f"   🔗 Link totali: {page_analysis['total_links']}")
            
            struct = page_analysis.get('structural_elements', {})
            print(f"   📊 Struttura: {struct.get('tables', 0)} tabelle, {struct.get('lists', 0)} liste")
        
        # Riferimenti anni recenti
        year_2025_refs = results.get('year_2025_references', [])
        year_2024_refs = results.get('year_2024_references', [])
        
        if year_2025_refs:
            print(f"\\n🎯 RIFERIMENTI 2025 ({len(year_2025_refs)}):")
            for i, ref in enumerate(year_2025_refs[:3], 1):
                print(f"   {i}. Score {ref['relevance_score']}: \"{ref['context'][:100]}...\"")
        
        if year_2024_refs:
            print(f"\\n📅 RIFERIMENTI 2024 ({len(year_2024_refs)}):")
            for i, ref in enumerate(year_2024_refs[:2], 1):
                print(f"   {i}. Score {ref['relevance_score']}: \"{ref['context'][:100]}...\"")
        
        # Riferimenti decreti
        decree_refs = results.get('decree_references', [])
        if decree_refs:
            print(f"\\n📜 LINK DECRETI/DELIBERAZIONI ({len(decree_refs)}):")
            for i, ref in enumerate(decree_refs[:5], 1):
                recent_marker = " 🔥" if ref['has_recent_years'] else ""
                print(f"   {i}. {ref['text'][:70]}...{recent_marker}")
                print(f"      🔗 {ref['url']}")
        
        # Funzionalità ricerca
        search_func = results.get('search_functionality', {})
        if search_func.get('has_search'):
            print(f"\\n🔍 RICERCA DISPONIBILE:")
            print(f"   📋 Form: {len(search_func.get('forms', []))}")
            print(f"   🔧 Filtri: {len(search_func.get('filter_elements', []))}")
        
        # Link correlati
        related_links = results.get('related_links', [])
        if related_links:
            print(f"\\n🔗 LINK CORRELATI CON ANNI RECENTI ({len(related_links)}):")
            related_links.sort(key=lambda x: x['total_relevance'], reverse=True)
            
            for i, link in enumerate(related_links[:3], 1):
                print(f"   {i}. {link['title'][:60]}...")
                print(f"      📅 2025: {link['year_2025_count']}, 2024: {link['year_2024_count']}")
                print(f"      🔗 {link['url']}")
        
        # Riassunto conclusivo
        total_2025_refs = len(year_2025_refs)
        total_2024_refs = len(year_2024_refs)
        total_decree_refs = len(decree_refs)
        
        print(f"\\n" + "="*80)
        print(f"📈 RIASSUNTO:")
        print(f"   🎯 Riferimenti 2025: {total_2025_refs}")
        print(f"   📅 Riferimenti 2024: {total_2024_refs}")
        print(f"   📜 Link decreti: {total_decree_refs}")
        print(f"   🔗 Link correlati: {len(related_links)}")
        
        if total_2025_refs > 0:
            print(f"\\n✅ CONCLUSIONE: La sezione contiene riferimenti a documenti 2025!")
            print(f"   💡 Questa potrebbe essere la fonte per decreti recenti")
        else:
            print(f"\\n❌ CONCLUSIONE: Nessun riferimento significativo a decreti 2025")
        
        print("="*80)
    
    def _save_results(self, results):
        """Salva i risultati."""
        try:
            output_file = "logs/atti_notifica_exploration.json"
            
            json_data = {
                'exploration_timestamp': time.time(),
                'target_url': self.target_url,
                'results': results
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"\\n💾 Risultati salvati in: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Errore salvataggio: {e}")

def main():
    """Funzione principale."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    explorer = AttiNotificaExplorer()
    results = explorer.explore_atti_notifica()
    
    return results

if __name__ == "__main__":
    main()
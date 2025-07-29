#!/usr/bin/env python3
"""
Script per esplorare in dettaglio www.regione.liguria.it
alla ricerca di sezioni con decreti/deliberazioni recenti
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

class RegioneSiteExplorer:
    """Explorer per il sito della Regione Liguria."""
    
    def __init__(self):
        self.base_url = "https://www.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"
        })
        
        self.logger = logging.getLogger(__name__)
        self.explored_urls = set()
        self.decree_urls = []
        
    def explore_site(self):
        """Esplora il sito della Regione Liguria."""
        print("\n" + "="*70)
        print("🔍 ESPLORAZIONE DETTAGLIATA www.regione.liguria.it")
        print("="*70)
        
        results = {
            "homepage_analysis": {},
            "relevant_sections": [],
            "decree_pages": [],
            "search_functionality": {},
            "recent_deliberations": []
        }
        
        # 1. Analizza homepage
        print("\n📍 Analizzando homepage...")
        self._analyze_homepage(results)
        
        # 2. Cerca sezioni amministrative
        print("\n🏛️ Cercando sezioni amministrative...")
        self._find_administrative_sections(results)
        
        # 3. Cerca funzionalità di ricerca
        print("\n🔍 Analizzando funzionalità di ricerca...")
        self._analyze_search_functionality(results)
        
        # 4. Cerca deliberazioni recenti
        print("\n📅 Cercando deliberazioni recenti...")
        self._find_recent_deliberations(results)
        
        # 5. Mostra risultati
        self._display_results(results)
        
        # 6. Salva risultati
        self._save_results(results)
        
        return results
    
    def _analyze_homepage(self, results):
        """Analizza la homepage del sito."""
        try:
            response = self._safe_get(self.base_url)
            if not response:
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Analizza menu di navigazione
            nav_links = []
            for nav in soup.find_all(['nav', 'menu', 'ul']):
                for link in nav.find_all('a', href=True):
                    text = link.get_text(strip=True).lower()
                    if any(term in text for term in 
                           ['giunta', 'delibera', 'decreto', 'atti', 'amministrazione', 'trasparenza']):
                        nav_links.append({
                            'url': urljoin(self.base_url, link.get('href')),
                            'text': link.get_text(strip=True),
                            'section': self._identify_section_type(text)
                        })
            
            # Cerca form di ricerca
            search_forms = soup.find_all('form')
            search_info = []
            for form in search_forms:
                action = form.get('action', '')
                inputs = form.find_all('input')
                if any('search' in inp.get('name', '').lower() or 'cerca' in inp.get('name', '').lower() 
                       for inp in inputs):
                    search_info.append({
                        'action': urljoin(self.base_url, action),
                        'method': form.get('method', 'GET'),
                        'inputs': [inp.get('name', '') for inp in inputs if inp.get('name')]
                    })
            
            results['homepage_analysis'] = {
                'nav_links': nav_links[:15],  # Top 15
                'search_forms': search_info,
                'total_links': len(soup.find_all('a', href=True))
            }
            
            print(f"   ✓ Trovati {len(nav_links)} link di navigazione rilevanti")
            print(f"   ✓ Trovati {len(search_info)} form di ricerca")
            
        except Exception as e:
            self.logger.error(f"Errore analisi homepage: {e}")
    
    def _find_administrative_sections(self, results):
        """Cerca sezioni amministrative."""
        # URL candidati per sezioni amministrative
        candidate_urls = [
            "/homepage-giunta",
            "/giunta-regionale", 
            "/amministrazione-trasparente",
            "/atti-amministrativi",
            "/deliberazioni",
            "/decreti",
            "/pubblicazioni",
            "/albo-pretorio",
            "/bandi-e-avvisi",
            "/normativa"
        ]
        
        # Aggiungi URL trovati nell'homepage
        if 'homepage_analysis' in results:
            for link in results['homepage_analysis'].get('nav_links', []):
                if link['section'] in ['administrative', 'transparency', 'acts']:
                    candidate_urls.append(urlparse(link['url']).path)
        
        for url_path in set(candidate_urls):  # Remove duplicates
            try:
                full_url = urljoin(self.base_url, url_path)
                if full_url in self.explored_urls:
                    continue
                    
                print(f"   🔍 Esplorando: {url_path}")
                response = self._safe_get(full_url)
                
                if response:
                    self.explored_urls.add(full_url)
                    section_info = self._analyze_section(full_url, response)
                    
                    if section_info['relevance_score'] > 0:
                        results['relevant_sections'].append(section_info)
                        print(f"      ✓ Rilevante (score: {section_info['relevance_score']})")
                    else:
                        print(f"      - Non rilevante")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                self.logger.debug(f"Errore esplorazione {url_path}: {e}")
    
    def _analyze_section(self, url, response):
        """Analizza una sezione del sito."""
        soup = BeautifulSoup(response.text, 'html.parser')
        
        section_info = {
            'url': url,
            'title': soup.find('title').get_text(strip=True) if soup.find('title') else 'N/A',
            'relevance_score': 0,
            'decree_indicators': 0,
            'recent_year_indicators': 0,
            'deliberation_links': [],
            'has_search': False,
            'description': ''
        }
        
        # Analizza contenuto testuale
        page_text = soup.get_text().lower()
        
        # Conta indicatori di rilevanza
        decree_terms = ['decreto', 'delibera', 'dgr', 'dcr', 'atto amministrativo']
        for term in decree_terms:
            count = page_text.count(term)
            section_info['decree_indicators'] += count
            section_info['relevance_score'] += count * 2
        
        # Conta anni recenti
        recent_years = ['2021', '2022', '2023', '2024', '2025']
        for year in recent_years:
            count = page_text.count(year)
            section_info['recent_year_indicators'] += count
            section_info['relevance_score'] += count * 3
        
        # Cerca link a deliberazioni/decreti
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            link_href = link.get('href', '').lower()
            
            if any(term in link_text.lower() or term in link_href 
                   for term in ['deliber', 'decreto', 'dgr', 'dcr']):
                
                # Controlla se contiene anni recenti
                has_recent_year = any(year in link_text for year in recent_years)
                
                section_info['deliberation_links'].append({
                    'url': urljoin(url, link.get('href')),
                    'text': link_text[:100],
                    'has_recent_year': has_recent_year
                })
                
                if has_recent_year:
                    section_info['relevance_score'] += 5
        
        # Cerca form di ricerca
        search_forms = soup.find_all('form')
        section_info['has_search'] = len(search_forms) > 0
        if section_info['has_search']:
            section_info['relevance_score'] += 10
        
        # Estrai descrizione
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            section_info['description'] = meta_desc.get('content', '')[:200]
        
        return section_info
    
    def _analyze_search_functionality(self, results):
        """Analizza le funzionalità di ricerca disponibili."""
        # Cerca pagine di ricerca comuni
        search_pages = [
            "/ricerca",
            "/search", 
            "/cerca",
            "/search.php",
            "/ricerca.php"
        ]
        
        search_functionality = {
            'search_pages': [],
            'global_search': None,
            'advanced_search': None
        }
        
        for search_path in search_pages:
            try:
                search_url = urljoin(self.base_url, search_path)
                response = self._safe_get(search_url)
                
                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Analizza form di ricerca
                    search_forms = soup.find_all('form')
                    
                    for form in search_forms:
                        form_info = {
                            'url': search_url,
                            'action': form.get('action', ''),
                            'method': form.get('method', 'GET'),
                            'fields': []
                        }
                        
                        # Analizza campi del form
                        for input_field in form.find_all(['input', 'select', 'textarea']):
                            field_info = {
                                'name': input_field.get('name', ''),
                                'type': input_field.get('type', input_field.name),
                                'placeholder': input_field.get('placeholder', ''),
                                'id': input_field.get('id', '')
                            }
                            form_info['fields'].append(field_info)
                        
                        search_functionality['search_pages'].append(form_info)
                        
                        # Identifica tipo di ricerca
                        field_names = [f['name'].lower() for f in form_info['fields']]
                        if any('advanced' in name or 'avanzat' in name for name in field_names):
                            search_functionality['advanced_search'] = form_info
                        elif not search_functionality['global_search']:
                            search_functionality['global_search'] = form_info
                
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.debug(f"Errore ricerca {search_path}: {e}")
        
        results['search_functionality'] = search_functionality
        
        print(f"   ✓ Trovate {len(search_functionality['search_pages'])} pagine di ricerca")
    
    def _find_recent_deliberations(self, results):
        """Cerca deliberazioni recenti."""
        # URL candidati per deliberazioni recenti
        deliberation_candidates = []
        
        # Aggiungi URL dalle sezioni rilevanti trovate
        for section in results.get('relevant_sections', []):
            for delib_link in section.get('deliberation_links', []):
                if delib_link['has_recent_year']:
                    deliberation_candidates.append(delib_link['url'])
        
        # URL diretti da provare
        direct_candidates = [
            "/homepage-giunta/giunta-regionale",
            "/deliberazioni-giunta",
            "/atti-giunta-regionale",
            "/pubblicazioni/deliberazioni"
        ]
        
        for url in direct_candidates:
            deliberation_candidates.append(urljoin(self.base_url, url))
        
        recent_deliberations = []
        
        for url in set(deliberation_candidates[:10]):  # Limita a 10 per non sovraccaricare
            try:
                if url in self.explored_urls:
                    continue
                    
                print(f"   📄 Controllando: {urlparse(url).path}")
                response = self._safe_get(url)
                
                if response:
                    self.explored_urls.add(url)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Cerca riferimenti a anni recenti
                    page_text = soup.get_text()
                    recent_years = ['2021', '2022', '2023', '2024', '2025']
                    
                    for year in recent_years:
                        if year in page_text:
                            # Cerca contesto intorno all'anno
                            year_contexts = []
                            for match in re.finditer(rf'\b{year}\b', page_text):
                                start = max(0, match.start() - 100)
                                end = min(len(page_text), match.end() + 100)
                                context = page_text[start:end].strip()
                                
                                # Verifica se il contesto è rilevante per decreti
                                if any(term in context.lower() for term in 
                                       ['deliber', 'decreto', 'dgr', 'giunta', 'atto']):
                                    year_contexts.append(context)
                            
                            if year_contexts:
                                recent_deliberations.append({
                                    'url': url,
                                    'year': year,
                                    'contexts': year_contexts[:3],  # Max 3 contexts
                                    'page_title': soup.find('title').get_text(strip=True) if soup.find('title') else 'N/A'
                                })
                                
                                print(f"      ✓ Trovati {len(year_contexts)} riferimenti al {year}")
                
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.debug(f"Errore controllo deliberazioni {url}: {e}")
        
        results['recent_deliberations'] = recent_deliberations
        
        print(f"   ✓ Trovate {len(recent_deliberations)} pagine con deliberazioni recenti")
    
    def _identify_section_type(self, text):
        """Identifica il tipo di sezione."""
        text = text.lower()
        
        if any(term in text for term in ['giunta', 'delibera', 'decreto']):
            return 'administrative'
        elif any(term in text for term in ['trasparenza', 'pubblicazioni']):
            return 'transparency'  
        elif any(term in text for term in ['atti', 'normativa']):
            return 'acts'
        else:
            return 'other'
    
    def _safe_get(self, url, timeout=15):
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
        print("\n" + "="*70)
        print("📊 RISULTATI ESPLORAZIONE")
        print("="*70)
        
        # Sezioni rilevanti
        relevant_sections = results.get('relevant_sections', [])
        if relevant_sections:
            print(f"\n🎯 SEZIONI RILEVANTI TROVATE ({len(relevant_sections)}):")
            relevant_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            for i, section in enumerate(relevant_sections[:5], 1):
                print(f"\n{i}. {section['url']}")
                print(f"   📊 Score rilevanza: {section['relevance_score']}")
                print(f"   📄 Titolo: {section['title'][:60]}...")
                print(f"   🔍 Indicatori: {section['decree_indicators']} decreti, {section['recent_year_indicators']} anni recenti")
                print(f"   🔗 Link deliberazioni: {len(section['deliberation_links'])}")
                print(f"   🔎 Ricerca: {'✓' if section['has_search'] else '❌'}")
        
        # Funzionalità di ricerca
        search_func = results.get('search_functionality', {})
        if search_func.get('search_pages'):
            print(f"\n🔍 FUNZIONALITÀ DI RICERCA:")
            print(f"   📄 Pagine di ricerca trovate: {len(search_func['search_pages'])}")
            
            if search_func.get('global_search'):
                print(f"   🌐 Ricerca globale: ✓")
                
            if search_func.get('advanced_search'):
                print(f"   🔧 Ricerca avanzata: ✓")
        
        # Deliberazioni recenti
        recent_delib = results.get('recent_deliberations', [])
        if recent_delib:
            print(f"\n📅 DELIBERAZIONI RECENTI TROVATE ({len(recent_delib)}):")
            
            # Raggruppa per anno
            by_year = {}
            for delib in recent_delib:
                year = delib['year']
                if year not in by_year:
                    by_year[year] = []
                by_year[year].append(delib)
            
            for year in sorted(by_year.keys(), reverse=True):
                print(f"\n   📅 Anno {year}: {len(by_year[year])} riferimenti")
                for delib in by_year[year][:2]:  # Max 2 per anno
                    print(f"      🔗 {delib['url']}")
                    print(f"      📄 {delib['page_title'][:60]}...")
                    if delib['contexts']:
                        print(f"      💬 \"{delib['contexts'][0][:80]}...\"")
        
        if not any([relevant_sections, search_func.get('search_pages'), recent_delib]):
            print("\n❌ Nessuna sezione significativa trovata per decreti recenti")
    
    def _save_results(self, results):
        """Salva i risultati in un file JSON."""
        try:
            output_file = "logs/regione_site_exploration.json"
            
            # Prepara dati per serializzazione JSON
            json_data = {
                'exploration_timestamp': time.time(),
                'base_url': self.base_url,
                'results': results,
                'explored_urls_count': len(self.explored_urls),
                'total_relevant_sections': len(results.get('relevant_sections', [])),
                'total_recent_deliberations': len(results.get('recent_deliberations', []))
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Risultati salvati in: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Errore salvataggio risultati: {e}")

def main():
    """Funzione principale."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    explorer = RegioneSiteExplorer()
    results = explorer.explore_site()
    
    print("\n" + "="*70)
    print("✅ ESPLORAZIONE COMPLETATA")
    print("="*70)
    
    return results

if __name__ == "__main__":
    main()
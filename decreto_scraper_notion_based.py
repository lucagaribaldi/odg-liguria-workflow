#!/usr/bin/env python3
"""
Decreto scraper that searches specifically for deliberations in our Notion database
using content-based search strategies and multiple approaches
"""

import json
import requests
import urllib3
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Optional
import re
from urllib.parse import quote

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NotionBasedDecretoScraper:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
    def load_notion_deliberations(self):
        """Load all deliberations from our Notion backup."""
        try:
            with open('data/backups/workflow_backup_20250718_152226.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract all deliberations from all PDF results
            all_deliberations = []
            for result in data.get('results', []):
                deliberations = result.get('deliberations', [])
                all_deliberations.extend(deliberations)
            
            return all_deliberations
        except FileNotFoundError:
            print("❌ Backup file not found")
            return []
    
    def get_form_tokens(self):
        """Get necessary form tokens and hidden fields from homepage."""
        response = self.session.get(self.base_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        main_form = soup.find('form', action='index.php')
        
        hidden_fields = {}
        if main_form:
            for hidden_input in main_form.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    hidden_fields[name] = value
        
        return hidden_fields
    
    def extract_search_terms_from_deliberation(self, delib: Dict) -> List[str]:
        """
        Extract multiple search terms from a deliberation for comprehensive searching.
        """
        terms = []
        
        numero = delib.get('numero', '')
        oggetto = delib.get('oggetto', '')
        proponente = delib.get('proponente', '')
        tipo_atto = delib.get('tipo_atto', '')
        
        # Basic number searches
        if numero:
            terms.extend([
                f"DGR {numero}",
                f"n. {numero}",
                f"numero {numero}",
                f"delibera {numero}",
                numero
            ])
        
        # Object-based searches (extract key words)
        if oggetto:
            # Extract significant words from oggetto (remove common words)
            obj_words = self.extract_significant_words(oggetto)
            for word in obj_words[:3]:  # Top 3 significant words
                terms.append(word)
            
            # Try exact phrases from oggetto
            if len(oggetto) > 20:
                # Try first significant part
                first_part = oggetto[:50].strip()
                if first_part:
                    terms.append(first_part)
        
        # Proponent-based searches
        if proponente:
            # Extract surname if available
            proponente_parts = proponente.split()
            if len(proponente_parts) > 1:
                surname = proponente_parts[-1]  # Usually surname is last
                terms.append(surname)
            terms.append(proponente)
        
        # Type-based searches
        if tipo_atto and 'deliberazione' in tipo_atto.lower():
            terms.append("deliberazione")
        
        return terms
    
    def extract_significant_words(self, text: str) -> List[str]:
        """Extract significant words from text, filtering out common words."""
        if not text:
            return []
        
        # Common Italian words to exclude
        stop_words = {
            'di', 'da', 'del', 'della', 'delle', 'dei', 'degli', 'con', 'per', 'in', 'a', 'su',
            'il', 'la', 'lo', 'le', 'gli', 'un', 'una', 'uno', 'e', 'o', 'che', 'al', 'alla',
            'dell', 'nell', 'sulla', 'nella', 'alle', 'agli', 'nei', 'nelle', 'sui', 'sulle',
            'dal', 'dallo', 'dalla', 'dalle', 'dagli', 'col', 'coi', 'colle', 'colla'
        }
        
        # Extract words (letters only, length > 3)
        words = re.findall(r'[A-Za-zÀ-ÿ]{4,}', text.upper())
        
        # Filter out stop words and very common terms
        significant_words = []
        for word in words:
            if word.lower() not in stop_words and len(word) > 3:
                significant_words.append(word)
        
        # Return most frequent words first
        word_counts = {}
        for word in significant_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency, then alphabetically
        sorted_words = sorted(word_counts.keys(), key=lambda w: (-word_counts[w], w))
        
        return sorted_words[:10]  # Top 10 significant words
    
    def search_with_term(self, search_term: str, year_hint: str = "2025") -> Dict:
        """
        Search for a specific term using different search strategies.
        """
        print(f"    🔍 Searching: '{search_term[:50]}...' (year hint: {year_hint})")
        
        hidden_fields = self.get_form_tokens()
        
        search_strategies = [
            # Strategy 1: Year + exact phrase search
            {
                'select_1': year_hint,
                'unnamed_1': search_term,
                'chkSearchType': '2',  # Exact phrase
                'strategy': 'year_exact'
            },
            # Strategy 2: Year + any word search
            {
                'select_1': year_hint,
                'unnamed_1': search_term,
                'chkSearchType': '1',  # Any word
                'strategy': 'year_any'
            },
            # Strategy 3: No year filter, exact phrase
            {
                'unnamed_1': search_term,
                'chkSearchType': '2',  # Exact phrase
                'strategy': 'no_year_exact'
            },
            # Strategy 4: No year filter, any word
            {
                'unnamed_1': search_term,
                'chkSearchType': '1',  # Any word
                'strategy': 'no_year_any'
            }
        ]
        
        for strategy in search_strategies:
            try:
                form_data = {**strategy, **hidden_fields}
                form_data.pop('strategy')  # Remove strategy key before submission
                
                response = self.session.post(
                    f"{self.base_url}/index.php",
                    data=form_data,
                    timeout=15,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check for results
                    if self.has_meaningful_results(soup, search_term):
                        print(f"      ✅ Found results with strategy: {strategy['strategy']}")
                        return {
                            'found': True,
                            'strategy': strategy['strategy'],
                            'search_term': search_term,
                            'url': response.url,
                            'content_preview': self.extract_result_preview(soup, search_term)
                        }
                    else:
                        print(f"      ❌ No results with strategy: {strategy['strategy']}")
                
            except Exception as e:
                print(f"      💥 Error with strategy {strategy.get('strategy', 'unknown')}: {str(e)}")
            
            time.sleep(0.5)  # Brief pause between strategies
        
        return {'found': False, 'search_term': search_term}
    
    def has_meaningful_results(self, soup: BeautifulSoup, search_term: str) -> bool:
        """Check if the search results page contains meaningful decreto content."""
        
        page_text = soup.get_text().lower()
        
        # Look for positive indicators
        positive_indicators = [
            'dgr', 'delibera', 'decreto', 'giunta regionale', 
            'regione liguria', 'n.', 'del 20'
        ]
        
        # Look for negative indicators (no results pages)
        negative_indicators = [
            'nessun risultato', 'no results', 'nessuna corrispondenza',
            'non trovato', 'not found', 'no matches'
        ]
        
        # Check for negative indicators first
        for indicator in negative_indicators:
            if indicator in page_text:
                return False
        
        # Check for positive indicators
        positive_count = sum(1 for indicator in positive_indicators if indicator in page_text)
        
        # Also look for structured content that might be results
        result_containers = soup.find_all(['div', 'tr', 'li'], text=True)
        structured_results = 0
        
        for container in result_containers:
            container_text = container.get_text(strip=True)
            if (len(container_text) > 30 and 
                any(term in container_text.lower() for term in ['dgr', 'delibera', 'decreto'])):
                structured_results += 1
        
        # Consider it meaningful if we have positive indicators or structured results
        return positive_count >= 2 or structured_results >= 1
    
    def extract_result_preview(self, soup: BeautifulSoup, search_term: str) -> str:
        """Extract a preview of the search results."""
        
        # Look for text that contains our search term or related terms
        relevant_texts = []
        
        for element in soup.find_all(text=True):
            text = element.strip()
            if (len(text) > 20 and 
                (search_term.lower() in text.lower() or 
                 any(term in text.lower() for term in ['dgr', 'delibera', 'decreto']))):
                relevant_texts.append(text[:100])
        
        if relevant_texts:
            return " | ".join(relevant_texts[:3])
        
        return "Results found but no specific preview available"
    
    def search_all_notion_deliberations(self) -> Dict:
        """
        Search for all deliberations from our Notion database on the decreto website.
        """
        print("🏛️  NOTION-BASED DECRETO SEARCH")
        print("=" * 60)
        
        deliberations = self.load_notion_deliberations()
        
        if not deliberations:
            print("❌ No deliberations loaded from Notion backup")
            return {}
        
        print(f"📋 Loaded {len(deliberations)} deliberations from Notion database")
        print()
        
        results = {
            'total_searched': len(deliberations),
            'found': 0,
            'not_found': 0,
            'errors': 0,
            'details': []
        }
        
        for i, delib in enumerate(deliberations, 1):
            numero = delib.get('numero', 'N/A')
            oggetto = delib.get('oggetto', '')[:50]
            data_seduta = delib.get('data_seduta', '')
            
            print(f"\n📄 DELIBERATION {i}/{len(deliberations)}")
            print(f"   Numero: {numero}")
            print(f"   Oggetto: {oggetto}...")
            print(f"   Data: {data_seduta}")
            
            # Extract search terms for this deliberation
            search_terms = self.extract_search_terms_from_deliberation(delib)
            
            # Try to determine year from data_seduta
            year_hint = "2025"  # Default
            if data_seduta:
                try:
                    year_hint = data_seduta.split('-')[0]
                except:
                    pass
            
            # Search with each term until we find results
            delib_result = {
                'deliberation': delib,
                'search_terms_tried': [],
                'found': False,
                'best_result': None
            }
            
            for term in search_terms[:5]:  # Try top 5 terms
                if not term or len(term.strip()) < 2:
                    continue
                    
                search_result = self.search_with_term(term, year_hint)
                delib_result['search_terms_tried'].append(term)
                
                if search_result.get('found'):
                    print(f"   ✅ FOUND with term: '{term}'")
                    print(f"      Strategy: {search_result.get('strategy')}")
                    print(f"      Preview: {search_result.get('content_preview', '')[:80]}...")
                    
                    delib_result['found'] = True
                    delib_result['best_result'] = search_result
                    results['found'] += 1
                    break
                
                time.sleep(1)  # Be respectful between searches
            
            if not delib_result['found']:
                print(f"   ❌ NOT FOUND (tried {len(delib_result['search_terms_tried'])} terms)")
                results['not_found'] += 1
            
            results['details'].append(delib_result)
            
            # Progress update every 10 deliberations
            if i % 10 == 0:
                found_so_far = results['found']
                success_rate = (found_so_far / i) * 100
                print(f"\n📊 Progress: {i}/{len(deliberations)} - Found: {found_so_far} ({success_rate:.1f}%)")
            
            time.sleep(2)  # Respectful delay between deliberations
        
        return results
    
    def generate_final_report(self, results: Dict):
        """Generate a comprehensive report of the search results."""
        
        print(f"\n🎯 FINAL SEARCH REPORT")
        print("=" * 50)
        print(f"Total deliberations searched: {results['total_searched']}")
        print(f"Found on decreto website: {results['found']}")
        print(f"Not found: {results['not_found']}")
        print(f"Success rate: {(results['found']/results['total_searched']*100):.1f}%")
        
        # Show successful matches
        if results['found'] > 0:
            print(f"\n✅ SUCCESSFUL MATCHES:")
            successful_matches = [d for d in results['details'] if d['found']]
            
            for i, match in enumerate(successful_matches[:10], 1):  # Show first 10
                delib = match['deliberation']
                result = match['best_result']
                print(f"  {i}. DGR {delib.get('numero')} - {delib.get('oggetto', '')[:40]}...")
                print(f"     Found with: '{result.get('search_term')[:30]}...'")
                print(f"     Strategy: {result.get('strategy')}")
        
        # Show breakdown by document type
        type_breakdown = {}
        for detail in results['details']:
            tipo_atto = detail['deliberation'].get('tipo_atto', 'Unknown')
            if tipo_atto not in type_breakdown:
                type_breakdown[tipo_atto] = {'total': 0, 'found': 0}
            type_breakdown[tipo_atto]['total'] += 1
            if detail['found']:
                type_breakdown[tipo_atto]['found'] += 1
        
        print(f"\n📊 BREAKDOWN BY DOCUMENT TYPE:")
        for tipo, stats in type_breakdown.items():
            success_rate = (stats['found'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {tipo[:40]}: {stats['found']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Save detailed results
        output_file = "notion_based_decreto_search_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {output_file}")

def main():
    """Run the Notion-based decreto search."""
    
    scraper = NotionBasedDecretoScraper()
    
    print("🚀 Starting comprehensive decreto search based on Notion database content...")
    print("This will search for each deliberation using multiple strategies and terms.")
    print()
    
    results = scraper.search_all_notion_deliberations()
    
    if results:
        scraper.generate_final_report(results)
    else:
        print("❌ No search results to report")

if __name__ == "__main__":
    main()
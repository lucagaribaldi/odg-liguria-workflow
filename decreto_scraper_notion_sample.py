#!/usr/bin/env python3
"""
Sample decreto scraper that tests a few deliberations from Notion database
with comprehensive search strategies
"""

import json
import requests
import urllib3
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Optional
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SampleDecretoScraper:
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
    
    def create_search_strategies(self, delib: Dict) -> List[Dict]:
        """Create comprehensive search strategies for a specific deliberation."""
        
        numero = delib.get('numero', '')
        oggetto = delib.get('oggetto', '')
        proponente = delib.get('proponente', '')
        
        strategies = []
        
        # Strategy 1: DGR + numero (most specific)
        if numero:
            strategies.append({
                'term': f"DGR {numero}",
                'search_type': '2',  # Exact phrase
                'description': f'Exact "DGR {numero}"'
            })
        
        # Strategy 2: Just the number
        if numero:
            strategies.append({
                'term': numero,
                'search_type': '1',  # Any word
                'description': f'Number "{numero}" only'
            })
        
        # Strategy 3: Key words from oggetto
        if oggetto:
            # Extract first meaningful word from oggetto
            words = oggetto.split()[:3]  # First 3 words
            meaningful_words = [w for w in words if len(w) > 4 and w.upper() == w]  # Likely acronyms/important
            
            if meaningful_words:
                strategies.append({
                    'term': meaningful_words[0],
                    'search_type': '1',
                    'description': f'Key word from oggetto: "{meaningful_words[0]}"'
                })
        
        # Strategy 4: Proponent surname
        if proponente:
            parts = proponente.split()
            if len(parts) > 1:
                surname = parts[-1]  # Last part is usually surname
                strategies.append({
                    'term': surname,
                    'search_type': '1',
                    'description': f'Proponent surname: "{surname}"'
                })
        
        # Strategy 5: Generic deliberazione search with year
        strategies.append({
            'term': 'deliberazione',
            'search_type': '1',
            'use_year': '2025',
            'description': 'Generic "deliberazione" with year 2025'
        })
        
        return strategies[:3]  # Limit to top 3 to save time
    
    def execute_search_strategy(self, strategy: Dict, year_hint: str = None) -> Dict:
        """Execute a specific search strategy."""
        
        hidden_fields = self.get_form_tokens()
        
        form_data = {
            'unnamed_1': strategy['term'],
            'chkSearchType': strategy['search_type']
        }
        
        # Add year if specified
        if strategy.get('use_year') or year_hint:
            form_data['select_1'] = strategy.get('use_year', year_hint)
        
        # Add hidden fields
        form_data.update(hidden_fields)
        
        try:
            response = self.session.post(
                f"{self.base_url}/index.php",
                data=form_data,
                timeout=10,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self.analyze_search_results(soup, strategy)
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'strategy': strategy
            }
        
        return {'success': False, 'strategy': strategy}
    
    def analyze_search_results(self, soup: BeautifulSoup, strategy: Dict) -> Dict:
        """Analyze search results to determine if meaningful content was found."""
        
        page_text = soup.get_text().lower()
        
        # Check for "no results" indicators
        no_results_patterns = [
            'nessun risultato', 'no results', 'nessuna corrispondenza',
            'non trovato', 'not found', 'no matches'
        ]
        
        for pattern in no_results_patterns:
            if pattern in page_text:
                return {
                    'success': False,
                    'reason': f'No results pattern found: {pattern}',
                    'strategy': strategy
                }
        
        # Look for positive decreto indicators
        positive_indicators = ['dgr', 'delibera', 'decreto', 'giunta', 'regionale']
        found_indicators = [ind for ind in positive_indicators if ind in page_text]
        
        # Look for structured content (links, containers)
        links = soup.find_all('a', href=True)
        decreto_links = []
        
        for link in links:
            link_text = link.get_text(strip=True).lower()
            if len(link_text) > 10 and any(ind in link_text for ind in positive_indicators):
                decreto_links.append({
                    'text': link_text[:80],
                    'href': link.get('href')
                })
        
        # Determine if results are meaningful
        has_content = (
            len(found_indicators) >= 2 or  # Multiple positive indicators
            len(decreto_links) > 0 or      # Structured links found
            ('risultat' in page_text and len(found_indicators) >= 1)  # Results page with indicators
        )
        
        return {
            'success': has_content,
            'strategy': strategy,
            'indicators_found': found_indicators,
            'decreto_links': decreto_links[:3],  # Top 3 links
            'content_preview': self.extract_content_preview(soup)
        }
    
    def extract_content_preview(self, soup: BeautifulSoup) -> str:
        """Extract a brief preview of relevant content."""
        
        # Look for text blocks that might contain decreto content
        relevant_text = []
        
        for element in soup.find_all(['p', 'div', 'td', 'li']):
            text = element.get_text(strip=True)
            if (len(text) > 20 and len(text) < 200 and
                any(word in text.lower() for word in ['dgr', 'delibera', 'decreto', 'n.'])):
                relevant_text.append(text)
        
        if relevant_text:
            return relevant_text[0][:100] + "..."
        
        return "No specific content preview available"
    
    def test_sample_deliberations(self, sample_size: int = 5) -> Dict:
        """Test a sample of deliberations with comprehensive strategies."""
        
        print("🧪 TESTING DECRETO SEARCH ON SAMPLE DELIBERATIONS")
        print("=" * 65)
        
        deliberations = self.load_notion_deliberations()
        
        if not deliberations:
            return {'error': 'No deliberations loaded'}
        
        # Take a diverse sample
        sample_deliberations = []
        step = max(1, len(deliberations) // sample_size)
        for i in range(0, len(deliberations), step):
            if len(sample_deliberations) < sample_size:
                sample_deliberations.append(deliberations[i])
        
        print(f"📋 Testing {len(sample_deliberations)} deliberations from database of {len(deliberations)}")
        print()
        
        results = {
            'total_tested': len(sample_deliberations),
            'found': 0,
            'not_found': 0,
            'detailed_results': []
        }
        
        for i, delib in enumerate(sample_deliberations, 1):
            numero = delib.get('numero', 'N/A')
            oggetto = delib.get('oggetto', '')[:40]
            
            print(f"🔍 TEST {i}/{len(sample_deliberations)}: DGR {numero}")
            print(f"   Oggetto: {oggetto}...")
            
            # Create search strategies for this deliberation
            strategies = self.create_search_strategies(delib)
            
            delib_result = {
                'deliberation': {
                    'numero': numero,
                    'oggetto': oggetto,
                    'proponente': delib.get('proponente', ''),
                    'data_seduta': delib.get('data_seduta', '')
                },
                'strategies_tested': [],
                'found': False,
                'best_match': None
            }
            
            # Test each strategy
            for j, strategy in enumerate(strategies, 1):
                print(f"   📝 Strategy {j}: {strategy['description']}")
                
                search_result = self.execute_search_strategy(strategy, "2025")
                delib_result['strategies_tested'].append(search_result)
                
                if search_result.get('success'):
                    print(f"      ✅ SUCCESS!")
                    print(f"         Indicators: {search_result.get('indicators_found', [])}")
                    if search_result.get('decreto_links'):
                        print(f"         Links found: {len(search_result['decreto_links'])}")
                    
                    delib_result['found'] = True
                    delib_result['best_match'] = search_result
                    results['found'] += 1
                    break
                else:
                    reason = search_result.get('reason', 'No meaningful results')
                    print(f"      ❌ {reason}")
                
                time.sleep(1)  # Brief pause between strategies
            
            if not delib_result['found']:
                results['not_found'] += 1
                print(f"   💔 No matches found for DGR {numero}")
            
            results['detailed_results'].append(delib_result)
            print()
            
            time.sleep(2)  # Pause between deliberations
        
        return results
    
    def generate_sample_report(self, results: Dict):
        """Generate a report from the sample test."""
        
        print("🎯 SAMPLE TEST REPORT")
        print("=" * 40)
        print(f"Deliberations tested: {results['total_tested']}")
        print(f"Found on decreto site: {results['found']}")
        print(f"Not found: {results['not_found']}")
        
        if results['total_tested'] > 0:
            success_rate = (results['found'] / results['total_tested']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        # Show successful matches
        if results['found'] > 0:
            print(f"\n✅ SUCCESSFUL MATCHES:")
            for result in results['detailed_results']:
                if result['found']:
                    delib = result['deliberation']
                    best_match = result['best_match']
                    print(f"  • DGR {delib['numero']}: {delib['oggetto']}")
                    print(f"    Strategy: {best_match['strategy']['description']}")
                    
                    if best_match.get('content_preview'):
                        print(f"    Preview: {best_match['content_preview'][:60]}...")
        
        # Save results
        with open('sample_decreto_search_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: sample_decreto_search_results.json")

def main():
    scraper = SampleDecretoScraper()
    
    # Test with 5 sample deliberations
    results = scraper.test_sample_deliberations(5)
    
    if 'error' not in results:
        scraper.generate_sample_report(results)
    else:
        print(f"❌ Error: {results['error']}")

if __name__ == "__main__":
    main()
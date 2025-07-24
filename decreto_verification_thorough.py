#!/usr/bin/env python3
"""
Thorough verification to check if we're actually finding real decreto documents
or just generic search page content
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import json
import time
from typing import Dict

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ThoroughDecretoVerification:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_form_tokens(self):
        """Get form tokens."""
        response = self.session.get(self.base_url, timeout=10)
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
    
    def deep_analyze_search_results(self, search_term: str) -> Dict:
        """Perform deep analysis of search results to verify actual decreto content."""
        
        print(f"🔍 Deep analysis for: '{search_term}'")
        
        hidden_fields = self.get_form_tokens()
        
        # Multiple search approaches
        search_configs = [
            {
                'name': 'exact_2025',
                'data': {
                    'select_1': '2025',
                    'unnamed_1': search_term,
                    'chkSearchType': '2',  # Exact phrase
                    **hidden_fields
                },
                'description': f'2025 + exact "{search_term}"'
            },
            {
                'name': 'any_2025',
                'data': {
                    'select_1': '2025',
                    'unnamed_1': search_term,
                    'chkSearchType': '1',  # Any word
                    **hidden_fields
                },
                'description': f'2025 + any word "{search_term}"'
            },
            {
                'name': 'no_year_exact',
                'data': {
                    'unnamed_1': search_term,
                    'chkSearchType': '2',  # Exact phrase
                    **hidden_fields
                },
                'description': f'No year + exact "{search_term}"'
            },
            {
                'name': 'historical_test',
                'data': {
                    'select_1': '2020',
                    'unnamed_1': 'deliberazione',
                    'chkSearchType': '1',
                    **hidden_fields
                },
                'description': 'Historical test: 2020 + deliberazione'
            }
        ]
        
        results = {}
        
        for config in search_configs:
            print(f"  📋 Testing: {config['description']}")
            
            try:
                response = self.session.post(
                    f"{self.base_url}/index.php",
                    data=config['data'],
                    timeout=15,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    analysis = self.analyze_page_content(response.text, search_term)
                    analysis['config'] = config['description']
                    analysis['final_url'] = response.url
                    results[config['name']] = analysis
                    
                    print(f"     Status: {analysis['page_type']}")
                    print(f"     Decreto evidence: {analysis['decreto_evidence_score']}/10")
                    if analysis['specific_documents']:
                        print(f"     Documents found: {len(analysis['specific_documents'])}")
                    
                else:
                    results[config['name']] = {
                        'error': f"HTTP {response.status_code}",
                        'config': config['description']
                    }
                    print(f"     ❌ HTTP {response.status_code}")
                
            except Exception as e:
                results[config['name']] = {
                    'error': str(e),
                    'config': config['description']
                }
                print(f"     💥 Error: {str(e)}")
            
            time.sleep(1.5)
        
        return results
    
    def analyze_page_content(self, html_content: str, search_term: str) -> Dict:
        """Perform comprehensive analysis of page content to determine what we actually found."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        page_text = soup.get_text().lower()
        
        analysis = {
            'page_type': 'unknown',
            'decreto_evidence_score': 0,
            'specific_documents': [],
            'page_indicators': [],
            'content_analysis': {},
            'raw_content_sample': page_text[:500]
        }
        
        # 1. Identify page type
        if 'nessun risultato' in page_text or 'no results' in page_text:
            analysis['page_type'] = 'no_results'
        elif 'ricerca' in page_text and 'parola chiave' in page_text:
            analysis['page_type'] = 'search_interface'
        elif any(pattern in page_text for pattern in ['risultati', 'trovati', 'documenti']):
            analysis['page_type'] = 'results_page'
        else:
            analysis['page_type'] = 'other'
        
        # 2. Score decreto evidence (0-10)
        evidence_indicators = [
            ('dgr', 2),
            ('delibera', 2),
            ('decreto', 2),
            ('numero', 1),
            ('n.', 1),
            ('giunta regionale', 2),
            ('regione liguria', 1),
            ('del 20', 1)  # Date patterns
        ]
        
        for indicator, points in evidence_indicators:
            if indicator in page_text:
                analysis['decreto_evidence_score'] += points
                analysis['page_indicators'].append(indicator)
        
        # Cap at 10
        analysis['decreto_evidence_score'] = min(analysis['decreto_evidence_score'], 10)
        
        # 3. Look for specific document structures
        # Check for document-like patterns in text
        document_patterns = [
            r'dgr\s*n\.\s*\d+',           # DGR n. 123
            r'delibera\s*n\.\s*\d+',       # Delibera n. 123
            r'decreto\s*n\.\s*\d+',       # Decreto n. 123
            r'n\.\s*\d+\s*del\s*\d{4}',   # n. 123 del 2025
        ]
        
        import re
        for pattern in document_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                analysis['specific_documents'].append(match)
        
        # 4. Analyze structured content
        # Look for tables, lists, or containers that might hold documents
        structured_elements = {
            'tables': len(soup.find_all('table')),
            'lists': len(soup.find_all(['ul', 'ol'])),
            'article_containers': len(soup.find_all('article')),
            'result_divs': len(soup.select('div[class*="result"]')),
            'document_links': 0
        }
        
        # Count links that look like documents
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            if (len(link_text) > 15 and 
                any(word in link_text for word in ['dgr', 'delibera', 'decreto', 'n.'])):
                structured_elements['document_links'] += 1
        
        analysis['content_analysis'] = structured_elements
        
        # 5. Extract sample content that looks like decreto information
        potential_decreto_content = []
        for element in soup.find_all(['p', 'div', 'td', 'li']):
            text = element.get_text(strip=True)
            if (50 < len(text) < 300 and 
                any(word in text.lower() for word in ['dgr', 'delibera', 'decreto'])):
                potential_decreto_content.append(text)
        
        analysis['potential_decreto_content'] = potential_decreto_content[:3]
        
        return analysis
    
    def verify_sample_deliberations(self):
        """Verify a few deliberations with thorough analysis."""
        
        print("🔬 THOROUGH DECRETO VERIFICATION")
        print("=" * 50)
        
        # Test cases
        test_cases = [
            "DGR 1",
            "DGR 123",  # Unlikely to exist
            "deliberazione",
            "decreto numero 1"
        ]
        
        all_results = {}
        
        for test_case in test_cases:
            print(f"\n{'='*30}")
            print(f"Testing: {test_case}")
            print(f"{'='*30}")
            
            results = self.deep_analyze_search_results(test_case)
            all_results[test_case] = results
            
            # Summary for this test case
            best_evidence = 0
            best_config = None
            
            for config_name, result in results.items():
                if isinstance(result, dict) and 'decreto_evidence_score' in result:
                    score = result['decreto_evidence_score']
                    if score > best_evidence:
                        best_evidence = score
                        best_config = config_name
            
            if best_evidence > 0:
                print(f"\n  🎯 BEST RESULT for '{test_case}':")
                print(f"     Configuration: {best_config}")
                print(f"     Evidence score: {best_evidence}/10")
                
                best_result = results[best_config]
                if best_result.get('specific_documents'):
                    print(f"     Documents found: {best_result['specific_documents']}")
                if best_result.get('potential_decreto_content'):
                    print(f"     Sample content: {best_result['potential_decreto_content'][0][:80]}...")
            else:
                print(f"\n  ❌ No meaningful decreto evidence found for '{test_case}'")
            
            time.sleep(2)
        
        # Save comprehensive results
        with open('thorough_decreto_verification.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Comprehensive results saved to: thorough_decreto_verification.json")
        
        return all_results
    
    def final_assessment(self, all_results: Dict):
        """Provide final assessment of decreto website status."""
        
        print(f"\n🎯 FINAL ASSESSMENT")
        print("=" * 30)
        
        max_evidence_score = 0
        total_tests = 0
        successful_tests = 0
        
        for test_case, results in all_results.items():
            total_tests += 1
            
            best_score = 0
            for config_name, result in results.items():
                if isinstance(result, dict) and 'decreto_evidence_score' in result:
                    score = result['decreto_evidence_score']
                    best_score = max(best_score, score)
            
            max_evidence_score = max(max_evidence_score, best_score)
            
            if best_score > 3:  # Threshold for "meaningful" evidence
                successful_tests += 1
        
        print(f"Tests performed: {total_tests}")
        print(f"Tests with meaningful evidence: {successful_tests}")
        print(f"Maximum evidence score: {max_evidence_score}/10")
        
        # Interpretation
        if max_evidence_score < 3:
            print(f"\n🔴 CONCLUSION: The decreto website search is NOT finding actual published decreti.")
            print(f"   The searches return generic search interface content but no specific documents.")
            print(f"   This confirms that 2025 deliberations have not been published yet.")
        elif max_evidence_score < 6:
            print(f"\n🟡 CONCLUSION: Limited decreto content found.")
            print(f"   Some evidence exists but not comprehensive document results.")
        else:
            print(f"\n🟢 CONCLUSION: Substantial decreto content found!")
            print(f"   The website appears to contain published decreto documents.")

def main():
    verifier = ThoroughDecretoVerification()
    
    all_results = verifier.verify_sample_deliberations()
    verifier.final_assessment(all_results)

if __name__ == "__main__":
    main()
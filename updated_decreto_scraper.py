#!/usr/bin/env python3
"""
Updated Decreto Scraper using correct endpoints for decretidigitali.regione.liguria.it
Based on exploration results showing working Joomla search endpoints
"""

import sys
import os
import requests
import time
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime
import re
import logging
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class UpdatedDecretoScraper:
    """Updated scraper using correct endpoints."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False  # SSL issues
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def search_decreto(self, seduta: str, numero: str, oggetto: str = "") -> dict:
        """Search for a decreto using the working Joomla search endpoint."""
        
        result = {
            'found': False,
            'url': None,
            'data_pubblicazione': None,
            'search_method': 'joomla_search',
            'error': None
        }
        
        try:
            self.logger.info(f"Searching for decreto {numero} from seduta {seduta}")
            
            # Try Joomla search endpoint with different search terms
            search_terms = [
                f"delibera {numero}",
                f"seduta {seduta} numero {numero}",
                f"deliberazione {numero}",
                numero,
                f"{seduta} {numero}"
            ]
            
            for search_term in search_terms:
                self.logger.info(f"Trying search term: '{search_term}'")
                
                # Use the working endpoint we found
                search_url = f"{self.base_url}/index.php"
                params = {
                    'option': 'com_search',
                    'searchword': search_term
                }
                
                try:
                    response = self.session.get(search_url, params=params, timeout=10)
                    response.raise_for_status()
                    
                    # Parse search results
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for search results
                    # Check for common result containers
                    result_containers = soup.find_all(['div', 'article', 'li'], 
                                                    class_=re.compile('result|item|documento', re.I))
                    
                    if not result_containers:
                        # Look for any links that might be results
                        result_containers = soup.find_all('a', href=True)
                    
                    for container in result_containers:
                        container_text = container.get_text(strip=True).lower()
                        
                        # Check if this result matches our decreto
                        if self._matches_decreto(container_text, seduta, numero):
                            # Extract the link
                            link = container.get('href') if container.name == 'a' else None
                            if not link:
                                link_elem = container.find('a', href=True)
                                if link_elem:
                                    link = link_elem.get('href')
                            
                            if link:
                                # Make URL absolute
                                if link.startswith('/'):
                                    link = self.base_url + link
                                elif not link.startswith('http'):
                                    link = f"{self.base_url}/{link}"
                                
                                result['found'] = True
                                result['url'] = link
                                result['search_method'] = f'joomla_search_term_{search_term}'
                                
                                # Try to extract publication date
                                result['data_pubblicazione'] = self._extract_date(container_text)
                                
                                self.logger.info(f"✅ Found decreto: {link}")
                                return result
                    
                    # Check if there's a "no results" message
                    no_results_indicators = [
                        'nessun risultato', 'no results', 'nessuna corrispondenza',
                        'non trovato', 'not found'
                    ]
                    
                    page_text = soup.get_text().lower()
                    if any(indicator in page_text for indicator in no_results_indicators):
                        self.logger.info(f"No results found for term: {search_term}")
                        continue
                    
                    # If we get here, there might be results but we couldn't parse them
                    self.logger.info(f"Search completed but no matching decreto found for: {search_term}")
                    
                except requests.RequestException as e:
                    self.logger.warning(f"Request failed for search term '{search_term}': {str(e)}")
                    continue
                
                # Rate limiting
                time.sleep(0.5)
            
            # If we get here, no search terms worked
            result['error'] = f"No results found with any search term"
            return result
            
        except Exception as e:
            self.logger.error(f"Error searching decreto {numero}: {str(e)}")
            result['error'] = str(e)
            return result
    
    def _matches_decreto(self, text: str, seduta: str, numero: str) -> bool:
        """Check if text matches our decreto."""
        text = text.lower()
        
        # Look for various patterns that might indicate our decreto
        patterns = [
            rf"\b{numero}\b",  # Exact number match
            rf"seduta\s*{seduta}.*{numero}",  # Seduta and number
            rf"delibera.*{numero}",  # Delibera and number
            rf"numero\s*{numero}",  # "numero" and number
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return True
        
        return False
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Try to extract publication date from text."""
        # Look for date patterns
        date_patterns = [
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',  # DD/MM/YYYY
            r'(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2}\s+[a-zA-Z]+\s+\d{4})',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None

def test_updated_scraper():
    """Test the updated scraper with real deliberations."""
    
    print("🧪 TESTING UPDATED DECRETO SCRAPER")
    print("=" * 50)
    
    # Load environment variables for Notion access
    from dotenv import load_dotenv
    load_dotenv()
    
    from notion_integrator import NotionIntegrator
    
    # Get a few deliberations from Notion to test
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("❌ Missing Notion credentials")
        return
    
    # Initialize components
    integrator = NotionIntegrator(notion_token, database_id)
    scraper = UpdatedDecretoScraper()
    
    # Get some test deliberations
    print("📄 Getting test deliberations from Notion...")
    response = integrator._make_notion_request("query_database", database_id=database_id, page_size=3)
    
    test_cases = []
    for page in response["results"]:
        properties = page["properties"]
        seduta = integrator._extract_property_value(properties, "Seduta", "number")
        numero = integrator._extract_property_value(properties, "Numero", "number")
        oggetto = integrator._extract_property_value(properties, "Oggetto", "rich_text")
        
        if seduta and numero:
            test_cases.append({
                'seduta': str(seduta),
                'numero': str(numero),
                'oggetto': oggetto or ""
            })
    
    print(f"🔍 Testing {len(test_cases)} deliberations:")
    print("-" * 30)
    
    results = []
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing decreto {case['seduta']}/{case['numero']}")
        print(f"   Oggetto: {case['oggetto'][:60]}...")
        
        result = scraper.search_decreto(case['seduta'], case['numero'], case['oggetto'])
        results.append(result)
        
        if result['found']:
            print(f"   ✅ FOUND: {result['url']}")
            print(f"   📅 Date: {result.get('data_pubblicazione', 'N/A')}")
            print(f"   🔍 Method: {result['search_method']}")
        else:
            print(f"   ❌ Not found")
            if result.get('error'):
                print(f"   ⚠️  Error: {result['error']}")
    
    # Summary
    found_count = len([r for r in results if r['found']])
    print(f"\n📊 RESULTS SUMMARY:")
    print(f"✅ Found: {found_count}/{len(results)} ({found_count/len(results)*100:.1f}%)")
    print(f"❌ Not found: {len(results) - found_count}/{len(results)}")
    
    return results

if __name__ == "__main__":
    test_updated_scraper()
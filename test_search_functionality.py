#!/usr/bin/env python3
"""
Test Script for decretidigitali.regione.liguria.it Search Functionality

This script tests the actual search functionality to validate our analysis
and ensure we can successfully submit search requests and receive results.

Author: Website Analysis
Date: 2025-07-18
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchTester:
    """Test the search functionality of the decreti website"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.csrf_token = None
        self.csrf_field_name = None
    
    def get_main_page(self):
        """Get the main page and extract necessary information"""
        logger.info("Fetching main page...")
        response = self.session.get(self.base_url)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch main page: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract CSRF token
        # Look for input with a long hex name (32 chars)
        csrf_inputs = soup.find_all('input', {'name': re.compile(r'^[a-f0-9]{32}$')})
        if csrf_inputs:
            self.csrf_field_name = csrf_inputs[0]['name']
            logger.info(f"Found CSRF field: {self.csrf_field_name}")
        
        # Also check for the form action
        form = soup.find('form', {'id': 'frmVisTutti'})
        if form:
            action = form.get('action', '')
            logger.info(f"Form action: {action}")
        
        return response.text
    
    def test_simple_search(self, keyword="delibera", year="2024"):
        """Test a simple search with keyword and year"""
        logger.info(f"Testing search: keyword='{keyword}', year='{year}'")
        
        # Get main page first
        main_page = self.get_main_page()
        if not main_page:
            return None
        
        # Prepare search data
        search_data = {
            'txtOggetto': keyword,
            'chkSearchType': '1',  # At least one word
            'txtAnno': year,
            'txtTipoAtto': '',
            'txtNumero': '',
            'txtSoggettoEmanante': '',
            'DataSottoscrizione': '',
            'DataPubblicazione': '',
            'EstremiNumero': '',
            'EstremiAnno': '',
            'txtMateria': '',
            'txtArgomento': '',
            'txtOrderField': 'ld:dataPubblicazioneRicercaWeb',
            'maxResults': '10'
        }
        
        # Add CSRF token if found
        if self.csrf_field_name:
            search_data[self.csrf_field_name] = ''
        
        # Submit search
        logger.info("Submitting search...")
        response = self.session.post(
            f"{self.base_url}/index.php",
            data=search_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.base_url
            }
        )
        
        logger.info(f"Search response status: {response.status_code}")
        logger.info(f"Response content length: {len(response.text)}")
        
        if response.status_code == 200:
            return self.analyze_search_results(response.text)
        else:
            logger.error(f"Search failed with status {response.status_code}")
            return None
    
    def analyze_search_results(self, html_content):
        """Analyze the search results from the response"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for results in the risultati div
        results_div = soup.find('div', {'id': 'risultati'})
        
        analysis = {
            'has_results_div': bool(results_div),
            'results_div_content': '',
            'total_links': 0,
            'decreto_links': [],
            'error_messages': [],
            'success_indicators': []
        }
        
        if results_div:
            analysis['results_div_content'] = results_div.get_text().strip()[:500]  # First 500 chars
            logger.info(f"Found results div with content: {analysis['results_div_content'][:100]}...")
            
            # Look for links in results
            links = results_div.find_all('a')
            analysis['total_links'] = len(links)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text().strip()
                if href and text:
                    analysis['decreto_links'].append({
                        'href': href,
                        'text': text
                    })
        
        # Look for error messages
        error_indicators = [
            'errore', 'error', 'nessun risultato', 'no results', 
            'non trovato', 'not found'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in error_indicators:
            if indicator in page_text:
                analysis['error_messages'].append(indicator)
        
        # Look for success indicators
        success_indicators = [
            'risultat', 'trovato', 'found', 'documento', 'decreto', 'delibera'
        ]
        
        for indicator in success_indicators:
            if indicator in page_text:
                analysis['success_indicators'].append(indicator)
        
        return analysis
    
    def test_empty_search(self):
        """Test search with no parameters to see default behavior"""
        logger.info("Testing empty search...")
        return self.test_simple_search("", "")
    
    def test_year_only_search(self, year="2024"):
        """Test search with only year parameter"""
        logger.info(f"Testing year-only search: {year}")
        return self.test_simple_search("", year)
    
    def save_search_response(self, response_text, filename="search_response.html"):
        """Save the search response for manual inspection"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response_text)
            logger.info(f"Search response saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save response: {e}")
    
    def run_comprehensive_tests(self):
        """Run a comprehensive set of tests"""
        logger.info("Starting comprehensive search tests...")
        
        test_cases = [
            ("delibera", "2024"),
            ("decreto", "2023"),
            ("", "2024"),  # Year only
            ("giunta", ""),  # Keyword only
            ("", "")  # Empty search
        ]
        
        results = {}
        
        for i, (keyword, year) in enumerate(test_cases):
            test_name = f"test_{i+1}_{keyword or 'empty'}_{year or 'empty'}"
            logger.info(f"Running {test_name}...")
            
            try:
                result = self.test_simple_search(keyword, year)
                results[test_name] = result
                
                if result:
                    logger.info(f"✓ {test_name} completed")
                    logger.info(f"  - Results div found: {result['has_results_div']}")
                    logger.info(f"  - Links found: {result['total_links']}")
                    logger.info(f"  - Success indicators: {len(result['success_indicators'])}")
                    logger.info(f"  - Error messages: {len(result['error_messages'])}")
                else:
                    logger.warning(f"✗ {test_name} failed")
                
                # Save first successful response for inspection
                if result and result['has_results_div'] and not hasattr(self, '_saved_response'):
                    response = self.session.get(self.base_url)
                    search_response = self.session.post(
                        f"{self.base_url}/index.php",
                        data={
                            'txtOggetto': keyword,
                            'chkSearchType': '1',
                            'txtAnno': year,
                            'maxResults': '10',
                            self.csrf_field_name: '' if self.csrf_field_name else 'csrf_token'
                        }
                    )
                    self.save_search_response(search_response.text, f"search_response_{test_name}.html")
                    self._saved_response = True
                
                time.sleep(1)  # Be respectful to the server
                
            except Exception as e:
                logger.error(f"Error in {test_name}: {e}")
                results[test_name] = {'error': str(e)}
        
        return results
    
    def generate_test_report(self, results):
        """Generate a comprehensive test report"""
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'base_url': self.base_url,
            'csrf_field_found': bool(self.csrf_field_name),
            'csrf_field_name': self.csrf_field_name,
            'total_tests': len(results),
            'successful_tests': len([r for r in results.values() if r and not r.get('error')]),
            'failed_tests': len([r for r in results.values() if not r or r.get('error')]),
            'test_results': results,
            'conclusions': []
        }
        
        # Generate conclusions
        if report['successful_tests'] > 0:
            report['conclusions'].append("✓ Search functionality is accessible")
        else:
            report['conclusions'].append("✗ Search functionality appears to be broken")
        
        if report['csrf_field_found']:
            report['conclusions'].append("✓ CSRF token field identified")
        else:
            report['conclusions'].append("✗ CSRF token field not found")
        
        # Check for actual results
        has_real_results = any(
            r.get('total_links', 0) > 0 for r in results.values() 
            if r and not r.get('error')
        )
        
        if has_real_results:
            report['conclusions'].append("✓ Search returns actual results with links")
        else:
            report['conclusions'].append("? Search responses need manual inspection")
        
        return report


def main():
    """Main test execution"""
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    tester = SearchTester()
    
    # Run comprehensive tests
    results = tester.run_comprehensive_tests()
    
    # Generate and save report
    report = tester.generate_test_report(results)
    
    # Save detailed report
    with open('search_functionality_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*60)
    print("SEARCH FUNCTIONALITY TEST SUMMARY")
    print("="*60)
    print(f"Total tests run: {report['total_tests']}")
    print(f"Successful tests: {report['successful_tests']}")
    print(f"Failed tests: {report['failed_tests']}")
    print(f"CSRF field found: {report['csrf_field_found']}")
    print(f"CSRF field name: {report['csrf_field_name']}")
    print("\nConclusions:")
    for conclusion in report['conclusions']:
        print(f"  {conclusion}")
    
    print(f"\nDetailed report saved to: search_functionality_test_report.json")
    print("Check search_response_*.html files for manual inspection")
    print("="*60)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Website Structure Explorer for decretidigitali.regione.liguria.it

This script thoroughly explores the website structure to understand:
1. Available endpoints and their responses
2. Search functionality and forms
3. Navigation structure
4. Links to decreto or search pages
5. Overall site architecture

Author: Website Structure Explorer
Date: 2025-07-18
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, List, Optional, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('exploration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebsiteExplorer:
    """Comprehensive website structure explorer"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification as requested
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Results storage
        self.results = {
            'base_url': base_url,
            'exploration_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'endpoints': {},
            'forms': [],
            'search_functionality': [],
            'navigation_links': [],
            'external_links': [],
            'potential_decreto_links': [],
            'javascript_references': [],
            'meta_information': {},
            'errors': []
        }
        
        # Common endpoints to test
        self.test_endpoints = [
            '/',
            '/cerca',
            '/ricerca',
            '/search',
            '/decreti',
            '/delibere',
            '/bandi',
            '/pubblicazioni',
            '/dgr',
            '/dcr',
            '/atti',
            '/documenti',
            '/amministrazione',
            '/trasparenza',
            '/albo',
            '/pretorio',
            '/normativa',
            '/circolari',
            '/determinazioni',
            '/ordinanze',
            '/provvedimenti',
            '/registro',
            '/archivio',
            '/elenco',
            '/lista',
            '/consultazione',
            '/visualizza',
            '/dettaglio',
            '/risultati',
            '/api',
            '/api/search',
            '/api/decreti',
            '/sitemap.xml',
            '/robots.txt'
        ]
    
    def safe_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make a safe HTTP request with error handling"""
        try:
            logger.info(f"Requesting {method} {url}")
            response = self.session.request(method, url, timeout=10, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            self.results['errors'].append({
                'url': url,
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return None
    
    def analyze_html(self, html_content: str, url: str) -> Dict:
        """Analyze HTML content for structure and functionality"""
        soup = BeautifulSoup(html_content, 'html.parser')
        analysis = {
            'title': '',
            'meta_description': '',
            'forms': [],
            'links': [],
            'search_elements': [],
            'navigation_elements': [],
            'content_sections': [],
            'javascript_files': [],
            'css_files': [],
            'potential_decreto_elements': []
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            analysis['title'] = title_tag.get_text().strip()
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            analysis['meta_description'] = meta_desc.get('content', '')
        
        # Find all forms
        forms = soup.find_all('form')
        for form in forms:
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET').upper(),
                'inputs': [],
                'has_search_indicators': False
            }
            
            # Analyze form inputs
            inputs = form.find_all(['input', 'select', 'textarea'])
            for input_elem in inputs:
                input_data = {
                    'name': input_elem.get('name', ''),
                    'type': input_elem.get('type', ''),
                    'value': input_elem.get('value', ''),
                    'placeholder': input_elem.get('placeholder', ''),
                    'id': input_elem.get('id', '')
                }
                form_data['inputs'].append(input_data)
                
                # Check for search indicators
                search_terms = ['search', 'cerca', 'ricerca', 'query', 'q', 'termine']
                if any(term in str(input_data).lower() for term in search_terms):
                    form_data['has_search_indicators'] = True
            
            analysis['forms'].append(form_data)
        
        # Find all links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            text = link.get_text().strip()
            
            # Resolve relative URLs
            full_url = urljoin(url, href)
            
            link_data = {
                'href': href,
                'full_url': full_url,
                'text': text,
                'title': link.get('title', ''),
                'is_external': not href.startswith('/') and not href.startswith(self.base_url)
            }
            
            analysis['links'].append(link_data)
            
            # Check for potential decreto-related links
            decreto_terms = ['decreto', 'delibera', 'dgr', 'dcr', 'determina', 'ordinanza', 'provvedimento']
            if any(term in text.lower() or term in href.lower() for term in decreto_terms):
                analysis['potential_decreto_elements'].append(link_data)
        
        # Find search-related elements
        search_elements = soup.find_all(lambda tag: tag.name and 
                                       any(term in str(tag).lower() for term in ['search', 'cerca', 'ricerca']))
        for elem in search_elements:
            analysis['search_elements'].append({
                'tag': elem.name,
                'attributes': dict(elem.attrs),
                'text': elem.get_text().strip()[:100]  # Limit text length
            })
        
        # Find navigation elements
        nav_elements = soup.find_all(['nav', 'ul', 'ol'])
        for nav in nav_elements:
            if nav.find('a'):  # Only include if it contains links
                analysis['navigation_elements'].append({
                    'tag': nav.name,
                    'class': nav.get('class', []),
                    'id': nav.get('id', ''),
                    'link_count': len(nav.find_all('a'))
                })
        
        # Find JavaScript and CSS files
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src')
            if src:
                analysis['javascript_files'].append(urljoin(url, src))
        
        styles = soup.find_all('link', rel='stylesheet')
        for style in styles:
            href = style.get('href')
            if href:
                analysis['css_files'].append(urljoin(url, href))
        
        # Find content sections
        content_sections = soup.find_all(['main', 'section', 'article', 'div'])
        for section in content_sections:
            if section.get('class') or section.get('id'):
                analysis['content_sections'].append({
                    'tag': section.name,
                    'class': section.get('class', []),
                    'id': section.get('id', ''),
                    'text_length': len(section.get_text().strip())
                })
        
        return analysis
    
    def explore_endpoint(self, endpoint: str) -> Dict:
        """Explore a specific endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        result = {
            'endpoint': endpoint,
            'url': url,
            'status_code': None,
            'response_time': None,
            'content_type': None,
            'content_length': None,
            'headers': {},
            'analysis': None,
            'error': None
        }
        
        start_time = time.time()
        response = self.safe_request(url)
        
        if response:
            result['status_code'] = response.status_code
            result['response_time'] = time.time() - start_time
            result['content_type'] = response.headers.get('content-type', '')
            result['content_length'] = len(response.content)
            result['headers'] = dict(response.headers)
            
            if response.status_code == 200 and 'text/html' in result['content_type']:
                result['analysis'] = self.analyze_html(response.text, url)
                
                # Save HTML for manual inspection if this is the main page
                if endpoint == '/':
                    self.save_html(response.text, 'main_page.html')
        else:
            result['error'] = 'Request failed'
        
        return result
    
    def save_html(self, html_content: str, filename: str):
        """Save HTML content to file for manual inspection"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Saved HTML content to {filename}")
        except Exception as e:
            logger.error(f"Failed to save HTML to {filename}: {str(e)}")
    
    def explore_discovered_links(self, max_links: int = 10):
        """Explore interesting links discovered during initial exploration"""
        interesting_links = []
        
        # Collect interesting links from all successful endpoints
        for endpoint_data in self.results['endpoints'].values():
            if endpoint_data.get('analysis') and endpoint_data['analysis'].get('potential_decreto_elements'):
                for link in endpoint_data['analysis']['potential_decreto_elements']:
                    if link['full_url'] not in [l['url'] for l in interesting_links]:
                        interesting_links.append({
                            'url': link['full_url'],
                            'text': link['text'],
                            'source_endpoint': endpoint_data['endpoint']
                        })
        
        # Explore top interesting links
        for i, link in enumerate(interesting_links[:max_links]):
            logger.info(f"Exploring discovered link {i+1}/{min(max_links, len(interesting_links))}: {link['url']}")
            
            # Parse URL to get endpoint
            parsed = urlparse(link['url'])
            if parsed.netloc == urlparse(self.base_url).netloc:
                endpoint = parsed.path
                if endpoint not in self.results['endpoints']:
                    result = self.explore_endpoint(endpoint)
                    self.results['endpoints'][endpoint] = result
                    time.sleep(1)  # Be respectful to the server
    
    def analyze_site_structure(self):
        """Analyze the overall site structure based on findings"""
        analysis = {
            'successful_endpoints': [],
            'failed_endpoints': [],
            'search_functionality_found': False,
            'forms_found': 0,
            'potential_search_forms': [],
            'navigation_structure': [],
            'decreto_related_content': [],
            'recommendations': []
        }
        
        for endpoint, data in self.results['endpoints'].items():
            if data['status_code'] == 200:
                analysis['successful_endpoints'].append({
                    'endpoint': endpoint,
                    'title': data['analysis']['title'] if data['analysis'] else '',
                    'forms': len(data['analysis']['forms']) if data['analysis'] else 0
                })
                
                if data['analysis']:
                    analysis['forms_found'] += len(data['analysis']['forms'])
                    
                    # Check for search functionality
                    for form in data['analysis']['forms']:
                        if form['has_search_indicators']:
                            analysis['potential_search_forms'].append({
                                'endpoint': endpoint,
                                'form': form
                            })
                            analysis['search_functionality_found'] = True
                    
                    # Collect decreto-related content
                    if data['analysis']['potential_decreto_elements']:
                        analysis['decreto_related_content'].extend(data['analysis']['potential_decreto_elements'])
            else:
                analysis['failed_endpoints'].append({
                    'endpoint': endpoint,
                    'status_code': data['status_code'],
                    'error': data['error']
                })
        
        # Generate recommendations
        if analysis['search_functionality_found']:
            analysis['recommendations'].append("Search functionality detected - examine forms for proper usage")
        else:
            analysis['recommendations'].append("No obvious search functionality found - may need to explore JavaScript or AJAX endpoints")
        
        if analysis['decreto_related_content']:
            analysis['recommendations'].append("Decreto-related content found - explore these links for scraping opportunities")
        else:
            analysis['recommendations'].append("No obvious decreto-related content found in main navigation")
        
        return analysis
    
    def run_exploration(self):
        """Run the complete exploration process"""
        logger.info(f"Starting exploration of {self.base_url}")
        
        # Explore all test endpoints
        for endpoint in self.test_endpoints:
            result = self.explore_endpoint(endpoint)
            self.results['endpoints'][endpoint] = result
            time.sleep(0.5)  # Be respectful to the server
        
        # Explore discovered links
        logger.info("Exploring discovered links...")
        self.explore_discovered_links()
        
        # Analyze overall structure
        logger.info("Analyzing site structure...")
        self.results['site_analysis'] = self.analyze_site_structure()
        
        # Save results
        self.save_results()
        
        # Generate summary report
        self.generate_summary_report()
    
    def save_results(self):
        """Save complete results to JSON file"""
        try:
            with open('exploration_results.json', 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info("Saved complete results to exploration_results.json")
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
    
    def generate_summary_report(self):
        """Generate a human-readable summary report"""
        report = []
        report.append("=" * 80)
        report.append(f"WEBSITE EXPLORATION SUMMARY REPORT")
        report.append(f"Site: {self.base_url}")
        report.append(f"Timestamp: {self.results['exploration_timestamp']}")
        report.append("=" * 80)
        
        # Successful endpoints
        successful = [ep for ep, data in self.results['endpoints'].items() if data['status_code'] == 200]
        report.append(f"\nSUCCESSFUL ENDPOINTS ({len(successful)}):")
        for endpoint in successful:
            data = self.results['endpoints'][endpoint]
            title = data['analysis']['title'] if data['analysis'] else 'No title'
            report.append(f"  {endpoint:<20} - {title}")
        
        # Failed endpoints
        failed = [ep for ep, data in self.results['endpoints'].items() if data['status_code'] != 200]
        report.append(f"\nFAILED ENDPOINTS ({len(failed)}):")
        for endpoint in failed:
            data = self.results['endpoints'][endpoint]
            status = data['status_code'] or 'No response'
            report.append(f"  {endpoint:<20} - Status: {status}")
        
        # Search functionality
        search_forms = self.results['site_analysis']['potential_search_forms']
        report.append(f"\nSEARCH FUNCTIONALITY:")
        if search_forms:
            report.append(f"  Found {len(search_forms)} potential search forms:")
            for form_info in search_forms:
                report.append(f"    - {form_info['endpoint']}: {form_info['form']['method']} {form_info['form']['action']}")
        else:
            report.append("  No obvious search forms found")
        
        # Decreto-related content
        decreto_content = self.results['site_analysis']['decreto_related_content']
        report.append(f"\nDECRETO-RELATED CONTENT:")
        if decreto_content:
            report.append(f"  Found {len(decreto_content)} decreto-related links:")
            for link in decreto_content[:10]:  # Show first 10
                report.append(f"    - {link['text'][:50]}... -> {link['href']}")
        else:
            report.append("  No decreto-related content found")
        
        # Recommendations
        recommendations = self.results['site_analysis']['recommendations']
        report.append(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            report.append(f"  {i}. {rec}")
        
        # Errors
        if self.results['errors']:
            report.append(f"\nERRORS ENCOUNTERED ({len(self.results['errors'])}):")
            for error in self.results['errors'][:5]:  # Show first 5
                report.append(f"  - {error['url']}: {error['error']}")
        
        report.append("\n" + "=" * 80)
        report.append("For detailed information, see exploration_results.json")
        report.append("For manual inspection, see main_page.html")
        report.append("=" * 80)
        
        # Save and display report
        report_text = "\n".join(report)
        
        try:
            with open('exploration_summary.txt', 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info("Saved summary report to exploration_summary.txt")
        except Exception as e:
            logger.error(f"Failed to save summary report: {str(e)}")
        
        print("\n" + report_text)


def main():
    """Main execution function"""
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    explorer = WebsiteExplorer(base_url)
    explorer.run_exploration()


if __name__ == "__main__":
    main()
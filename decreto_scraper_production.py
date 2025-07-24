#!/usr/bin/env python3
"""
Production decreto scraper con gestione avanzata delle protezioni del sito
e implementazione completa del workflow richiesto.
"""

import json
import requests
import urllib3
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
from urllib.parse import urljoin, urlparse

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ProductionDecretoScraper:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        
        # Enhanced headers to bypass anti-bot protection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        # Load Notion credentials
        self.notion_token = None
        self.notion_db_id = None
        self.load_notion_credentials()
        
    def load_notion_credentials(self):
        """Load Notion API credentials."""
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('NOTION_TOKEN='):
                        self.notion_token = line.split('=', 1)[1].strip()
                    elif line.startswith('NOTION_DATABASE_ID='):
                        self.notion_db_id = line.split('=', 1)[1].strip()
            
            if self.notion_token:
                print("✅ Notion credentials loaded")
        except FileNotFoundError:
            print("⚠️ .env file not found")
    
    def establish_session(self) -> bool:
        """Establish a proper session with the website."""
        
        print("🔐 Establishing session with decreto website...")
        
        try:
            # First, visit the homepage to establish session
            response = self.session.get(self.base_url, timeout=20)
            
            if response.status_code == 200:
                print("✅ Session established successfully")
                
                # Update headers with any session-specific values
                if 'Set-Cookie' in response.headers:
                    print("🍪 Session cookies received")
                
                return True
            else:
                print(f"❌ Failed to establish session: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"💥 Session establishment error: {str(e)}")
            return False
    
    def analyze_form_structure(self) -> Dict:
        """Analyze the current form structure in detail."""
        
        print("🔍 Analyzing current form structure...")
        
        try:
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find main form
            main_form = soup.find('form', action='index.php')
            if not main_form:
                print("❌ Main form not found")
                return {}
            
            form_analysis = {
                'action': main_form.get('action'),
                'method': main_form.get('method', 'GET'),
                'fields': {},
                'selects': {},
                'buttons': []
            }
            
            # Analyze all form elements
            print("📋 Form elements found:")
            
            # Input fields
            for inp in main_form.find_all('input'):
                inp_type = inp.get('type', 'text')
                inp_name = inp.get('name', 'unnamed')
                inp_value = inp.get('value', '')
                
                form_analysis['fields'][inp_name] = {
                    'type': inp_type,
                    'value': inp_value,
                    'required': inp.has_attr('required')
                }
                
                if inp_type not in ['hidden', 'submit']:
                    print(f"   📝 {inp_name}: {inp_type} = '{inp_value}'")
            
            # Select dropdowns
            for select in main_form.find_all('select'):
                select_name = select.get('name', 'unnamed')
                options = []
                
                for option in select.find_all('option'):
                    opt_value = option.get('value', '')
                    opt_text = option.get_text(strip=True)
                    selected = option.has_attr('selected')
                    
                    options.append({
                        'value': opt_value,
                        'text': opt_text,
                        'selected': selected
                    })
                
                form_analysis['selects'][select_name] = options
                print(f"   📋 {select_name}: {len(options)} options")
                
                # Show options for anno and type selects
                if 'select_1' in select_name or 'anno' in select_name.lower():
                    print(f"      Years available: {[opt['value'] for opt in options if opt['value']]}")
                elif 'select_2' in select_name or 'tipo' in select_name.lower():
                    print(f"      Types available: {[opt['text'] for opt in options if opt['value']]}")
            
            # Buttons
            for button in main_form.find_all(['input', 'button']):
                if button.get('type') in ['submit', 'button'] or button.name == 'button':
                    btn_name = button.get('name', button.get('id', 'unnamed'))
                    btn_value = button.get('value', button.get_text(strip=True))
                    
                    form_analysis['buttons'].append({
                        'name': btn_name,
                        'value': btn_value,
                        'type': button.get('type', 'button')
                    })
                    
                    print(f"   🔘 Button: {btn_name} = '{btn_value}'")
            
            return form_analysis
            
        except Exception as e:
            print(f"💥 Error analyzing form: {str(e)}")
            return {}
    
    def test_search_functionality(self) -> bool:
        """Test basic search functionality to understand the workflow."""
        
        print("\n🧪 TESTING SEARCH FUNCTIONALITY")
        print("=" * 40)
        
        # First establish session
        if not self.establish_session():
            return False
        
        # Analyze current form
        form_data = self.analyze_form_structure()
        
        if not form_data:
            return False
        
        print(f"\n🔧 Testing with minimal search parameters...")
        
        try:
            # Get fresh form state
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            main_form = soup.find('form', action='index.php')
            
            if not main_form:
                print("❌ Cannot find form for testing")
                return False
            
            # Build minimal form data
            test_form_data = {}
            
            # Add all hidden fields
            for hidden in main_form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value', '')
                if name:
                    test_form_data[name] = value
            
            # Set search parameters
            # Try year 2020 (should have data based on previous analysis)
            if 'select_1' in form_data['selects']:
                available_years = [opt['value'] for opt in form_data['selects']['select_1'] if opt['value']]
                if '2020' in available_years:
                    test_form_data['select_1'] = '2020'
                    print(f"   📅 Setting year: 2020")
                elif available_years:
                    test_form_data['select_1'] = available_years[-1]  # Most recent
                    print(f"   📅 Setting year: {available_years[-1]}")
            
            # Set document type if available
            if 'select_2' in form_data['selects']:
                available_types = [opt for opt in form_data['selects']['select_2'] if opt['value']]
                for opt in available_types:
                    if 'delibera' in opt['text'].lower():
                        test_form_data['select_2'] = opt['value']
                        print(f"   📋 Setting type: {opt['text']}")
                        break
            
            # Set basic search parameters
            test_form_data['chkSearchType'] = '1'  # Any word search
            test_form_data['unnamed_1'] = 'deliberazione'  # Keyword
            
            # Set results per page to maximum
            results_field = None
            for field_name in test_form_data.keys():
                if 'result' in field_name.lower() or len(field_name) > 20:  # Likely the results field
                    results_field = field_name
                    break
            
            if results_field:
                test_form_data[results_field] = '50'
                print(f"   📊 Setting results per page: 50")
            
            print(f"\n🔄 Submitting test search...")
            print(f"Form data keys: {list(test_form_data.keys())}")
            
            # Submit with GET method first (safer)
            if form_data.get('method', '').upper() == 'POST':
                search_response = self.session.post(
                    f"{self.base_url}/index.php",
                    data=test_form_data,
                    timeout=20,
                    allow_redirects=True
                )
            else:
                search_response = self.session.get(
                    f"{self.base_url}/index.php",
                    params=test_form_data,
                    timeout=20,
                    allow_redirects=True
                )
            
            print(f"   Response status: {search_response.status_code}")
            print(f"   Response URL: {search_response.url}")
            
            if search_response.status_code == 200:
                # Analyze results
                result_soup = BeautifulSoup(search_response.text, 'html.parser')
                
                # Look for results indicators
                page_text = result_soup.get_text().lower()
                
                result_indicators = [
                    'risultat', 'trovato', 'documento', 'delibera', 'dgr', 'n.'
                ]
                
                found_indicators = [ind for ind in result_indicators if ind in page_text]
                
                print(f"   Content indicators found: {found_indicators}")
                
                # Look for pagination
                pagination_links = result_soup.find_all('a', href=True)
                page_links = [link for link in pagination_links 
                            if any(word in link.get_text().lower() for word in ['page', 'next', 'successiv'])]
                
                if page_links:
                    print(f"   📄 Pagination found: {len(page_links)} navigation links")
                
                # Look for attachment/document links
                doc_links = []
                for link in result_soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if (any(ext in href.lower() for ext in ['.pdf', '.doc']) or
                        'reg_amm' in href.lower() or 'reg_amm' in text.lower() or
                        any(word in text.lower() for word in ['allegat', 'scarica', 'documento'])):
                        doc_links.append({
                            'url': href,
                            'text': text
                        })
                
                if doc_links:
                    print(f"   📎 Document links found: {len(doc_links)}")
                    for i, doc in enumerate(doc_links[:3], 1):  # Show first 3
                        print(f"      {i}. {doc['text'][:50]}...")
                
                print(f"✅ Search functionality test completed")
                return True
            else:
                print(f"❌ Search failed with status: {search_response.status_code}")
                print(f"Response content preview: {search_response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"💥 Search test error: {str(e)}")
            return False
    
    def search_year_with_full_workflow(self, year: str) -> List[Dict]:
        """
        Execute complete search workflow for a specific year:
        1. Select year in dropdown
        2. Select "Deliberazione" type
        3. Set max results per page
        4. Submit search
        5. Navigate all pages
        6. Extract REG_AMM attachments
        """
        
        print(f"\n🎯 FULL WORKFLOW SEARCH FOR YEAR {year}")
        print("=" * 50)
        
        all_deliberazioni = []
        
        try:
            # Step 1: Get initial form state
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            main_form = soup.find('form', action='index.php')
            
            if not main_form:
                print("❌ Cannot find search form")
                return []
            
            # Step 2: Build complete form data
            form_data = {}
            
            # Add all hidden fields
            for hidden in main_form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value', '')
                if name:
                    form_data[name] = value
            
            # Step 3: Configure search parameters
            print("🔧 Configuring search parameters...")
            
            # Set year
            form_data['select_1'] = year
            print(f"   📅 Year: {year}")
            
            # Set document type to deliberazione (if available)
            type_select = main_form.find('select', attrs={'name': 'select_2'})
            if type_select:
                for option in type_select.find_all('option'):
                    text = option.get_text(strip=True).lower()
                    if 'delibera' in text:
                        form_data['select_2'] = option.get('value', '')
                        print(f"   📋 Type: {option.get_text(strip=True)}")
                        break
            
            # Set search mode and keyword
            form_data['chkSearchType'] = '1'  # Any word
            form_data['unnamed_1'] = 'deliberazione'
            print(f"   🔍 Keyword: deliberazione")
            
            # Set maximum results per page
            for field_name, field_info in [('8877ea8e05085d5bf2a469b94f5c4ddf', 'results_per_page')]:
                if field_name in [inp.get('name') for inp in main_form.find_all('input')]:
                    form_data[field_name] = '100'  # Max results
                    print(f"   📊 Results per page: 100")
                    break
            
            # Step 4: Submit initial search
            print("🔄 Submitting search...")
            
            search_response = self.session.post(
                f"{self.base_url}/index.php",
                data=form_data,
                timeout=20,
                allow_redirects=True
            )
            
            if search_response.status_code != 200:
                print(f"❌ Search failed: {search_response.status_code}")
                return []
            
            print(f"✅ Search submitted successfully")
            
            # Step 5: Process all result pages
            page_num = 1
            current_response = search_response
            
            while current_response and page_num <= 10:  # Safety limit
                print(f"\n📄 Processing results page {page_num}...")
                
                page_deliberazioni = self.extract_deliberazioni_from_search_results(
                    current_response.text, year, page_num
                )
                
                if page_deliberazioni:
                    all_deliberazioni.extend(page_deliberazioni)
                    print(f"   ✅ Found {len(page_deliberazioni)} deliberazioni")
                else:
                    print(f"   📭 No deliberazioni found")
                
                # Look for next page
                next_url = self.find_next_page_link(current_response.text)
                
                if not next_url:
                    print(f"   📄 No more pages")
                    break
                
                # Navigate to next page
                print(f"   ➡️ Navigating to next page...")
                time.sleep(3)  # Be respectful
                
                try:
                    current_response = self.session.get(next_url, timeout=20)
                    if current_response.status_code != 200:
                        print(f"   ❌ Failed to load page {page_num + 1}")
                        break
                except Exception as e:
                    print(f"   💥 Error loading next page: {str(e)}")
                    break
                
                page_num += 1
            
            print(f"\n🎯 Search completed for {year}")
            print(f"   Total deliberazioni found: {len(all_deliberazioni)}")
            
            return all_deliberazioni
            
        except Exception as e:
            print(f"💥 Workflow error for year {year}: {str(e)}")
            return []
    
    def extract_deliberazioni_from_search_results(self, html_content: str, year: str, page_num: int) -> List[Dict]:
        """Extract deliberazioni with REG_AMM attachments from search results."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        deliberazioni = []
        
        # Look for result containers
        # Try multiple selectors for different page layouts
        container_selectors = [
            'div[class*="risultato"]',
            'div[class*="result"]',
            'div[class*="item"]',
            'tr[class*="result"]',
            'li[class*="documento"]',
            '.search-result',
            '.documento',
            'article'
        ]
        
        result_containers = []
        for selector in container_selectors:
            containers = soup.select(selector)
            for container in containers:
                text = container.get_text(strip=True)
                if (len(text) > 30 and 
                    any(keyword in text.lower() for keyword in ['dgr', 'delibera', 'n.', 'del 20'])):
                    result_containers.append(container)
        
        # If no structured containers, look for DGR patterns in the whole page
        if not result_containers:
            # Extract DGR numbers from page text
            page_text = soup.get_text()
            dgr_patterns = re.findall(r'DGR\s+n?\s*\.?\s*(\d+)[^\n]*(?:del\s+[\d/]+)?', page_text, re.IGNORECASE)
            
            for numero in dgr_patterns:
                # Look for links near this DGR mention
                reg_amm_links = []
                
                # Find all links and check if they're related to this DGR
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Check if this link is a REG_AMM attachment
                    if (re.search(r'REG_AMM_\w*', href, re.IGNORECASE) or
                        re.search(r'REG_AMM_\w*', text, re.IGNORECASE) or
                        (numero in href or numero in text)):
                        
                        full_url = self.make_absolute_url(href)
                        reg_amm_links.append({
                            'url': full_url,
                            'text': text,
                            'type': 'REG_AMM'
                        })
                
                if reg_amm_links:  # Only include if we found attachments
                    deliberazioni.append({
                        'numero': numero,
                        'year': year,
                        'page': page_num,
                        'reg_amm_attachments': reg_amm_links,
                        'extraction_method': 'text_pattern'
                    })
        
        # Process structured containers
        for i, container in enumerate(result_containers):
            try:
                delib_info = self.parse_deliberazione_result(container, year, page_num, i+1)
                if delib_info:
                    deliberazioni.append(delib_info)
            except Exception as e:
                print(f"     ⚠️ Error parsing container {i+1}: {str(e)}")
        
        return deliberazioni
    
    def parse_deliberazione_result(self, container, year: str, page_num: int, index: int) -> Optional[Dict]:
        """Parse a single deliberazione result container."""
        
        text = container.get_text(strip=True)
        
        # Extract DGR number
        numero_patterns = [
            r'DGR\s+n?\s*\.?\s*(\d+)',
            r'delibera(?:zione)?\s+n?\s*\.?\s*(\d+)',
            r'n\.\s*(\d+)',
        ]
        
        numero = None
        for pattern in numero_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                numero = match.group(1)
                break
        
        if not numero:
            return None
        
        # Find all links in this container
        links = container.find_all('a', href=True)
        reg_amm_attachments = []
        
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Check for REG_AMM or document attachments
            is_reg_amm = (
                re.search(r'REG_AMM_\w*', href, re.IGNORECASE) or
                re.search(r'REG_AMM_\w*', link_text, re.IGNORECASE) or
                any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx']) or
                any(word in link_text.lower() for word in ['allegat', 'documento', 'scarica', 'download'])
            )
            
            if is_reg_amm:
                full_url = self.make_absolute_url(href)
                
                reg_amm_attachments.append({
                    'url': full_url,
                    'text': link_text,
                    'type': 'REG_AMM' if 'reg_amm' in (href + link_text).lower() else 'document'
                })
        
        # Extract additional metadata
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
        
        return {
            'numero': numero,
            'year': year,
            'page': page_num,
            'index': index,
            'raw_text': text[:300],
            'date_found': date_match.group(1) if date_match else None,
            'reg_amm_attachments': reg_amm_attachments,
            'extraction_method': 'structured_container'
        }
    
    def make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL."""
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return self.base_url + url
        else:
            return urljoin(self.base_url, url)
    
    def find_next_page_link(self, html_content: str) -> Optional[str]:
        """Find the URL for the next page in pagination."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for pagination links
        pagination_indicators = [
            'next', 'successiv', 'avanti', 'prossim', '>', '»', '›'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Check if this looks like a next page link
            for indicator in pagination_indicators:
                if indicator in text or indicator in href:
                    return self.make_absolute_url(href)
        
        # Also look for numbered page links (try page + 1)
        current_page_links = soup.find_all('a', href=True)
        for link in current_page_links:
            href = link.get('href', '')
            # Look for page numbers in URL
            page_match = re.search(r'page[=:](\d+)', href, re.IGNORECASE)
            if page_match:
                current_page_num = int(page_match.group(1))
                next_page_url = href.replace(f'page={current_page_num}', f'page={current_page_num + 1}')
                return self.make_absolute_url(next_page_url)
        
        return None
    
    def update_notion_with_reg_amm_urls(self, deliberazioni: List[Dict]) -> Dict:
        """Update Notion database with REG_AMM URLs in url-decreto field."""
        
        if not self.notion_token:
            print("⚠️ Notion credentials not available - skipping updates")
            return {'updated': 0, 'errors': []}
        
        print(f"\n📝 UPDATING NOTION WITH REG_AMM URLs")
        print("=" * 45)
        
        results = {'updated': 0, 'errors': [], 'not_found': 0, 'no_attachments': 0}
        
        for delib in deliberazioni:
            numero = delib['numero']
            attachments = delib.get('reg_amm_attachments', [])
            
            if not attachments:
                results['no_attachments'] += 1
                continue
            
            # Find the best REG_AMM attachment
            reg_amm_url = None
            for att in attachments:
                if att['type'] == 'REG_AMM':
                    reg_amm_url = att['url']
                    break
            
            # If no specific REG_AMM, use first attachment
            if not reg_amm_url and attachments:
                reg_amm_url = attachments[0]['url']
            
            if reg_amm_url:
                # Find Notion page and update url-decreto field
                page_id = self.find_notion_page_by_numero(numero)
                
                if page_id:
                    success = self.update_notion_url_decreto(page_id, reg_amm_url)
                    if success:
                        results['updated'] += 1
                        print(f"   ✅ DGR {numero}: url-decreto updated")
                    else:
                        results['errors'].append(f"DGR {numero}: Update failed")
                        print(f"   ❌ DGR {numero}: Update failed")
                else:
                    results['not_found'] += 1
                    print(f"   ⚠️ DGR {numero}: Not found in Notion")
        
        print(f"\n📊 NOTION UPDATE SUMMARY:")
        print(f"   Updated: {results['updated']}")
        print(f"   Not found in Notion: {results['not_found']}")
        print(f"   No attachments: {results['no_attachments']}")
        print(f"   Errors: {len(results['errors'])}")
        
        return results
    
    def find_notion_page_by_numero(self, numero: str) -> Optional[str]:
        """Find Notion page by deliberation number."""
        try:
            url = f"https://api.notion.com/v1/databases/{self.notion_db_id}/query"
            
            payload = {
                "filter": {
                    "property": "Numero",
                    "rich_text": {
                        "equals": numero
                    }
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.notion_token}",
                "Content-Type": "application/json", 
                "Notion-Version": "2022-06-28"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    return results[0]['id']
        except Exception as e:
            print(f"   💥 Error finding Notion page for {numero}: {str(e)}")
        
        return None
    
    def update_notion_url_decreto(self, page_id: str, url_decreto: str) -> bool:
        """Update url-decreto field in Notion page."""
        try:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            
            payload = {
                "properties": {
                    "URL_Decreto": {
                        "url": url_decreto
                    },
                    "Decreto_Trovato": {
                        "checkbox": True
                    },
                    "Data_Aggiornamento_Decreto": {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    }
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            response = requests.patch(url, json=payload, headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            print(f"   💥 Error updating Notion: {str(e)}")
            return False

def main():
    """Test the production decreto scraper."""
    
    scraper = ProductionDecretoScraper()
    
    print("🚀 PRODUCTION DECRETO SCRAPER TEST")
    print("=" * 50)
    
    # First test the search functionality
    if scraper.test_search_functionality():
        print("\n✅ Search functionality test passed")
        
        # Test with a specific year
        test_year = "2020"
        print(f"\n🎯 Testing full workflow for year {test_year}...")
        
        deliberazioni = scraper.search_year_with_full_workflow(test_year)
        
        if deliberazioni:
            print(f"✅ Found {len(deliberazioni)} deliberazioni for {test_year}")
            
            # Update Notion with found URLs
            notion_results = scraper.update_notion_with_reg_amm_urls(deliberazioni)
            
            # Save results
            output_file = f"production_decreto_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'year': test_year,
                    'deliberazioni': deliberazioni,
                    'notion_updates': notion_results
                }, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Results saved to: {output_file}")
        else:
            print(f"❌ No deliberazioni found for {test_year}")
    else:
        print("❌ Search functionality test failed")

if __name__ == "__main__":
    main()
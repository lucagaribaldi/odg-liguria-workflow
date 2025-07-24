#!/usr/bin/env python3
"""
Advanced decreto scraper che implementa il workflow completo:
1. Seleziona anno + tipo deliberazione
2. Imposta risultati per pagina al massimo
3. Attiva pulsante "Cerca"
4. Naviga tutte le pagine
5. Trova allegati REG_AMM_xxx
6. Aggiorna campo url-decreto in Notion
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

class AdvancedDecretoScraper:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
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
        except FileNotFoundError:
            print("⚠️ .env file not found")
    
    def get_initial_form_data(self) -> Tuple[Dict, BeautifulSoup]:
        """Get initial form data and page structure."""
        
        print("📄 Loading initial form...")
        response = self.session.get(self.base_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find main search form
        main_form = soup.find('form', action='index.php')
        if not main_form:
            raise Exception("Main search form not found")
        
        # Extract all form data
        form_data = {}
        
        # Hidden fields
        for hidden_input in main_form.find_all('input', type='hidden'):
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name:
                form_data[name] = value
        
        # Text inputs (set empty for now)
        for text_input in main_form.find_all('input', type='text'):
            name = text_input.get('name')
            if name:
                form_data[name] = ''
        
        # Radio buttons (find checked ones)
        for radio_input in main_form.find_all('input', type='radio'):
            name = radio_input.get('name')
            value = radio_input.get('value', '')
            if radio_input.has_attr('checked'):
                form_data[name] = value
        
        print("✅ Initial form data loaded")
        return form_data, soup
    
    def get_available_years_and_types(self, soup: BeautifulSoup) -> Tuple[List[str], Dict[str, str]]:
        """Extract available years and document types from form."""
        
        years = []
        doc_types = {}
        
        # Find year dropdown (select_1)
        year_select = soup.find('select', attrs={'name': 'select_1'})
        if year_select:
            for option in year_select.find_all('option'):
                value = option.get('value', '').strip()
                if value and value != '':
                    years.append(value)
        
        # Find document type dropdown (select_2) - might be empty initially
        type_select = soup.find('select', attrs={'name': 'select_2'})
        if type_select:
            for option in type_select.find_all('option'):
                value = option.get('value', '').strip()
                text = option.get_text(strip=True)
                if value and value != '':
                    doc_types[value] = text
        
        print(f"📅 Available years: {len(years)} ({years[-5:] if len(years) > 5 else years})")
        print(f"📋 Available doc types: {len(doc_types)}")
        
        return years, doc_types
    
    def search_deliberazioni_by_year(self, year: str, max_results_per_page: int = 50) -> List[Dict]:
        """
        Search for deliberazioni by year with complete workflow:
        1. Select year + deliberazione type
        2. Set max results per page
        3. Submit search 
        4. Navigate all pages
        5. Extract all deliberazioni with REG_AMM attachments
        """
        
        print(f"\n🔍 SEARCHING DELIBERAZIONI FOR YEAR {year}")
        print("=" * 50)
        
        # Get initial form
        form_data, soup = self.get_initial_form_data()
        
        # Configure search parameters
        form_data['select_1'] = year  # Anno
        
        # Try to find deliberazione type option
        # First attempt: look for deliberazione in existing options
        type_select = soup.find('select', attrs={'name': 'select_2'})
        deliberazione_value = None
        
        if type_select:
            for option in type_select.find_all('option'):
                text = option.get_text(strip=True).lower()
                if 'delibera' in text:
                    deliberazione_value = option.get('value', '')
                    print(f"📋 Found deliberazione type: {deliberazione_value} = {option.get_text(strip=True)}")
                    break
        
        if deliberazione_value:
            form_data['select_2'] = deliberazione_value
        
        # Set maximum results per page
        # Look for results per page field
        for field_name in ['8877ea8e05085d5bf2a469b94f5c4ddf', 'results_per_page', 'per_page']:
            if field_name in form_data or any(field_name in str(inp.get('name', '')) for inp in soup.find_all('input')):
                form_data[field_name] = str(max_results_per_page)
                print(f"📊 Set results per page: {max_results_per_page}")
                break
        
        # Set search type to "any word" for broader results
        form_data['chkSearchType'] = '1'
        
        # Add keyword for deliberazioni
        form_data['unnamed_1'] = 'deliberazione'  # Keyword search
        
        print(f"🔧 Form configured:")
        print(f"   Year: {form_data.get('select_1')}")
        print(f"   Type: {form_data.get('select_2', 'Not specified')}")
        print(f"   Keyword: {form_data.get('unnamed_1')}")
        
        # Submit search
        all_deliberazioni = []
        page_num = 1
        
        while True:
            print(f"\n📄 Processing page {page_num}...")
            
            try:
                # Submit form (first page) or navigate to next page
                if page_num == 1:
                    response = self.session.post(
                        f"{self.base_url}/index.php",
                        data=form_data,
                        timeout=20,
                        allow_redirects=True
                    )
                else:
                    # For subsequent pages, we need to find and follow pagination links
                    next_page_url = self.find_next_page_url(response.text, page_num)
                    if not next_page_url:
                        print("   No more pages found")
                        break
                    
                    response = self.session.get(next_page_url, timeout=20)
                
                response.raise_for_status()
                
                # Parse results from this page
                page_deliberazioni = self.extract_deliberazioni_from_page(response.text, year, page_num)
                
                if not page_deliberazioni:
                    print("   No deliberazioni found on this page")
                    break
                
                all_deliberazioni.extend(page_deliberazioni)
                print(f"   ✅ Found {len(page_deliberazioni)} deliberazioni on page {page_num}")
                
                # Check if there are more pages
                if not self.has_next_page(response.text):
                    print("   📄 Last page reached")
                    break
                
                page_num += 1
                time.sleep(2)  # Be respectful between pages
                
                # Safety limit
                if page_num > 20:
                    print("   ⚠️ Page limit reached (20 pages)")
                    break
                    
            except Exception as e:
                print(f"   💥 Error on page {page_num}: {str(e)}")
                break
        
        print(f"\n🎯 SEARCH COMPLETED")
        print(f"Total deliberazioni found: {len(all_deliberazioni)}")
        
        return all_deliberazioni
    
    def find_next_page_url(self, html_content: str, current_page: int) -> Optional[str]:
        """Find URL for next page in pagination."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for pagination links
        pagination_patterns = [
            f"page={current_page + 1}",
            f"p={current_page + 1}",
            f"start={current_page * 50}",  # Assuming 50 results per page
            "next",
            "successiva",
            "avanti"
        ]
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            
            # Check if this looks like a next page link
            for pattern in pagination_patterns:
                if pattern.lower() in href.lower() or pattern.lower() in link_text:
                    # Convert relative URL to absolute
                    if href.startswith('/'):
                        return self.base_url + href
                    elif href.startswith('http'):
                        return href
                    else:
                        return urljoin(self.base_url, href)
        
        return None
    
    def has_next_page(self, html_content: str) -> bool:
        """Check if there are more pages available."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for indicators of more pages
        next_indicators = [
            "next", "successiva", "avanti", ">>", "›",
            "page", "pagina"
        ]
        
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link.get('href', '').lower()
            
            for indicator in next_indicators:
                if indicator in link_text or indicator in href:
                    return True
        
        return False
    
    def extract_deliberazioni_from_page(self, html_content: str, year: str, page_num: int) -> List[Dict]:
        """Extract deliberazioni from a results page."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        deliberazioni = []
        
        # Look for result containers
        result_containers = []
        
        # Common patterns for search results
        container_selectors = [
            'div[class*="result"]',
            'div[class*="item"]',
            'div[class*="documento"]',
            'tr',
            'li[class*="result"]',
            'article'
        ]
        
        for selector in container_selectors:
            containers = soup.select(selector)
            if containers:
                for container in containers:
                    text = container.get_text(strip=True)
                    # Filter for deliberazione-related content
                    if (len(text) > 50 and 
                        any(keyword in text.lower() for keyword in [
                            'dgr', 'delibera', 'deliberazione', 'n.', 'del 20'
                        ])):
                        result_containers.append(container)
        
        # If no structured containers, look for text patterns
        if not result_containers:
            # Look for DGR patterns in all text
            all_text = soup.get_text()
            dgr_matches = re.findall(r'DGR\s+n?\s*\.?\s*(\d+)[^\n]*', all_text, re.IGNORECASE)
            
            for match in dgr_matches:
                deliberazioni.append({
                    'numero': match,
                    'year': year,
                    'page': page_num,
                    'extraction_method': 'text_pattern',
                    'raw_text': f"DGR n. {match}",
                    'reg_amm_attachments': []
                })
        
        # Process each container
        for i, container in enumerate(result_containers):
            try:
                delib_info = self.parse_deliberazione_container(container, year, page_num, i+1)
                if delib_info:
                    deliberazioni.append(delib_info)
            except Exception as e:
                print(f"     ⚠️ Error parsing container {i+1}: {str(e)}")
        
        return deliberazioni
    
    def parse_deliberazione_container(self, container, year: str, page_num: int, container_num: int) -> Optional[Dict]:
        """Parse a single deliberazione container."""
        
        text = container.get_text(strip=True)
        
        # Extract DGR number
        numero_match = re.search(r'(?:DGR|delibera|n\.)\s*n?\s*\.?\s*(\d+)', text, re.IGNORECASE)
        if not numero_match:
            return None
        
        numero = numero_match.group(1)
        
        # Look for REG_AMM attachments
        reg_amm_attachments = []
        
        # Find all links in this container
        links = container.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Check if this is a REG_AMM attachment
            if re.search(r'REG_AMM_\w+', href, re.IGNORECASE) or re.search(r'REG_AMM_\w+', link_text, re.IGNORECASE):
                # Convert to absolute URL
                if href.startswith('/'):
                    full_url = self.base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(self.base_url, href)
                
                reg_amm_attachments.append({
                    'url': full_url,
                    'text': link_text,
                    'type': 'REG_AMM'
                })
                
                print(f"     📎 Found REG_AMM attachment: {link_text[:50]}...")
        
        # Also look for any PDF or document attachments
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Check for document patterns
            if (any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx']) or
                any(word in link_text.lower() for word in ['allegato', 'documento', 'scarica'])):
                
                if href.startswith('/'):
                    full_url = self.base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(self.base_url, href)
                
                # Only add if not already added as REG_AMM
                if not any(att['url'] == full_url for att in reg_amm_attachments):
                    reg_amm_attachments.append({
                        'url': full_url,
                        'text': link_text,
                        'type': 'document'
                    })
        
        # Extract other metadata
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
        date_found = date_match.group(1) if date_match else None
        
        return {
            'numero': numero,
            'year': year,
            'page': page_num,
            'container': container_num,
            'raw_text': text[:200],  # First 200 chars
            'date_found': date_found,
            'reg_amm_attachments': reg_amm_attachments,
            'total_attachments': len(reg_amm_attachments),
            'extraction_method': 'structured_parse'
        }
    
    def update_notion_with_decreto_urls(self, deliberazioni: List[Dict]) -> Dict:
        """Update Notion database with decreto URLs found."""
        
        if not self.notion_token:
            print("⚠️ Notion credentials not available")
            return {'updated': 0, 'errors': []}
        
        print(f"\n📝 UPDATING NOTION WITH DECRETO URLs")
        print("=" * 40)
        
        results = {
            'updated': 0,
            'errors': [],
            'not_found': 0,
            'no_attachments': 0
        }
        
        for delib in deliberazioni:
            numero = delib['numero']
            attachments = delib.get('reg_amm_attachments', [])
            
            if not attachments:
                results['no_attachments'] += 1
                continue
            
            # Find Notion page for this deliberation
            page_id = self.find_notion_page_by_numero(numero)
            
            if not page_id:
                results['not_found'] += 1
                print(f"   ⚠️ DGR {numero}: Notion page not found")
                continue
            
            # Use first REG_AMM attachment or first attachment
            primary_attachment = None
            for att in attachments:
                if att['type'] == 'REG_AMM':
                    primary_attachment = att
                    break
            
            if not primary_attachment and attachments:
                primary_attachment = attachments[0]
            
            if primary_attachment:
                success = self.update_notion_decreto_url(page_id, primary_attachment['url'])
                
                if success:
                    results['updated'] += 1
                    print(f"   ✅ DGR {numero}: URL updated")
                else:
                    results['errors'].append(f"DGR {numero}: Update failed")
                    print(f"   ❌ DGR {numero}: Update failed")
        
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
    
    def update_notion_decreto_url(self, page_id: str, decreto_url: str) -> bool:
        """Update decreto URL in Notion page."""
        
        try:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            
            payload = {
                "properties": {
                    "URL_Decreto": {
                        "url": decreto_url
                    },
                    "Decreto_Trovato": {
                        "checkbox": True
                    },
                    "Ultimo_Aggiornamento_Decreto": {
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
    
    def run_complete_decreto_search(self, years: List[str] = None) -> Dict:
        """Run complete decreto search for specified years."""
        
        if years is None:
            years = ["2023", "2022", "2021", "2020"]  # Default years to search
        
        print(f"🚀 STARTING COMPLETE DECRETO SEARCH")
        print(f"Years to search: {years}")
        print("=" * 60)
        
        all_results = {
            'timestamp': datetime.now().isoformat(),
            'years_searched': years,
            'total_deliberazioni': 0,
            'total_attachments': 0,
            'notion_updates': 0,
            'detailed_results': {}
        }
        
        for year in years:
            try:
                print(f"\n{'='*20} YEAR {year} {'='*20}")
                
                deliberazioni = self.search_deliberazioni_by_year(year)
                
                if deliberazioni:
                    # Update Notion with found URLs
                    notion_results = self.update_notion_with_decreto_urls(deliberazioni)
                    
                    # Count attachments
                    total_attachments = sum(len(d.get('reg_amm_attachments', [])) for d in deliberazioni)
                    
                    all_results['detailed_results'][year] = {
                        'deliberazioni_found': len(deliberazioni),
                        'attachments_found': total_attachments,
                        'notion_updated': notion_results['updated'],
                        'notion_errors': len(notion_results['errors']),
                        'deliberazioni': deliberazioni
                    }
                    
                    all_results['total_deliberazioni'] += len(deliberazioni)
                    all_results['total_attachments'] += total_attachments
                    all_results['notion_updates'] += notion_results['updated']
                    
                    print(f"✅ Year {year} completed: {len(deliberazioni)} deliberazioni, {total_attachments} attachments")
                else:
                    print(f"❌ Year {year}: No deliberazioni found")
                    all_results['detailed_results'][year] = {
                        'deliberazioni_found': 0,
                        'attachments_found': 0,
                        'notion_updated': 0,
                        'notion_errors': 0,
                        'deliberazioni': []
                    }
                
                time.sleep(5)  # Pause between years
                
            except Exception as e:
                print(f"💥 Error processing year {year}: {str(e)}")
                all_results['detailed_results'][year] = {
                    'error': str(e),
                    'deliberazioni_found': 0,
                    'attachments_found': 0,
                    'notion_updated': 0
                }
        
        # Save results
        output_file = f"advanced_decreto_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎯 COMPLETE SEARCH FINISHED")
        print(f"📊 FINAL SUMMARY:")
        print(f"   Total deliberazioni found: {all_results['total_deliberazioni']}")
        print(f"   Total attachments found: {all_results['total_attachments']}")
        print(f"   Notion pages updated: {all_results['notion_updates']}")
        print(f"   Results saved to: {output_file}")
        
        return all_results

def main():
    """Run the advanced decreto scraper."""
    
    scraper = AdvancedDecretoScraper()
    
    # Test with recent years first
    test_years = ["2023", "2022"]
    
    results = scraper.run_complete_decreto_search(test_years)
    
    print("\n🎉 Advanced decreto scraping completed!")
    print("Check the JSON output file for detailed results.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Final working decreto scraper che implementa il workflow richiesto
utilizzando l'analisi del form esistente e metodi funzionanti.
"""

import json
import requests
import urllib3
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import Dict, List, Optional
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FinalWorkingDecretoScraper:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
            pass
    
    def get_working_search_strategy(self, year: str, deliberation_numbers: List[str]) -> List[Dict]:
        """
        Use the working search strategy we know functions:
        Search for specific DGR numbers we need to verify.
        """
        
        print(f"🔍 SEARCHING FOR {len(deliberation_numbers)} DELIBERATIONS IN {year}")
        print("=" * 60)
        
        found_deliberazioni = []
        
        for numero in deliberation_numbers:
            print(f"\n📋 Searching for DGR {numero}...")
            
            try:
                # Use the working search approach with the form
                hidden_fields = self.get_form_tokens()
                
                # Multiple search strategies for each number
                search_terms = [
                    f"DGR {numero}",
                    f"delibera {numero}",
                    f"numero {numero}",
                    numero
                ]
                
                for search_term in search_terms:
                    print(f"   🔍 Trying: '{search_term}'")
                    
                    form_data = {
                        'select_1': year,  # Year
                        'unnamed_1': search_term,  # Keyword
                        'chkSearchType': '2',  # Exact phrase
                        **hidden_fields
                    }
                    
                    try:
                        response = self.session.post(
                            f"{self.base_url}/index.php",
                            data=form_data,
                            timeout=15
                        )
                        
                        if response.status_code == 200:
                            # Look for REG_AMM attachments in response
                            reg_amm_urls = self.extract_reg_amm_from_response(response.text, numero)
                            
                            if reg_amm_urls:
                                found_deliberazioni.append({
                                    'numero': numero,
                                    'year': year,
                                    'search_term': search_term,
                                    'reg_amm_urls': reg_amm_urls,
                                    'found_at': datetime.now().isoformat()
                                })
                                
                                print(f"   ✅ Found {len(reg_amm_urls)} REG_AMM attachments!")
                                break  # Found it, no need to try other terms
                            else:
                                print(f"   ❌ No REG_AMM attachments found")
                        else:
                            print(f"   ⚠️ HTTP {response.status_code}")
                            
                    except Exception as e:
                        print(f"   💥 Search error: {str(e)}")
                    
                    time.sleep(1)  # Be respectful
                
                if not any(d['numero'] == numero for d in found_deliberazioni):
                    print(f"   📭 DGR {numero} not found with any search term")
                
            except Exception as e:
                print(f"   💥 Error searching DGR {numero}: {str(e)}")
            
            time.sleep(2)  # Pause between deliberations
        
        return found_deliberazioni
    
    def get_form_tokens(self):
        """Get form tokens from homepage."""
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
    
    def extract_reg_amm_from_response(self, html_content: str, numero: str) -> List[Dict]:
        """Extract REG_AMM attachment URLs from search response."""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        reg_amm_urls = []
        
        # Look for links that contain REG_AMM pattern
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if this is a REG_AMM link
            is_reg_amm = (
                'REG_AMM' in href.upper() or
                'REG_AMM' in text.upper() or
                (numero in href and any(ext in href.lower() for ext in ['.pdf', '.doc'])) or
                (numero in text and any(word in text.lower() for word in ['allegat', 'scarica', 'documento']))
            )
            
            if is_reg_amm:
                # Make URL absolute  
                if href.startswith('/'):
                    full_url = self.base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"{self.base_url}/{href}"
                
                reg_amm_urls.append({
                    'url': full_url,
                    'text': text,
                    'is_reg_amm': 'REG_AMM' in (href + text).upper()
                })
        
        return reg_amm_urls
    
    def load_notion_deliberations(self) -> List[Dict]:
        """Load deliberations from our Notion backup to get numbers to search for."""
        try:
            with open('data/backups/workflow_backup_20250718_152226.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            all_deliberations = []
            for result in data.get('results', []):
                deliberations = result.get('deliberations', [])
                all_deliberations.extend(deliberations)
            
            return all_deliberations
        except FileNotFoundError:
            print("⚠️ Notion backup not found")
            return []
    
    def update_notion_with_reg_amm_urls(self, found_deliberazioni: List[Dict]) -> Dict:
        """Update Notion database with found REG_AMM URLs."""
        
        if not self.notion_token:
            print("⚠️ Notion credentials not available")
            return {'updated': 0, 'errors': []}
        
        print(f"\n📝 UPDATING NOTION WITH REG_AMM URLs")
        print("=" * 40)
        
        results = {'updated': 0, 'errors': [], 'not_found': 0}
        
        for delib in found_deliberazioni:
            numero = delib['numero']
            reg_amm_urls = delib.get('reg_amm_urls', [])
            
            if not reg_amm_urls:
                continue
            
            # Use first (and likely best) REG_AMM URL
            primary_url = reg_amm_urls[0]['url']
            
            # Find Notion page
            page_id = self.find_notion_page_by_numero(numero)
            
            if page_id:
                success = self.update_notion_url_decreto(page_id, primary_url)
                if success:
                    results['updated'] += 1
                    print(f"   ✅ DGR {numero}: URL_Decreto updated")
                else:
                    results['errors'].append(f"DGR {numero}")
                    print(f"   ❌ DGR {numero}: Update failed")
            else:
                results['not_found'] += 1
                print(f"   ⚠️ DGR {numero}: Not found in Notion")
        
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
            print(f"   💥 Error finding Notion page: {str(e)}")
        
        return None
    
    def update_notion_url_decreto(self, page_id: str, url_decreto: str) -> bool:
        """Update URL_Decreto field in Notion."""
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
                    "Data_Verifica_Decreto": {
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
    
    def run_targeted_decreto_search(self) -> Dict:
        """
        Run targeted decreto search for deliberations in our Notion database.
        This is the main function that implements the complete workflow.
        """
        
        print("🎯 TARGETED DECRETO SEARCH FOR NOTION DELIBERATIONS")
        print("=" * 65)
        
        # Load deliberations from Notion backup
        notion_deliberations = self.load_notion_deliberations()
        
        if not notion_deliberations:
            print("❌ No deliberations found in backup")
            return {'error': 'No deliberations to search'}
        
        print(f"📋 Loaded {len(notion_deliberations)} deliberations from Notion backup")
        
        # Group by year for efficient searching
        by_year = {}
        for delib in notion_deliberations:
            # Extract year from data_seduta
            data_seduta = delib.get('data_seduta', '')
            if data_seduta:
                try:
                    year = data_seduta.split('-')[0]
                    if year not in by_year:
                        by_year[year] = []
                    by_year[year].append(delib.get('numero', ''))
                except:
                    pass
        
        print(f"📅 Years to search: {list(by_year.keys())}")
        
        all_found = []
        search_results = {
            'timestamp': datetime.now().isoformat(),
            'total_searched': len(notion_deliberations),
            'years_processed': list(by_year.keys()),
            'found_with_reg_amm': 0,
            'notion_updated': 0,
            'detailed_results': {}
        }
        
        # Search each year
        for year, numeri in by_year.items():
            print(f"\n{'='*20} YEAR {year} {'='*20}")
            print(f"Searching for {len(numeri)} deliberations...")
            
            try:
                found_in_year = self.get_working_search_strategy(year, numeri)
                all_found.extend(found_in_year)
                
                search_results['detailed_results'][year] = {
                    'searched': len(numeri),
                    'found': len(found_in_year),
                    'deliberazioni': found_in_year
                }
                
                search_results['found_with_reg_amm'] += len(found_in_year)
                
                print(f"✅ Year {year}: Found {len(found_in_year)}/{len(numeri)} with REG_AMM attachments")
                
            except Exception as e:
                print(f"💥 Error processing year {year}: {str(e)}")
                search_results['detailed_results'][year] = {
                    'searched': len(numeri),
                    'found': 0,
                    'error': str(e)
                }
        
        # Update Notion with found URLs
        if all_found:
            notion_results = self.update_notion_with_reg_amm_urls(all_found)
            search_results['notion_updated'] = notion_results['updated']
        
        # Save results
        output_file = f"targeted_decreto_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(search_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎯 TARGETED SEARCH COMPLETED")
        print(f"📊 FINAL SUMMARY:")
        print(f"   Total searched: {search_results['total_searched']}")
        print(f"   Found with REG_AMM: {search_results['found_with_reg_amm']}")
        print(f"   Notion pages updated: {search_results['notion_updated']}")
        print(f"   Results saved: {output_file}")
        
        return search_results

def main():
    """Run the final working decreto scraper."""
    
    scraper = FinalWorkingDecretoScraper()
    
    print("🚀 FINAL WORKING DECRETO SCRAPER")
    print("This scraper searches for specific deliberations from our Notion database")
    print("and updates the URL_Decreto field with found REG_AMM attachments.")
    print()
    
    results = scraper.run_targeted_decreto_search()
    
    if 'error' not in results:
        print("\n🎉 Decreto scraping completed successfully!")
        
        if results.get('found_with_reg_amm', 0) > 0:
            print(f"Found {results['found_with_reg_amm']} deliberations with REG_AMM attachments")
            print(f"Updated {results['notion_updated']} Notion pages")
        else:
            print("No deliberations found with REG_AMM attachments")
            print("This is normal for recent deliberations that may not be published yet")
    else:
        print(f"❌ Error: {results['error']}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Sistema integrato che monitora le pubblicazioni decreto e aggiorna automaticamente
lo stato su Notion quando le deliberazioni vengono pubblicate.
"""

import json
import requests
import urllib3
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os
from typing import Dict, List, Optional

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DecretoNotionSync:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
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
                        
            if self.notion_token and self.notion_db_id:
                print("✅ Notion credentials loaded successfully")
            else:
                print("⚠️ Notion credentials not found in .env file")
                
        except FileNotFoundError:
            print("⚠️ .env file not found - Notion sync disabled")
    
    def get_notion_headers(self):
        """Get headers for Notion API requests."""
        return {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def find_notion_page_by_numero(self, numero: str, seduta: str) -> Optional[str]:
        """Find Notion page ID by numero and seduta."""
        if not self.notion_token:
            return None
            
        try:
            url = f"https://api.notion.com/v1/databases/{self.notion_db_id}/query"
            
            # Search for page with matching numero
            payload = {
                "filter": {
                    "property": "Numero",
                    "rich_text": {
                        "equals": numero
                    }
                }
            }
            
            response = requests.post(url, json=payload, headers=self.get_notion_headers())
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Find exact match by seduta if multiple results
                for result in results:
                    page_seduta = ""
                    if 'properties' in result and 'Seduta' in result['properties']:
                        seduta_prop = result['properties']['Seduta']
                        if seduta_prop.get('rich_text'):
                            page_seduta = seduta_prop['rich_text'][0]['text']['content']
                    
                    if seduta in page_seduta or page_seduta == seduta:
                        return result['id']
                
                # If no exact seduta match, return first result
                if results:
                    return results[0]['id']
            
        except Exception as e:
            print(f"   💥 Error finding Notion page: {str(e)}")
        
        return None
    
    def update_notion_decreto_status(self, page_id: str, status: str, url: str = None) -> bool:
        """Update decreto publication status in Notion."""
        if not self.notion_token or not page_id:
            return False
            
        try:
            notion_url = f"https://api.notion.com/v1/pages/{page_id}"
            
            # Prepare update payload
            properties = {
                "Decreto_Pubblicato": {
                    "checkbox": status == "published"
                },
                "Decreto_Status": {
                    "select": {
                        "name": "Pubblicato" if status == "published" else "Non Pubblicato"
                    }
                },
                "Ultimo_Controllo_Decreto": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            }
            
            if url:
                properties["Decreto_URL"] = {
                    "url": url
                }
            
            payload = {
                "properties": properties
            }
            
            response = requests.patch(notion_url, json=payload, headers=self.get_notion_headers())
            
            if response.status_code == 200:
                return True
            else:
                print(f"   ❌ Notion update failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   💥 Error updating Notion: {str(e)}")
        
        return False
    
    def ensure_notion_decreto_properties(self):
        """Ensure Notion database has required decreto properties."""
        if not self.notion_token:
            print("⚠️ Skipping Notion property setup - no credentials")
            return False
            
        try:
            url = f"https://api.notion.com/v1/databases/{self.notion_db_id}"
            
            # Get current database schema
            response = requests.get(url, headers=self.get_notion_headers())
            
            if response.status_code != 200:
                print(f"❌ Cannot access Notion database: {response.status_code}")
                return False
            
            db_data = response.json()
            existing_properties = db_data.get('properties', {})
            
            # Define required properties for decreto tracking
            required_properties = {
                "Decreto_Pubblicato": {
                    "checkbox": {}
                },
                "Decreto_Status": {
                    "select": {
                        "options": [
                            {"name": "Non Controllato", "color": "gray"},
                            {"name": "Non Pubblicato", "color": "yellow"},
                            {"name": "Pubblicato", "color": "green"}
                        ]
                    }
                },
                "Decreto_URL": {
                    "url": {}
                },
                "Ultimo_Controllo_Decreto": {
                    "date": {}
                }
            }
            
            # Check which properties need to be added
            properties_to_add = {}
            for prop_name, prop_config in required_properties.items():
                if prop_name not in existing_properties:
                    properties_to_add[prop_name] = prop_config
                    print(f"📝 Will add property: {prop_name}")
            
            # Add missing properties
            if properties_to_add:
                update_payload = {
                    "properties": properties_to_add
                }
                
                response = requests.patch(url, json=update_payload, headers=self.get_notion_headers())
                
                if response.status_code == 200:
                    print(f"✅ Added {len(properties_to_add)} properties to Notion database")
                    return True
                else:
                    print(f"❌ Failed to update Notion database: {response.status_code}")
                    return False
            else:
                print("✅ All required decreto properties already exist in Notion")
                return True
                
        except Exception as e:
            print(f"💥 Error setting up Notion properties: {str(e)}")
            return False
    
    def search_for_deliberation(self, numero: str) -> Optional[Dict]:
        """Search for a specific deliberation on decreto website."""
        try:
            # Get form tokens
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
            
            # Multiple search strategies
            search_strategies = [
                {
                    'term': f"DGR {numero}",
                    'search_type': '2',  # Exact phrase
                    'description': f'Exact "DGR {numero}"'
                },
                {
                    'term': f"delibera {numero}",
                    'search_type': '2',  # Exact phrase
                    'description': f'Exact "delibera {numero}"'
                },
                {
                    'term': f"numero {numero}",
                    'search_type': '1',  # Any word
                    'description': f'Any word "numero {numero}"'
                }
            ]
            
            for strategy in search_strategies:
                form_data = {
                    'unnamed_1': strategy['term'],
                    'chkSearchType': strategy['search_type'],
                    **hidden_fields
                }
                
                response = self.session.post(
                    f"{self.base_url}/index.php",
                    data=form_data,
                    timeout=15
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Enhanced detection of published documents
                    if self.is_documento_published(soup, numero):
                        return {
                            'found': True,
                            'url': response.url,
                            'search_strategy': strategy['description'],
                            'confidence': 'high',
                            'detection_method': 'content_analysis'
                        }
                
                time.sleep(1)  # Respectful delay between strategies
            
        except Exception as e:
            print(f"   💥 Search error: {str(e)}")
        
        return None
    
    def is_documento_published(self, soup: BeautifulSoup, numero: str) -> bool:
        """Enhanced detection to determine if a document is actually published."""
        
        page_text = soup.get_text().lower()
        
        # Strong positive indicators (high confidence)
        strong_indicators = [
            f"dgr n. {numero}",
            f"dgr n.{numero}",
            f"delibera n. {numero}",
            f"decreto n. {numero}",
            f"n. {numero} del 2025"
        ]
        
        for indicator in strong_indicators:
            if indicator in page_text:
                print(f"   🎯 Strong match found: '{indicator}'")
                return True
        
        # Look for document links with decreto patterns
        links = soup.find_all('a', href=True)
        decreto_links = []
        
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            # Check if link points to actual document
            if (href and 
                any(pattern in href for pattern in ['.pdf', 'documento', 'decreto', 'dgr']) and
                numero in text):
                decreto_links.append(link)
        
        if decreto_links:
            print(f"   📄 Found {len(decreto_links)} document links containing numero {numero}")
            return True
        
        # Medium confidence indicators
        medium_indicators = [
            (f"dgr {numero}", 2),
            (f"delibera {numero}", 2),
            (f"numero {numero}", 1),
            ("pubblicat", 1),
            ("documento", 1)
        ]
        
        confidence_score = 0
        found_terms = []
        
        for term, points in medium_indicators:
            if term in page_text:
                confidence_score += points
                found_terms.append(term)
        
        if confidence_score >= 4:  # Threshold for medium confidence
            print(f"   ⚡ Medium confidence match (score: {confidence_score}): {found_terms}")
            return True
        
        return False
    
    def monitor_and_sync_publications(self, max_checks: int = 15) -> Dict:
        """Monitor decreto publications and sync status to Notion."""
        
        print("🔍 MONITORAGGIO DECRETO CON SYNC NOTION")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Ensure Notion database has required properties
        if self.notion_token:
            print("🔧 Setting up Notion database properties...")
            if not self.ensure_notion_decreto_properties():
                print("⚠️ Continuing without Notion property setup")
        
        # Load tracking data
        try:
            with open('decreto_status_tracking.json', 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
        except FileNotFoundError:
            print("❌ No tracking data found. Run decreto_final_integration.py first.")
            return {'error': 'No tracking data'}
        
        # Select deliberations to check (prioritize unchecked ones)
        to_check = []
        for key, data in tracking_data['decreto_status'].items():
            current_status = data['decreto_publication']['status']
            if current_status in ['not_checked', 'not_found'] and len(to_check) < max_checks:
                to_check.append((key, data))
        
        if not to_check:
            print("✅ All deliberations already checked recently")
            return {'message': 'All up to date'}
        
        print(f"📋 Checking {len(to_check)} deliberations...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'checked': 0,
            'found_published': 0,
            'notion_updated': 0,
            'errors': 0,
            'newly_published': []
        }
        
        for key, data in to_check:
            numero = data['deliberation_info']['numero']
            oggetto = data['deliberation_info']['oggetto'][:50]
            seduta = data['deliberation_info'].get('data_seduta', '')
            
            print(f"\n🔍 Checking DGR {numero}: {oggetto}...")
            results['checked'] += 1
            
            # Search for this deliberation
            search_result = self.search_for_deliberation(numero)
            
            # Update tracking data
            data['decreto_publication']['last_check'] = datetime.now().isoformat()
            
            if search_result and search_result.get('found'):
                print(f"   ✅ PUBBLICATO! DGR {numero}")
                print(f"      Strategy: {search_result.get('search_strategy')}")
                print(f"      URL: {search_result.get('url')}")
                
                # Update local tracking
                data['decreto_publication']['status'] = 'found'
                data['decreto_publication']['publication_url'] = search_result.get('url')
                data['decreto_publication']['verification_notes'] = f"Found via {search_result.get('search_strategy')}"
                
                results['found_published'] += 1
                results['newly_published'].append({
                    'numero': numero,
                    'oggetto': oggetto,
                    'url': search_result.get('url'),
                    'seduta': seduta
                })
                
                # Update Notion if credentials available
                if self.notion_token:
                    print(f"   📝 Updating Notion...")
                    
                    # Find Notion page
                    page_id = self.find_notion_page_by_numero(numero, seduta)
                    
                    if page_id:
                        success = self.update_notion_decreto_status(
                            page_id, 
                            "published", 
                            search_result.get('url')
                        )
                        
                        if success:
                            print(f"   ✅ Notion updated successfully")
                            results['notion_updated'] += 1
                        else:
                            print(f"   ❌ Failed to update Notion")
                            results['errors'] += 1
                    else:
                        print(f"   ⚠️ Notion page not found for DGR {numero}")
                        results['errors'] += 1
                else:
                    print(f"   ⚠️ Notion sync disabled - no credentials")
                
            else:
                print(f"   ❌ Not yet published")
                data['decreto_publication']['status'] = 'not_found'
            
            time.sleep(2)  # Respectful delay
        
        # Save updated tracking data
        tracking_data['last_updated'] = datetime.now().isoformat()
        with open('decreto_status_tracking.json', 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        
        # Generate summary report
        self.generate_sync_report(results)
        
        return results
    
    def generate_sync_report(self, results: Dict):
        """Generate comprehensive sync report."""
        
        print(f"\n🎯 DECRETO MONITORING & NOTION SYNC REPORT")
        print("=" * 55)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Deliberations checked: {results['checked']}")
        print(f"Found published: {results['found_published']}")
        print(f"Notion pages updated: {results['notion_updated']}")
        print(f"Errors: {results['errors']}")
        
        if results['newly_published']:
            print(f"\n🎉 NEWLY PUBLISHED DELIBERATIONS:")
            for pub in results['newly_published']:
                print(f"   • DGR {pub['numero']}: {pub['oggetto']}")
                print(f"     Date: {pub['seduta']}")
                print(f"     URL: {pub['url']}")
        
        # Save detailed report
        report_file = f"decreto_sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved: {report_file}")
        
        if results['found_published'] > 0:
            print(f"\n🚀 NEXT STEPS:")
            print(f"   • Check Notion database for updated decreto status")
            print(f"   • Review newly published deliberations")
            print(f"   • Set up notifications for future publications")

def main():
    """Execute decreto monitoring with Notion sync."""
    
    sync_system = DecretoNotionSync()
    
    print("🚀 Starting integrated decreto monitoring and Notion sync...")
    
    # Run monitoring and sync
    results = sync_system.monitor_and_sync_publications(max_checks=15)
    
    if 'error' not in results:
        print(f"\n✅ MONITORING COMPLETED SUCCESSFULLY")
        
        if results.get('found_published', 0) > 0:
            print(f"🎉 {results['found_published']} deliberations found published!")
            print(f"📝 {results['notion_updated']} Notion pages updated!")
        else:
            print("📭 No new publications found this time")
    else:
        print(f"❌ Error: {results['error']}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Production decreto checker for ODG Liguria workflow.
This script can be run periodically to check for newly published deliberations.
"""

import json
import requests
import urllib3
from bs4 import BeautifulSoup
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ProductionDecretoChecker:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def check_decreto_publications(self, max_checks: int = 10):
        """Check for newly published deliberations."""
        
        print(f"🔍 CHECKING DECRETO PUBLICATIONS")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Load tracking data
        try:
            with open('decreto_status_tracking.json', 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
        except FileNotFoundError:
            print("❌ No tracking data found. Run decreto_final_integration.py first.")
            return
        
        # Check subset of deliberations that need checking
        to_check = []
        for key, data in tracking_data['decreto_status'].items():
            if (data['decreto_publication']['status'] in ['not_checked', 'not_found'] and 
                len(to_check) < max_checks):
                to_check.append((key, data))
        
        print(f"📋 Checking {len(to_check)} deliberations...")
        
        newly_found = []
        
        for key, data in to_check:
            numero = data['deliberation_info']['numero']
            oggetto = data['deliberation_info']['oggetto'][:50]
            
            print(f"\n🔍 Checking DGR {numero}: {oggetto}...")
            
            # Search for this deliberation
            found = self.search_for_deliberation(numero)
            
            # Update tracking data
            data['decreto_publication']['last_check'] = datetime.now().isoformat()
            
            if found:
                print(f"   ✅ FOUND! DGR {numero} is now published")
                data['decreto_publication']['status'] = 'found'
                data['decreto_publication']['publication_url'] = found.get('url')
                data['decreto_publication']['verification_notes'] = found.get('notes')
                newly_found.append(data['deliberation_info'])
            else:
                print(f"   ❌ Not yet published")
                data['decreto_publication']['status'] = 'not_found'
            
            time.sleep(2)  # Be respectful
        
        # Update tracking file
        tracking_data['last_updated'] = datetime.now().isoformat()
        with open('decreto_status_tracking.json', 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        
        # Generate report
        if newly_found:
            print(f"\n🎉 NEW PUBLICATIONS FOUND: {len(newly_found)}")
            for delib in newly_found:
                print(f"   • DGR {delib['numero']}: {delib['oggetto'][:60]}...")
            
            # Send notification if configured
            self.send_notification(newly_found)
        else:
            print(f"\n📭 No new publications found")
        
        print(f"\n✅ Check completed at {datetime.now().strftime('%H:%M:%S')}")
    
    def search_for_deliberation(self, numero: str) -> dict:
        """Search for a specific deliberation."""
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
            
            # Search for DGR + numero
            form_data = {
                'unnamed_1': f"DGR {numero}",
                'chkSearchType': '2',  # Exact phrase
                **hidden_fields
            }
            
            response = self.session.post(
                f"{self.base_url}/index.php",
                data=form_data,
                timeout=15
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text().lower()
                
                # Look for strong evidence of published documento
                evidence_score = 0
                if f"dgr {numero}" in page_text or f"n. {numero}" in page_text:
                    evidence_score += 3
                if "pubblicat" in page_text or "atti" in page_text:
                    evidence_score += 2
                if len(soup.find_all('a', href=True)) > 10:  # Many links = results page
                    evidence_score += 1
                
                if evidence_score >= 4:  # High confidence threshold
                    return {
                        'found': True,
                        'url': response.url,
                        'notes': f'Evidence score: {evidence_score}/6',
                        'search_term': f"DGR {numero}"
                    }
            
        except Exception as e:
            print(f"   💥 Search error: {str(e)}")
        
        return None
    
    def send_notification(self, newly_found: list):
        """Send notification about newly published deliberations."""
        # This would integrate with your preferred notification method
        # (email, Slack, Teams, etc.)
        print(f"📧 Notification would be sent for {len(newly_found)} new publications")
        
        # Example: Save notification log
        notification_log = {
            'timestamp': datetime.now().isoformat(),
            'type': 'new_publications',
            'count': len(newly_found),
            'deliberations': newly_found
        }
        
        with open('decreto_notifications.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(notification_log) + "\n")

if __name__ == "__main__":
    checker = ProductionDecretoChecker()
    checker.check_decreto_publications()

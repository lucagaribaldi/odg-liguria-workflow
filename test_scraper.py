#!/usr/bin/env python3
"""
Test script for DecretoScraper - Manual testing on a single deliberation.

This script tests the decreto scraper on a specific deliberation from session 3928
to verify if it can be found on the official website decretidigitali.regione.liguria.it.

Test Case:
- Seduta: 3928
- Numero: 1
- Oggetto: "Disposizioni di carattere fiscale e altre disposizioni di adeguamento normativo"
- Data seduta: 2025-07-03
- Proponente: BUCCI Marco
- Tipo atto: Disegno di legge di iniziativa della Giunta regionale
"""

import sys
import os
import logging
import json
from typing import Dict, Any
from datetime import datetime
import ssl
import urllib3

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from decreto_scraper import DecretoScraper

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class VerboseDecretoScraper(DecretoScraper):
    """Extended DecretoScraper with verbose output for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up more verbose logging
        self.logger.setLevel(logging.DEBUG)
        
        # Add console handler with detailed formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        self.logger.addHandler(console_handler)
        
    def _make_request(self, url: str, params: dict = None) -> Any:
        """Override to add verbose output about requests."""
        print(f"\n🔍 Making request to: {url}")
        if params:
            print(f"📋 Parameters: {params}")
        
        # Handle SSL issues gracefully
        try:
            # First try normal request
            response = super()._make_request(url, params)
            if response:
                print(f"✅ Request successful: {response.status_code}")
                print(f"📄 Response content length: {len(response.text)} chars")
                if hasattr(response, 'url'):
                    print(f"🔗 Final URL: {response.url}")
                return response
            else:
                print("❌ Request failed (returned None)")
                return None
                
        except Exception as e:
            print(f"❌ Request failed with error: {str(e)}")
            
            # Try with SSL verification disabled as fallback
            try:
                print("🔄 Retrying with SSL verification disabled...")
                self.session.verify = False
                response = super()._make_request(url, params)
                if response:
                    print(f"✅ Request successful with SSL disabled: {response.status_code}")
                    return response
                else:
                    print("❌ Request still failed even with SSL disabled")
                    return None
            except Exception as e2:
                print(f"❌ Final request attempt failed: {str(e2)}")
                return None


def test_single_deliberation():
    """Test the decreto scraper on a single deliberation from session 3928."""
    
    print("="*80)
    print("🧪 DECRETO SCRAPER TEST")
    print("="*80)
    print()
    
    # Test case data from backup file
    test_case = {
        "seduta": "3928",
        "numero": "1",
        "oggetto": "Disposizioni di carattere fiscale e altre disposizioni di adeguamento normativo",
        "data_seduta": "2025-07-03",
        "proponente": "BUCCI Marco",
        "tipo_atto": "Disegno di legge di iniziativa della Giunta regionale"
    }
    
    print("📋 TEST CASE DATA:")
    print("-" * 40)
    for key, value in test_case.items():
        print(f"{key:15}: {value}")
    print()
    
    # Initialize scraper with verbose output
    print("🚀 Initializing DecretoScraper...")
    print("-" * 40)
    
    try:
        scraper = VerboseDecretoScraper(
            base_url="https://decretidigitali.regione.liguria.it",
            rate_limit=2.0,  # Be more gentle with requests
            max_retries=3,
            timeout=30,
            verify_ssl=False  # Disable SSL verification due to certificate issues
        )
        
        print("🔧 Testing with updated scraper including working implementation...")
        print("✅ Scraper initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize scraper: {str(e)}")
        return False
    
    print()
    print("🔍 TESTING DECRETO VERIFICATION...")
    print("-" * 40)
    
    # Test the verification
    start_time = datetime.now()
    
    try:
        result = scraper.verify_decreto_publication(
            seduta=test_case["seduta"],
            numero=test_case["numero"],
            oggetto=test_case["oggetto"],
            data_seduta=test_case["data_seduta"]
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print()
        print("📊 VERIFICATION RESULTS:")
        print("-" * 40)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Found: {result.get('found', False)}")
        
        if result.get('found'):
            print("✅ DECRETO FOUND ON WEBSITE!")
            print(f"URL: {result.get('url', 'N/A')}")
            print(f"Publication Date: {result.get('data_pubblicazione', 'N/A')}")
            print(f"DGR Number: {result.get('dgr_numero', 'N/A')}")
            print(f"DGR Year: {result.get('dgr_anno', 'N/A')}")
            
            # Try to get additional details
            if result.get('url'):
                print()
                print("📄 GETTING ADDITIONAL DETAILS...")
                print("-" * 40)
                try:
                    details = scraper.get_decreto_details(result['url'])
                    if details:
                        print("Additional details:")
                        for key, value in details.items():
                            if value:
                                print(f"  {key}: {value}")
                    else:
                        print("No additional details retrieved")
                except Exception as e:
                    print(f"Error getting details: {str(e)}")
                    
        else:
            print("❌ DECRETO NOT FOUND ON WEBSITE")
            
        print()
        print("📋 FULL RESULT DATA:")
        print("-" * 40)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return result.get('found', False)
        
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Print more detailed error information
        import traceback
        print()
        print("🔍 DETAILED ERROR TRACEBACK:")
        print("-" * 40)
        traceback.print_exc()
        
        return False


def test_website_connectivity():
    """Test basic connectivity to the decreto website."""
    
    print("🌐 TESTING WEBSITE CONNECTIVITY...")
    print("-" * 40)
    
    import requests
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    try:
        # Test basic connectivity
        print(f"Testing connection to: {base_url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        
        print(f"✅ Connection successful: {response.status_code}")
        print(f"📄 Response length: {len(response.text)} chars")
        print(f"🔗 Final URL: {response.url}")
        
        # Check if we can access search endpoints
        search_endpoints = [
            "/ricerca",
            "/search", 
            "/decreti"
        ]
        
        print()
        print("🔍 Testing search endpoints...")
        
        for endpoint in search_endpoints:
            try:
                test_url = f"{base_url}{endpoint}"
                response = requests.get(test_url, headers=headers, timeout=10)
                print(f"  {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"  {endpoint}: ERROR - {str(e)}")
                
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        
        # Try with SSL verification disabled
        try:
            print("🔄 Retrying with SSL verification disabled...")
            response = requests.get(base_url, headers=headers, timeout=10, verify=False)
            print(f"✅ Connection successful with SSL disabled: {response.status_code}")
            return True
        except Exception as e2:
            print(f"❌ Connection still failed: {str(e2)}")
            return False


def main():
    """Main test function."""
    
    print("🧪 DECRETO SCRAPER MANUAL TEST")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Website connectivity
    connectivity_ok = test_website_connectivity()
    print()
    
    if not connectivity_ok:
        print("❌ Website connectivity test failed. Scraper test may not work properly.")
        print("This could be due to:")
        print("  - Network connectivity issues")
        print("  - SSL certificate problems")
        print("  - Website being temporarily unavailable")
        print("  - Firewall or proxy blocking the connection")
        print()
        
        response = input("Continue with scraper test anyway? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Test aborted.")
            return
        print()
    
    # Test 2: Decreto scraper functionality
    found = test_single_deliberation()
    
    print()
    print("=" * 80)
    print("🏁 TEST SUMMARY")
    print("=" * 80)
    print(f"Website connectivity: {'✅ OK' if connectivity_ok else '❌ FAILED'}")
    print(f"Decreto found: {'✅ YES' if found else '❌ NO'}")
    print()
    
    if not found:
        print("📝 POSSIBLE REASONS WHY DECRETO WAS NOT FOUND:")
        print("  - Decreto not yet published on the website")
        print("  - Different search parameters needed")
        print("  - Website structure changed")
        print("  - Decreto published under different number/name")
        print("  - Website temporarily unavailable")
        print("  - Search functionality not working as expected")
        print()
        print("💡 NEXT STEPS:")
        print("  1. Check the website manually to see if the decreto exists")
        print("  2. Review and update the scraper's search strategies")
        print("  3. Test with different deliberations")
        print("  4. Consider adjusting search parameters or patterns")
    else:
        print("✅ SUCCESS! The decreto was found on the website.")
        print("The scraper is working correctly for this test case.")
    
    print()
    print("Test completed.")


if __name__ == "__main__":
    main()
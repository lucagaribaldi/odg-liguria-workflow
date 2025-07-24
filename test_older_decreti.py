#!/usr/bin/env python3
"""
Test search with older/historical decree terms to see if the site has any content
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_historical_search():
    """Test search with historical terms."""
    
    print("🕰️  TESTING HISTORICAL DECRETO SEARCH")
    print("=" * 50)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Create session
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    # Test with historical terms and common decreto patterns
    historical_terms = [
        "2024",  # Last year
        "2023",  # Year before
        "DGR",   # Decreto Giunta Regionale
        "dgr 2024",
        "delibera 2024", 
        "decreto 2024",
        "giunta regionale",
        "numero 1",  # Very common numero
        "numero 100",
        "deliberazione giunta",
        "regione liguria"
    ]
    
    found_any = False
    
    for term in historical_terms:
        print(f"\n🔍 Searching: '{term}'")
        
        try:
            search_url = f"{base_url}/index.php"
            params = {
                'option': 'com_search',
                'searchword': term
            }
            
            response = session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # More thorough analysis of the response
            page_text = soup.get_text()
            
            # Look for actual document titles or decreto numbers
            potential_results = []
            
            # Find all text that might be results
            for element in soup.find_all(text=True):
                text = element.strip()
                if text and len(text) > 20:
                    # Look for patterns that suggest decreto content
                    if any(pattern in text.lower() for pattern in [
                        'n.', 'numero', 'del ', 'dgr', 'delibera', 'decreto',
                        'giunta', 'regionale', 'liguria'
                    ]):
                        potential_results.append(text[:100])
            
            if potential_results:
                print(f"  ✅ Potential content found:")
                for result in potential_results[:3]:
                    if result.strip():
                        print(f"    - {result}")
                found_any = True
            
            # Look for structured results or links
            results_found = False
            for link in soup.find_all('a', href=True):
                link_text = link.get_text(strip=True)
                href = link.get('href', '')
                
                if link_text and len(link_text) > 15:
                    # Check if this looks like a decreto result
                    if any(indicator in link_text.lower() for indicator in [
                        'dgr', 'delibera', 'decreto', 'n.', 'del 20'
                    ]) and 'home' not in href.lower():
                        print(f"  📄 Document link: {link_text}")
                        print(f"      URL: {href}")
                        results_found = True
                        found_any = True
            
            if not potential_results and not results_found:
                print(f"  ❌ No relevant content found")
            
        except Exception as e:
            print(f"  💥 Error: {str(e)}")
        
        time.sleep(0.8)  # Be respectful
    
    if not found_any:
        print(f"\n⚠️  NO DECRETO CONTENT FOUND")
        print("This suggests that either:")
        print("1. The website doesn't contain decreto/delibera documents")
        print("2. The search functionality isn't working properly")
        print("3. Documents are stored in a different format/location")
        print("4. Access might be restricted")
    else:
        print(f"\n✅ Some content was found - the search system appears to work")
    
    # Try direct URL patterns that might exist
    print(f"\n🔗 Testing direct URL patterns...")
    
    url_patterns = [
        "/documenti",
        "/decreti", 
        "/atti",
        "/delibere",
        "/dgr",
        "/archivio",
        "/search",
        "/ricerca"
    ]
    
    for pattern in url_patterns:
        try:
            url = base_url + pattern
            response = session.head(url, timeout=5)
            
            if response.status_code == 200:
                print(f"  ✅ {pattern} - accessible")
                
                # Try to get content to see what's there
                content_response = session.get(url, timeout=5)
                if content_response.status_code == 200:
                    content_soup = BeautifulSoup(content_response.text, 'html.parser')
                    
                    # Look for any decreto-related content
                    links = content_soup.find_all('a', href=True)
                    decreto_links = [
                        link for link in links 
                        if any(word in link.get_text().lower() for word in ['dgr', 'delibera', 'decreto'])
                    ]
                    
                    if decreto_links:
                        print(f"      Found {len(decreto_links)} potential decreto links")
                        
            elif response.status_code == 404:
                print(f"  ❌ {pattern} - not found")
            else:
                print(f"  ⚠️  {pattern} - {response.status_code}")
                
        except Exception as e:
            print(f"  💥 {pattern} - error: {str(e)}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    test_historical_search()
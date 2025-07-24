#!/usr/bin/env python3
"""
Debug the search functionality to understand what's available
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def debug_search():
    """Debug search functionality."""
    
    print("🔍 DEBUG SEARCH FUNCTIONALITY")
    print("=" * 50)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Create session
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    # Test different search terms to see what's available
    test_searches = [
        "decreto",
        "delibera", 
        "2025",
        "giunta",
        "regionale",
        "deliberazione",
        "seduta"
    ]
    
    for search_term in test_searches:
        print(f"\n🔍 Searching for: '{search_term}'")
        
        try:
            search_url = f"{base_url}/index.php"
            params = {
                'option': 'com_search',
                'searchword': search_term
            }
            
            response = session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for any results
            page_text = soup.get_text()
            
            # Check for result indicators
            result_indicators = [
                'risultat', 'trovato', 'found', 'matches',
                'document', 'decreto', 'delibera'
            ]
            
            found_indicators = []
            for indicator in result_indicators:
                if indicator.lower() in page_text.lower():
                    found_indicators.append(indicator)
            
            print(f"  Indicators found: {found_indicators}")
            
            # Look for actual result links or content
            links = soup.find_all('a', href=True)
            result_links = []
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if text and len(text) > 10:  # Skip short navigation links
                    if any(word in text.lower() for word in ['delibera', 'decreto', 'atto']):
                        result_links.append((text[:80], href))
            
            if result_links:
                print(f"  Potential results found: {len(result_links)}")
                for i, (text, href) in enumerate(result_links[:3], 1):
                    print(f"    {i}. {text}")
                    print(f"       {href}")
            else:
                # Look for any meaningful content
                content_divs = soup.find_all(['div', 'section', 'article'], class_=True)
                for div in content_divs:
                    div_text = div.get_text(strip=True)
                    if len(div_text) > 50 and search_term.lower() in div_text.lower():
                        print(f"  Content match: {div_text[:100]}...")
                        break
                else:
                    print("  No clear results found")
            
            # Check if there's a "no results" message
            no_results_patterns = [
                'nessun risultato', 'no results', 'nessuna corrispondenza',
                'non trovato', 'not found', 'no matches'
            ]
            
            for pattern in no_results_patterns:
                if pattern.lower() in page_text.lower():
                    print(f"  ❌ No results message found: '{pattern}'")
                    break
            
        except Exception as e:
            print(f"  💥 Error: {str(e)}")
        
        time.sleep(1)  # Be respectful
    
    # Try to access the homepage search form directly
    print(f"\n📋 Analyzing homepage search form...")
    
    try:
        response = session.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main search form
        forms = soup.find_all('form')
        main_form = None
        
        for form in forms:
            if form.get('action') == 'index.php':
                main_form = form
                break
        
        if main_form:
            print("  Main search form found!")
            inputs = main_form.find_all(['input', 'select', 'textarea'])
            
            for inp in inputs:
                name = inp.get('name', 'N/A')
                input_type = inp.get('type', inp.name)
                value = inp.get('value', '')
                placeholder = inp.get('placeholder', '')
                
                print(f"    - {name} ({input_type}): value='{value}', placeholder='{placeholder}'")
        
        # Look for recent documents or any examples
        print(f"\n📄 Looking for any example documents...")
        
        all_links = soup.find_all('a', href=True)
        doc_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Look for anything that might be a document
            if text and any(word in text.lower() for word in [
                'delibera', 'decreto', 'atto', 'document', 'dgr', 'n.'
            ]):
                doc_links.append((text, href))
        
        if doc_links:
            print(f"  Found {len(doc_links)} potential document links:")
            for i, (text, href) in enumerate(doc_links[:5], 1):
                print(f"    {i}. {text[:60]}")
                print(f"       {href}")
        else:
            print("  No obvious document links found")
            
    except Exception as e:
        print(f"  💥 Error analyzing homepage: {str(e)}")

if __name__ == "__main__":
    debug_search()
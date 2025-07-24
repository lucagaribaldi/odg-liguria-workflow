#!/usr/bin/env python3
"""
Explore decreti.digitali website structure to find correct search endpoints
"""

import requests
import re
from bs4 import BeautifulSoup
import time
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def explore_website():
    """Explore the decreti digitali website structure."""
    
    print("🔍 ESPLORANDO decreti.digitali.regione.liguria.it")
    print("=" * 60)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    try:
        # Get homepage
        print("📄 Caricando homepage...")
        response = requests.get(base_url, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for search forms
        print("\n🔍 Cercando form di ricerca...")
        forms = soup.find_all('form')
        
        if forms:
            print(f"Trovati {len(forms)} form:")
            for i, form in enumerate(forms, 1):
                print(f"\nForm {i}:")
                print(f"  Action: {form.get('action', 'N/A')}")
                print(f"  Method: {form.get('method', 'GET')}")
                
                inputs = form.find_all(['input', 'select'])
                if inputs:
                    print(f"  Input fields:")
                    for inp in inputs:
                        name = inp.get('name', 'N/A')
                        input_type = inp.get('type', inp.name)
                        placeholder = inp.get('placeholder', '')
                        print(f"    - {name} ({input_type}): {placeholder}")
        
        # Look for links that might lead to search or decreto pages
        print("\n🔗 Cercando link di ricerca o decreti...")
        links = soup.find_all('a', href=True)
        
        search_links = []
        decreto_links = []
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if any(word in href.lower() for word in ['search', 'ricerca', 'cerca']):
                search_links.append((href, text))
            elif any(word in href.lower() for word in ['decreto', 'delibera', 'atto']):
                decreto_links.append((href, text))
        
        if search_links:
            print(f"\nLink di ricerca trovati:")
            for href, text in search_links[:5]:
                print(f"  - {text}: {href}")
        
        if decreto_links:
            print(f"\nLink di decreti trovati:")
            for href, text in decreto_links[:5]:
                print(f"  - {text}: {href}")
        
        # Look for navigation menu
        print("\n📋 Cercando menu di navigazione...")
        nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile('menu|nav', re.I))
        
        for nav in nav_elements[:3]:
            nav_links = nav.find_all('a', href=True)
            if nav_links:
                print(f"\nMenu trovato:")
                for link in nav_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if text and href:
                        print(f"  - {text}: {href}")
        
        # Try to find any JavaScript that might handle search
        print("\n💻 Cercando JavaScript per ricerca...")
        scripts = soup.find_all('script')
        for script in scripts:
            script_content = script.string or ''
            if any(word in script_content.lower() for word in ['search', 'ricerca', 'decreto']):
                print("Script rilevante trovato (frammento):")
                # Show first 200 chars
                print(f"  {script_content[:200]}...")
                break
        
        # Try some common paths
        print("\n🧪 Testando endpoint comuni...")
        common_paths = [
            '/ricerca',
            '/search',
            '/decreti',
            '/atti',
            '/delibere',
            '/cerca',
            '/index.php?option=com_search',
            '/component/search/',
            '/cerca.php',
            '/ricerca.php'
        ]
        
        for path in common_paths:
            try:
                url = base_url + path
                resp = requests.head(url, timeout=5, verify=False)
                if resp.status_code == 200:
                    print(f"  ✅ {path} - 200 OK")
                elif resp.status_code == 404:
                    print(f"  ❌ {path} - 404 Not Found")
                else:
                    print(f"  ⚠️  {path} - {resp.status_code}")
                time.sleep(0.5)  # Be respectful
            except:
                print(f"  💥 {path} - Error")
        
        # Look for sitemap or robots.txt
        print("\n📋 Verificando sitemap e robots.txt...")
        for path in ['/sitemap.xml', '/robots.txt']:
            try:
                resp = requests.get(base_url + path, timeout=5, verify=False)
                if resp.status_code == 200:
                    print(f"  ✅ {path} disponibile")
                    if path == '/sitemap.xml':
                        # Parse sitemap for useful URLs
                        sitemap_soup = BeautifulSoup(resp.text, 'xml')
                        urls = sitemap_soup.find_all('url')
                        print(f"    Trovati {len(urls)} URL in sitemap")
                        
                        # Look for search-related URLs
                        for url_elem in urls[:10]:
                            loc = url_elem.find('loc')
                            if loc:
                                url_text = loc.get_text()
                                if any(word in url_text.lower() for word in ['search', 'ricerca', 'decreto']):
                                    print(f"    - {url_text}")
                    
                    elif path == '/robots.txt':
                        print(f"    Content preview:")
                        print(f"    {resp.text[:300]}...")
            except:
                print(f"  ❌ {path} non disponibile")
        
    except Exception as e:
        print(f"💥 Errore durante l'esplorazione: {str(e)}")

def test_search_functionality():
    """Test different search approaches."""
    
    print("\n\n🧪 TESTANDO FUNZIONALITÀ DI RICERCA")
    print("=" * 50)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Try different search approaches
    search_tests = [
        {
            'name': 'GET ricerca con parametri',
            'url': f'{base_url}/index.php',
            'params': {'option': 'com_search', 'searchword': 'delibera'}
        },
        {
            'name': 'Joomla component search',
            'url': f'{base_url}/component/search/',
            'params': {'searchword': 'decreto'}
        },
        {
            'name': 'Direct search',
            'url': f'{base_url}/',
            'params': {'search': 'decreto', 'q': 'decreto'}
        }
    ]
    
    for test in search_tests:
        print(f"\n🔍 Test: {test['name']}")
        try:
            response = requests.get(test['url'], params=test.get('params', {}), timeout=10, verify=False)
            print(f"  Status: {response.status_code}")
            print(f"  URL finale: {response.url}")
            
            if response.status_code == 200:
                # Check if we got search results
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for common search result indicators
                result_indicators = [
                    'result', 'risultat', 'trovato', 'decreto', 'delibera', 
                    'search-result', 'risultati-ricerca'
                ]
                
                found_indicators = []
                for indicator in result_indicators:
                    if soup.find(text=re.compile(indicator, re.I)):
                        found_indicators.append(indicator)
                
                if found_indicators:
                    print(f"  ✅ Possibili risultati trovati: {found_indicators}")
                else:
                    print(f"  ❌ Nessun risultato evidente")
                    
                # Look for forms in the response
                forms = soup.find_all('form')
                if forms:
                    print(f"  📋 Form trovati: {len(forms)}")
            
        except Exception as e:
            print(f"  💥 Errore: {str(e)}")
        
        time.sleep(1)  # Be respectful

if __name__ == "__main__":
    explore_website()
    test_search_functionality()
#!/usr/bin/env python3
"""
Script per testare se è possibile cercare decreti di anni recenti bypassando il dropdown
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import logging
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_search_recent_years():
    """Testa la ricerca per anni recenti non presenti nel dropdown."""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Create session
    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0.0.0 Safari/537.36",
        "Referer": base_url,
        "Origin": base_url
    })
    
    # Test years to try
    test_years = ['2021', '2022', '2023', '2024', '2025']
    
    print("\n" + "="*60)
    print("TESTING SEARCH FOR RECENT YEARS")
    print("="*60)
    
    for year in test_years:
        try:
            logger.info(f"Testing search for year {year}")
            
            # Prepare form data for POST request
            form_data = {
                'txtAnno': year,  # Try setting year directly
                'chkSearchType': '0',  # All words
                'txtOggetto': '',  # Empty search to get all
                'maxResults': '10'
            }
            
            # Make POST request
            response = session.post(
                f"{base_url}/index.php",
                data=form_data,
                timeout=15
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for results
                result_indicators = [
                    soup.find_all('div', class_=['result', 'documento', 'item']),
                    soup.find_all('tr', class_=['risultato', 'item']),
                    soup.find_all('a', href=lambda x: x and 'decreto' in x.lower()),
                    soup.find_all(text=lambda x: x and year in str(x))
                ]
                
                results_found = any(indicator for indicator in result_indicators)
                year_mentions = len([text for text in soup.get_text().split() if year in text])
                
                print(f"Year {year}:")
                print(f"  - Response: {response.status_code}")
                print(f"  - Results found: {'YES' if results_found else 'NO'}")
                print(f"  - Year mentions: {year_mentions}")
                
                # Look for error messages
                error_messages = []
                error_selectors = [
                    'div.error', 'div.alert', 'span.error', 
                    'div.message', 'div.warning'
                ]
                
                for selector in error_selectors:
                    errors = soup.select(selector)
                    for error in errors:
                        error_text = error.get_text(strip=True)
                        if error_text and len(error_text) < 200:
                            error_messages.append(error_text)
                
                if error_messages:
                    print(f"  - Errors: {error_messages[:2]}")  # Show first 2 errors
                
                # Check if form was accepted
                form_indicators = soup.find_all('select', {'id': 'txtAnno'})
                if form_indicators:
                    selected_option = soup.find('option', selected=True)
                    if selected_option:
                        selected_year = selected_option.get('value', '')
                        print(f"  - Form selected year: {selected_year}")
                
            else:
                print(f"Year {year}: Request failed with status {response.status_code}")
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error testing year {year}: {e}")
            print(f"Year {year}: ERROR - {e}")
    
    print("\n" + "="*60)
    print("TESTING ALTERNATIVE SEARCH APPROACHES")
    print("="*60)
    
    # Test 1: Search by date range without year filter
    try:
        logger.info("Testing date range search for 2025")
        
        form_data = {
            'DataPubblicazione': '2025-01-01',  # Try 2025 date
            'chkSearchType': '0',
            'maxResults': '10'
        }
        
        response = session.post(f"{base_url}/index.php", data=form_data, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            date_mentions = len([text for text in soup.get_text().split() if '2025' in text])
            print(f"Date range search (2025-01-01): {date_mentions} mentions of 2025")
        
    except Exception as e:
        logger.error(f"Date range test failed: {e}")
    
    # Test 2: Check if there are other search endpoints
    try:
        logger.info("Looking for alternative search endpoints")
        
        response = session.get(base_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for other forms or search URLs
        forms = soup.find_all('form')
        links = soup.find_all('a', href=True)
        
        search_endpoints = []
        for form in forms:
            action = form.get('action', '')
            if action and action != 'index.php':
                search_endpoints.append(f"Form: {action}")
        
        for link in links:
            href = link.get('href', '')
            if any(keyword in href.lower() for keyword in ['search', 'cerca', 'ricerca', 'query']):
                search_endpoints.append(f"Link: {href}")
        
        if search_endpoints:
            print("Alternative endpoints found:")
            for endpoint in search_endpoints[:5]:  # Show first 5
                print(f"  - {endpoint}")
        else:
            print("No alternative search endpoints found")
            
    except Exception as e:
        logger.error(f"Alternative endpoints search failed: {e}")
    
    print("="*60)

if __name__ == "__main__":
    test_search_recent_years()
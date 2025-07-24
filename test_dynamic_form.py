#!/usr/bin/env python3
"""
Test dynamic form loading by submitting with different years to see available types
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_year_form_submission():
    """Test form submission with different years to see available data."""
    
    print("🧪 TESTING FORM SUBMISSION WITH DIFFERENT YEARS")
    print("=" * 60)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Create session
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded'
    })
    
    # Get the homepage first to get any necessary tokens/session data
    print("📄 Getting homepage for session setup...")
    homepage_response = session.get(base_url, timeout=10)
    homepage_soup = BeautifulSoup(homepage_response.text, 'html.parser')
    
    # Extract any hidden fields that might be needed
    main_form = homepage_soup.find('form', action='index.php')
    hidden_fields = {}
    
    if main_form:
        for hidden_input in main_form.find_all('input', type='hidden'):
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name:
                hidden_fields[name] = value
                print(f"Found hidden field: {name} = {value}")
    
    # Test years to try (from most recent backwards)
    test_years = ['2020', '2019', '2018', '2017', '2016']
    
    for year in test_years:
        print(f"\n🗓️  TESTING YEAR: {year}")
        print("-" * 30)
        
        try:
            # Prepare form data
            form_data = {
                'select_1': year,  # Anno field
                'chkSearchType': '1',  # Default radio selection
                **hidden_fields  # Include any hidden fields
            }
            
            # Submit form
            response = session.post(
                f"{base_url}/index.php",
                data=form_data,
                timeout=15,
                allow_redirects=True
            )
            
            response.raise_for_status()
            
            print(f"  Status: {response.status_code}")
            print(f"  Final URL: {response.url}")
            
            # Parse response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for results or document listings
            page_text = soup.get_text().lower()
            
            # Count potential results
            result_indicators = [
                'risultat', 'document', 'decreto', 'delibera', 
                'dgr', 'n.', 'del ', 'giunta'
            ]
            
            found_indicators = []
            for indicator in result_indicators:
                if indicator in page_text:
                    found_indicators.append(indicator)
            
            print(f"  Content indicators: {found_indicators}")
            
            # Look for actual document links or results
            document_links = []
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check if this looks like a document result
                if text and len(text) > 20:
                    if any(word in text.lower() for word in ['dgr', 'delibera', 'decreto', 'n.', 'del 20']):
                        document_links.append((text[:80], href))
            
            if document_links:
                print(f"  ✅ Found {len(document_links)} potential documents:")
                for i, (text, href) in enumerate(document_links[:3], 1):
                    print(f"    {i}. {text}")
                    print(f"       → {href}")
                
                # This year has data! Let's analyze it more
                if len(document_links) > 0:
                    print(f"\n🎯 YEAR {year} HAS DATA - ANALYZING STRUCTURE...")
                    analyze_results_page(soup, year)
                    break  # Found data, no need to test other years
            else:
                # Check for "no results" messages
                no_results_patterns = [
                    'nessun risultato', 'no results', 'nessuna corrispondenza',
                    'non trovato', 'not found', 'no matches'
                ]
                
                found_no_results = False
                for pattern in no_results_patterns:
                    if pattern in page_text:
                        print(f"  ❌ No results: '{pattern}' found")
                        found_no_results = True
                        break
                
                if not found_no_results:
                    print(f"  ⚠️  Unclear results - might need different approach")
            
        except Exception as e:
            print(f"  💥 Error: {str(e)}")
        
        time.sleep(1)  # Be respectful

def analyze_results_page(soup, year):
    """Analyze a results page that contains documents."""
    
    print(f"📊 ANALYZING RESULTS PAGE FOR {year}:")
    print("-" * 40)
    
    # Look for document listing structure
    document_containers = []
    
    # Common container patterns for document results
    container_selectors = [
        'div[class*="result"]',
        'div[class*="document"]', 
        'div[class*="item"]',
        'tr',  # Table rows
        'li',  # List items
        'article'
    ]
    
    for selector in container_selectors:
        containers = soup.select(selector)
        if containers:
            print(f"  Found {len(containers)} containers with selector: {selector}")
            
            # Analyze first few containers
            for i, container in enumerate(containers[:3], 1):
                container_text = container.get_text(strip=True)
                if len(container_text) > 50:  # Substantial content
                    # Look for document patterns
                    if any(pattern in container_text.lower() for pattern in [
                        'dgr', 'delibera', 'decreto', 'n.', 'del 20'
                    ]):
                        print(f"    Document {i}: {container_text[:100]}...")
                        
                        # Look for type information
                        if 'delibera' in container_text.lower():
                            print(f"      → Contains DELIBERAZIONE")
                        if 'relazione' in container_text.lower():
                            print(f"      → Contains RELAZIONE")
                        if 'dgr' in container_text.lower() or 'decreto' in container_text.lower():
                            print(f"      → Contains DECRETO/DGR")
            break
    
    # Look for pagination or total count
    total_indicators = soup.find_all(text=lambda text: text and 'risultat' in text.lower())
    for indicator in total_indicators:
        if any(char.isdigit() for char in indicator):
            print(f"  Total indicator: {indicator.strip()}")

if __name__ == "__main__":
    test_year_form_submission()
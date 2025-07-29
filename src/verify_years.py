#!/usr/bin/env python3
"""
Script per verificare gli anni realmente disponibili nel sito decretidigitali.regione.liguria.it
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import logging

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def verify_available_years():
    """Verifica gli anni realmente disponibili nel sito."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    url = "https://decretidigitali.regione.liguria.it"
    
    try:
        logger.info(f"Fetching page: {url}")
        
        # Create session with SSL disabled
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"
        })
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Page fetched successfully: {response.status_code}")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the year dropdown
        year_dropdown = soup.find('select', {'id': 'txtAnno'})
        
        if not year_dropdown:
            logger.error("Year dropdown (txtAnno) not found!")
            return None
        
        # Extract all year options
        options = year_dropdown.find_all('option')
        years = []
        
        for option in options:
            year_value = option.get('value', '').strip()
            year_text = option.get_text(strip=True)
            
            if year_value and year_value.isdigit():
                years.append({
                    'value': year_value,
                    'text': year_text,
                    'selected': option.has_attr('selected')
                })
        
        # Sort years
        years.sort(key=lambda x: int(x['value']))
        
        # Print results
        print("\n" + "="*60)
        print("YEARS AVAILABLE IN DECRETO WEBSITE")
        print("="*60)
        print(f"Total years found: {len(years)}")
        
        if years:
            print(f"Oldest year: {years[0]['value']}")
            print(f"Newest year: {years[-1]['value']}")
            print(f"Range: {years[0]['value']} - {years[-1]['value']}")
            
            # Check for recent years
            recent_years = [y for y in years if int(y['value']) >= 2017]
            print(f"Years from 2017 onwards: {len(recent_years)}")
            
            # Check for current year
            current_years = [y for y in years if int(y['value']) >= 2024]
            print(f"Years 2024+: {len(current_years)}")
            
            print("\nAll available years:")
            for i, year in enumerate(years):
                selected_marker = " [SELECTED]" if year['selected'] else ""
                print(f"  {i+1:2d}. {year['value']}{selected_marker}")
            
            # Detailed analysis
            print(f"\n" + "="*60)
            print("DETAILED ANALYSIS")
            print("="*60)
            
            year_values = [int(y['value']) for y in years]
            
            # Check continuity
            if year_values:
                missing_years = []
                for year in range(min(year_values), max(year_values) + 1):
                    if year not in year_values:
                        missing_years.append(year)
                
                if missing_years:
                    print(f"Missing years in range: {missing_years}")
                else:
                    print("No missing years in the range")
                
                # Check if 2017-2025 are available
                target_years = list(range(2017, 2026))  # 2017-2025
                available_target = [y for y in year_values if y in target_years]
                missing_target = [y for y in target_years if y not in year_values]
                
                print(f"Years 2017-2025 available: {available_target}")
                if missing_target:
                    print(f"Years 2017-2025 missing: {missing_target}")
                else:
                    print("All years 2017-2025 are available ✓")
        else:
            print("No years found!")
        
        print("="*60)
        
        return years
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    years = verify_available_years()
    if years:
        print(f"\nVerification completed successfully!")
    else:
        print(f"\nVerification failed!")
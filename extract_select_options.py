#!/usr/bin/env python3
"""
Extract all options from select dropdowns to understand available types and categories
"""

import requests
import urllib3
from bs4 import BeautifulSoup

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_select_options():
    """Extract all options from select dropdowns."""
    
    print("📋 EXTRACTING SELECT OPTIONS")
    print("=" * 50)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Create session
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        # Get homepage
        response = session.get(base_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main form
        main_form = soup.find('form', action='index.php')
        if not main_form:
            print("❌ Main form not found")
            return
        
        # Get all select elements
        selects = main_form.find_all('select')
        
        print(f"Found {len(selects)} select dropdowns:\n")
        
        for i, select in enumerate(selects, 1):
            name = select.get('name', f'select_{i}')
            
            # Try to find label
            label = "Unknown"
            select_id = select.get('id')
            if select_id:
                label_elem = soup.find('label', {'for': select_id})
                if label_elem:
                    label = label_elem.get_text(strip=True)
            
            if label == "Unknown":
                # Look for nearby text
                parent = select.parent
                if parent:
                    parent_text = parent.get_text(strip=True)
                    # Try to extract a meaningful label
                    lines = parent_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and 'select' not in line.lower() and len(line) < 50:
                            label = line
                            break
            
            print(f"🔽 SELECT {i}: {name}")
            print(f"   Label: {label}")
            print(f"   Options:")
            
            options = select.find_all('option')
            
            if not options:
                print("     (No options found)")
            else:
                for option in options:
                    value = option.get('value', '')
                    text = option.get_text(strip=True)
                    selected = "✓" if option.has_attr('selected') else " "
                    
                    # Highlight important options
                    highlight = ""
                    if any(keyword in text.lower() for keyword in [
                        'delibera', 'deliberazione', 'relazione', 'giunta', 
                        'decreto', 'dgr', 'atto'
                    ]):
                        highlight = " ⭐"
                    
                    print(f"     [{selected}] '{value}' → {text}{highlight}")
            
            print()  # Empty line between selects
        
        # Special focus on "Tipo Atto" dropdown
        print("🎯 FOCUSING ON 'TIPO ATTO' DROPDOWN:")
        print("-" * 40)
        
        tipo_atto_select = None
        for select in selects:
            # Look for the select that seems to be "Tipo Atto"
            parent_text = select.parent.get_text().lower() if select.parent else ""
            if 'tipo' in parent_text and 'atto' in parent_text:
                tipo_atto_select = select
                break
            
            # Also check by position (usually the 2nd select)
            if selects.index(select) == 1:  # 0-based index, so 1 = 2nd select
                tipo_atto_select = select
        
        if tipo_atto_select:
            print("✅ Tipo Atto dropdown found!")
            options = tipo_atto_select.find_all('option')
            
            delibera_options = []
            relazione_options = []
            all_options = []
            
            for option in options:
                value = option.get('value', '')
                text = option.get_text(strip=True)
                all_options.append((value, text))
                
                if any(word in text.lower() for word in ['delibera', 'deliberazione']):
                    delibera_options.append((value, text))
                elif any(word in text.lower() for word in ['relazione', 'giunta']):
                    relazione_options.append((value, text))
            
            print(f"\n📊 SUMMARY:")
            print(f"Total options: {len(all_options)}")
            print(f"Delibera options: {len(delibera_options)}")
            print(f"Relazione options: {len(relazione_options)}")
            
            if delibera_options:
                print(f"\n🏛️  DELIBERAZIONE OPTIONS:")
                for value, text in delibera_options:
                    print(f"   - '{value}' → {text}")
            
            if relazione_options:
                print(f"\n📄 RELAZIONE OPTIONS:")
                for value, text in relazione_options:
                    print(f"   - '{value}' → {text}")
            
            if not delibera_options and not relazione_options:
                print(f"\n⚠️  No Delibera or Relazione options found")
                print(f"All options:")
                for value, text in all_options:
                    print(f"   - '{value}' → {text}")
        
        else:
            print("❌ Could not identify Tipo Atto dropdown")
        
    except Exception as e:
        print(f"💥 Error: {str(e)}")

if __name__ == "__main__":
    extract_select_options()
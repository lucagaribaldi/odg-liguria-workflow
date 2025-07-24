#!/usr/bin/env python3
"""
Analyze the main search form structure to understand year and type filtering
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def analyze_form():
    """Analyze the main search form structure."""
    
    print("📋 ANALYZING MAIN SEARCH FORM STRUCTURE")
    print("=" * 60)
    
    base_url = "https://decretidigitali.regione.liguria.it"
    
    # Create session
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        # Get homepage with the main form
        print("📄 Loading homepage...")
        response = session.get(base_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main search form
        main_form = None
        forms = soup.find_all('form')
        
        for form in forms:
            if form.get('action') == 'index.php':
                main_form = form
                break
        
        if not main_form:
            print("❌ Main search form not found")
            return
        
        print("✅ Main search form found!")
        print(f"Action: {main_form.get('action')}")
        print(f"Method: {main_form.get('method')}")
        
        # Analyze all form elements
        print(f"\n📝 FORM ELEMENTS ANALYSIS:")
        print("-" * 40)
        
        form_data = {}
        
        # Text inputs
        text_inputs = main_form.find_all('input', type='text')
        print(f"\n📄 Text Inputs ({len(text_inputs)}):")
        for i, inp in enumerate(text_inputs, 1):
            name = inp.get('name', f'unnamed_{i}')
            placeholder = inp.get('placeholder', '')
            value = inp.get('value', '')
            label = find_label_for_input(inp, soup)
            
            print(f"  {i}. Name: {name}")
            print(f"     Label: {label}")
            print(f"     Placeholder: {placeholder}")
            print(f"     Default: {value}")
            
            form_data[name] = {
                'type': 'text',
                'label': label,
                'placeholder': placeholder,
                'default': value
            }
        
        # Date inputs
        date_inputs = main_form.find_all('input', type='date')
        print(f"\n📅 Date Inputs ({len(date_inputs)}):")
        for i, inp in enumerate(date_inputs, 1):
            name = inp.get('name', f'date_{i}')
            value = inp.get('value', '')
            label = find_label_for_input(inp, soup)
            
            print(f"  {i}. Name: {name}")
            print(f"     Label: {label}")
            print(f"     Default: {value}")
            
            form_data[name] = {
                'type': 'date',
                'label': label,
                'default': value
            }
        
        # Number inputs
        number_inputs = main_form.find_all('input', type='number')
        print(f"\n🔢 Number Inputs ({len(number_inputs)}):")
        for i, inp in enumerate(number_inputs, 1):
            name = inp.get('name', f'number_{i}')
            value = inp.get('value', '')
            label = find_label_for_input(inp, soup)
            
            print(f"  {i}. Name: {name}")
            print(f"     Label: {label}")
            print(f"     Default: {value}")
            
            form_data[name] = {
                'type': 'number',
                'label': label,
                'default': value
            }
        
        # Radio buttons
        radio_inputs = main_form.find_all('input', type='radio')
        if radio_inputs:
            print(f"\n🔘 Radio Buttons ({len(radio_inputs)}):")
            radio_groups = {}
            
            for inp in radio_inputs:
                name = inp.get('name', 'unnamed')
                value = inp.get('value', '')
                checked = inp.has_attr('checked')
                label = find_label_for_input(inp, soup)
                
                if name not in radio_groups:
                    radio_groups[name] = []
                
                radio_groups[name].append({
                    'value': value,
                    'label': label,
                    'checked': checked
                })
            
            for group_name, options in radio_groups.items():
                print(f"  Group: {group_name}")
                for opt in options:
                    check_mark = "✓" if opt['checked'] else " "
                    print(f"    [{check_mark}] {opt['value']}: {opt['label']}")
                
                form_data[group_name] = {
                    'type': 'radio',
                    'options': options
                }
        
        # Select dropdowns
        selects = main_form.find_all('select')
        print(f"\n📋 Select Dropdowns ({len(selects)}):")
        for i, select in enumerate(selects, 1):
            name = select.get('name', f'select_{i}')
            label = find_label_for_input(select, soup)
            
            print(f"  {i}. Name: {name}")
            print(f"     Label: {label}")
            
            options = []
            for option in select.find_all('option'):
                value = option.get('value', '')
                text = option.get_text(strip=True)
                selected = option.has_attr('selected')
                
                options.append({
                    'value': value,
                    'text': text,
                    'selected': selected
                })
                
                selected_mark = "✓" if selected else " "
                print(f"       [{selected_mark}] {value}: {text}")
            
            form_data[name] = {
                'type': 'select',
                'label': label,
                'options': options
            }
        
        # Buttons
        buttons = main_form.find_all(['input', 'button'], type=['submit', 'button'])
        print(f"\n🔘 Buttons ({len(buttons)}):")
        for i, btn in enumerate(buttons, 1):
            btn_type = btn.get('type', btn.name)
            value = btn.get('value', btn.get_text(strip=True))
            name = btn.get('name', f'button_{i}')
            
            print(f"  {i}. Type: {btn_type}, Name: {name}, Value: {value}")
        
        # Save form structure for reference
        form_structure = {
            'action': main_form.get('action'),
            'method': main_form.get('method'),
            'fields': form_data,
            'analysis_date': '2025-07-23'
        }
        
        with open('form_structure_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(form_structure, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Form structure saved to: form_structure_analysis.json")
        
        # Look for hidden fields that might be important
        hidden_inputs = main_form.find_all('input', type='hidden')
        if hidden_inputs:
            print(f"\n🔒 Hidden Fields ({len(hidden_inputs)}):")
            for inp in hidden_inputs:
                name = inp.get('name', 'unnamed')
                value = inp.get('value', '')
                print(f"  - {name}: {value}")
        
        return form_structure
        
    except Exception as e:
        print(f"💥 Error analyzing form: {str(e)}")
        return None

def find_label_for_input(element, soup):
    """Try to find a label for a form element."""
    
    # Method 1: Look for a label with 'for' attribute
    element_id = element.get('id')
    if element_id:
        label = soup.find('label', {'for': element_id})
        if label:
            return label.get_text(strip=True)
    
    # Method 2: Look for parent label
    parent_label = element.find_parent('label')
    if parent_label:
        return parent_label.get_text(strip=True)
    
    # Method 3: Look for nearby text (previous sibling, parent, etc.)
    for sibling in element.previous_siblings:
        if hasattr(sibling, 'get_text'):
            text = sibling.get_text(strip=True)
            if text and len(text) < 100:  # Reasonable label length
                return text
    
    # Method 4: Look in parent container
    parent = element.parent
    if parent:
        parent_text = parent.get_text(strip=True)
        # Remove the input's own text/value
        input_text = element.get('value', '') + element.get('placeholder', '')
        clean_text = parent_text.replace(input_text, '').strip()
        if clean_text and len(clean_text) < 100:
            return clean_text
    
    return "No label found"

if __name__ == "__main__":
    analyze_form()
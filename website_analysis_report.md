# Website Structure Analysis Report
## decretidigitali.regione.liguria.it

**Date:** 2025-07-18  
**Analysis Method:** Automated exploration script and manual HTML inspection

## Executive Summary

The exploration revealed that the decretidigitali.regione.liguria.it website is a **single-page application** built with what appears to be a **Joomla CMS** (based on the K2 component references and URL structure). The site does NOT use traditional REST endpoints but instead relies on:

1. **Main search form** posting to `index.php`
2. **JavaScript-driven functionality** for dynamic content loading
3. **AJAX calls** for fetching search results and populating dropdowns

## Key Findings

### 1. Search Functionality

**Main Search Form Structure:**
- **Action:** `index.php` (POST)
- **JavaScript Handler:** `startSearch(0)` function
- **Results Container:** `<div id="risultati">`

**Search Parameters Available:**
- `txtOggetto` - Keyword search (text input)
- `chkSearchType` - Search type (radio buttons):
  - `0` = "Tutte le parole" (All words)
  - `1` = "Almeno una parola" (At least one word) [default]
  - `2` = "Frase esatta" (Exact phrase)
- `txtAnno` - Year (dropdown, populated via JavaScript)
- `txtTipoAtto` - Document type (dropdown, populated via JavaScript)
- `txtNumero` - Registry number (text input)
- `txtSoggettoEmanante` - Issuing authority (text input)
- `DataSottoscrizione` - Signature date (date input)
- `DataPubblicazione` - Publication date (date input)
- `txtMateria` - Subject matter (dropdown, populated via JavaScript)
- `txtArgomento` - Topic (dropdown, populated via JavaScript)
- `txtOrderField` - Sort order (hidden, defaults to publication date)
- `maxResults` - Results per page (range slider, 5-50)

### 2. JavaScript Dependencies

**Critical JavaScript Functions:**
- `startSearchAnniCombo()` - Populates year dropdown
- `startSearchTipoAttoCombo()` - Populates document type dropdown
- `startSearchMaterieCombo()` - Populates subject matter dropdown
- `startSearch(0)` - Executes the search
- `resetFields()` - Clears the form

**JavaScript Files:**
- `/components/com_lddocs_iterg/js/functions.js` - Main application logic
- jQuery and jQuery UI for form interactions
- Various UIKit components for UI

### 3. Technology Stack

**CMS:** Joomla with K2 component
**Server:** Microsoft IIS/10.0 on ASP.NET
**Frontend:** UIKit CSS framework, jQuery
**Custom Component:** `com_lddocs_iterg` (appears to be a custom Joomla component)

### 4. Failed Endpoints

All traditional REST endpoints returned connection failures, confirming this is NOT a REST API:
- `/ricerca`, `/search`, `/cerca` ❌
- `/decreti`, `/delibere`, `/dgr`, `/dcr` ❌
- `/api`, `/api/search`, `/api/decreti` ❌
- `/documenti`, `/atti`, `/pubblicazioni` ❌

### 5. Working Endpoints

**Only successful endpoint:** `/` (root)
- Returns the main search page
- Contains the complete search interface
- All functionality is JavaScript-driven from this single page

## Technical Implementation Details

### Search Request Structure

The search works by:
1. User fills out the form on the main page
2. JavaScript `startSearch(0)` function is called
3. Form data is POSTed to `index.php`
4. Server returns HTML results
5. Results are inserted into the `<div id="risultati">` container

### Form Data Structure

Based on the HTML analysis, a typical search request would include:
```
POST /index.php
Content-Type: application/x-www-form-urlencoded

txtOggetto=<keyword>
chkSearchType=<0|1|2>
txtAnno=<year>
txtTipoAtto=<document_type>
txtNumero=<registry_number>
txtSoggettoEmanante=<issuing_authority>
DataSottoscrizione=<signature_date>
DataPubblicazione=<publication_date>
txtMateria=<subject_matter>
txtArgomento=<topic>
txtOrderField=ld:dataPubblicazioneRicercaWeb
maxResults=<5-50>
8877ea8e05085d5bf2a469b94f5c4ddf=<csrf_token>
```

### CSRF Protection

The form includes a CSRF token field:
- Field name: `8877ea8e05085d5bf2a469b94f5c4ddf`
- This token needs to be extracted from the main page and included in searches

## Recommendations for Scraping

### 1. Session Management
- Use `requests.Session()` to maintain cookies and session state
- Extract CSRF token from the main page before each search
- Maintain the same session throughout the scraping process

### 2. JavaScript Execution
- The dropdown population requires JavaScript execution
- Consider using Selenium WebDriver for full JavaScript support
- Alternative: Reverse-engineer the AJAX calls that populate dropdowns

### 3. Search Strategy
- Start with simple keyword searches using `txtOggetto`
- Use `chkSearchType=1` (at least one word) for broader results
- Implement pagination by analyzing the results structure
- Filter by year using `txtAnno` for targeted searches

### 4. Error Handling
- Monitor for rate limiting (no explicit indication found)
- Handle JavaScript errors gracefully
- Implement retry logic for failed requests

### 5. Data Extraction
- Results are returned as HTML in the `risultati` div
- Parse the HTML structure to extract decreto information
- Look for patterns in the result formatting

## Next Steps

1. **Analyze JavaScript files** to understand the exact AJAX endpoints
2. **Implement session-based scraper** with CSRF token handling
3. **Test search functionality** with various parameter combinations
4. **Map the results structure** to understand data formats
5. **Implement pagination logic** if results are paginated

## Sample Implementation Approach

```python
import requests
from bs4 import BeautifulSoup

class DecretiScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.csrf_token = None
    
    def get_csrf_token(self):
        response = self.session.get(self.base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': lambda x: x and len(x) == 32})
        if csrf_input:
            self.csrf_token = csrf_input['name']
        return self.csrf_token
    
    def search(self, keyword="", year="", document_type="", **kwargs):
        if not self.csrf_token:
            self.get_csrf_token()
        
        data = {
            'txtOggetto': keyword,
            'chkSearchType': '1',  # At least one word
            'txtAnno': year,
            'txtTipoAtto': document_type,
            'txtOrderField': 'ld:dataPubblicazioneRicercaWeb',
            'maxResults': '50',
            self.csrf_token: ''
        }
        
        response = self.session.post(f"{self.base_url}/index.php", data=data)
        return response.text
```

This analysis provides a solid foundation for implementing a working decreto scraper that properly handles the website's JavaScript-driven architecture.
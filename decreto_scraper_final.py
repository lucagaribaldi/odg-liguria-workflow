#!/usr/bin/env python3
"""
Final decreto scraper that searches by year and document type (Deliberazione/Relazioni di Giunta)
as per user instruction: "fare scraping su anno e tipologia, a partire da deliberazione e relazioni di giunta"
"""

import requests
import urllib3
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Optional
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DecretoScraperFinal:
    def __init__(self):
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
    def get_form_tokens(self):
        """Get necessary form tokens and hidden fields from homepage."""
        response = self.session.get(self.base_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        main_form = soup.find('form', action='index.php')
        
        hidden_fields = {}
        if main_form:
            for hidden_input in main_form.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    hidden_fields[name] = value
        
        return hidden_fields
    
    def search_by_year_and_keywords(self, year: str, keywords: List[str]) -> List[Dict]:
        """
        Search for documents by year and keywords using the form-based approach.
        
        Args:
            year: Year to search (e.g., "2020")
            keywords: Keywords to search for (e.g., ["deliberazione", "relazioni di giunta"])
        
        Returns:
            List of found documents
        """
        results = []
        
        # Get form tokens
        hidden_fields = self.get_form_tokens()
        
        for keyword in keywords:
            print(f"🔍 Searching {year} for: {keyword}")
            
            try:
                # Prepare form data combining year selection and keyword search
                form_data = {
                    'select_1': year,  # Anno field from form analysis
                    'unnamed_1': keyword,  # Parola chiave field
                    'chkSearchType': '1',  # "Almeno una parola" search type
                    **hidden_fields
                }
                
                # Submit search
                response = self.session.post(
                    f"{self.base_url}/index.php",
                    data=form_data,
                    timeout=15,
                    allow_redirects=True
                )
                
                response.raise_for_status()
                
                # Parse results
                soup = BeautifulSoup(response.text, 'html.parser')
                documents = self.extract_documents_from_results(soup, year, keyword)
                results.extend(documents)
                
                print(f"  Found {len(documents)} documents")
                
            except Exception as e:
                print(f"  Error searching {keyword}: {str(e)}")
            
            time.sleep(1)  # Be polite
        
        return results
    
    def extract_documents_from_results(self, soup: BeautifulSoup, year: str, search_term: str) -> List[Dict]:
        """Extract document information from search results."""
        documents = []
        
        # Look for various patterns that might contain document results
        potential_containers = []
        
        # Try different selectors for document containers
        for selector in ['div[class*="result"]', 'div[class*="item"]', 'tr', 'li', 'article', 'div']:
            containers = soup.select(selector)
            for container in containers:
                text = container.get_text(strip=True)
                
                # Check if this looks like a document result
                if (len(text) > 50 and 
                    any(indicator in text.lower() for indicator in [
                        'dgr', 'delibera', 'decreto', 'n.', 'del 20', 'numero'
                    ])):
                    potential_containers.append((container, text))
        
        # Process potential document containers
        for container, text in potential_containers:
            try:
                doc_info = self.parse_document_info(container, text, year, search_term)
                if doc_info:
                    documents.append(doc_info)
            except Exception as e:
                print(f"    Error parsing document: {str(e)}")
        
        # If no structured results found, look for any mention of documents in page text
        if not documents:
            page_text = soup.get_text()
            if any(term in page_text.lower() for term in ['dgr', 'delibera', 'decreto']):
                # Page contains document-related content but no structured results
                # This might indicate the documents exist but pagination or different structure
                documents.append({
                    'type': 'search_indication',
                    'year': year,
                    'search_term': search_term,
                    'indication': 'Document-related content found but no structured results',
                    'page_content_preview': page_text[:300]
                })
        
        return documents
    
    def parse_document_info(self, container, text: str, year: str, search_term: str) -> Optional[Dict]:
        """Parse document information from a container element."""
        
        # Look for document links
        links = container.find_all('a', href=True)
        
        doc_info = {
            'year': year,
            'search_term': search_term,
            'text': text[:200],  # First 200 chars
            'links': []
        }
        
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            if link_text and href:
                doc_info['links'].append({
                    'text': link_text,
                    'url': href if href.startswith('http') else self.base_url + href
                })
        
        # Try to extract document number/title
        if 'n.' in text.lower() or 'numero' in text.lower():
            doc_info['has_number'] = True
        
        if any(term in text.lower() for term in ['delibera', 'deliberazione']):
            doc_info['document_type'] = 'deliberazione'
        elif any(term in text.lower() for term in ['relazione', 'giunta']):
            doc_info['document_type'] = 'relazione_giunta'
        elif any(term in text.lower() for term in ['dgr', 'decreto']):
            doc_info['document_type'] = 'decreto'
        
        return doc_info if doc_info['links'] or doc_info.get('has_number') else None
    
    def search_deliberations_for_years(self, years: List[str]) -> Dict[str, List[Dict]]:
        """
        Search for deliberazioni and relazioni di giunta for multiple years.
        This implements the user's request: "fare scraping su anno e tipologia"
        """
        print("🏛️  DECRETO SCRAPER - SEARCHING BY YEAR AND TYPE")
        print("=" * 60)
        print("Searching for: Deliberazione + Relazioni di Giunta")
        print(f"Years: {', '.join(years)}")
        print()
        
        all_results = {}
        
        # Document types to search for (as requested by user)
        document_types = [
            "deliberazione",
            "relazioni di giunta",
            "delibera",
            "dgr"
        ]
        
        for year in years:
            print(f"📅 YEAR: {year}")
            print("-" * 30)
            
            year_results = self.search_by_year_and_keywords(year, document_types)
            all_results[year] = year_results
            
            if year_results:
                print(f"✅ Found {len(year_results)} results for {year}")
                
                # Show sample of results
                for i, result in enumerate(year_results[:3], 1):
                    doc_type = result.get('document_type', 'unknown')
                    text_preview = result.get('text', '')[:80]
                    print(f"  {i}. [{doc_type}] {text_preview}...")
                    
                    if result.get('links'):
                        print(f"     Links: {len(result['links'])}")
            else:
                print(f"❌ No results found for {year}")
            
            print()
            time.sleep(2)  # Be respectful between years
        
        return all_results
    
    def verify_deliberation_exists(self, deliberation_info: Dict) -> Optional[Dict]:
        """
        Verify if a specific deliberation from our Notion database exists on the decreto website.
        
        Args:
            deliberation_info: Dict with 'numero', 'seduta', 'titolo' from Notion
        
        Returns:
            Dict with verification results or None if not found
        """
        numero = deliberation_info.get('numero', '')
        seduta = deliberation_info.get('seduta', '')
        titolo = deliberation_info.get('titolo', '')
        
        print(f"🔍 Verifying: DGR n.{numero} - {titolo[:50]}...")
        
        # Search strategies
        search_terms = [
            f"DGR {numero}",
            f"numero {numero}",
            f"delibera {numero}",
            numero  # Just the number
        ]
        
        # Try to determine year from seduta date if possible
        search_year = "2025"  # Default to current year
        if seduta and len(seduta) >= 4:
            # Try to extract year from seduta date
            try:
                if "/" in seduta:
                    year_part = seduta.split("/")[-1]
                    if len(year_part) == 4 and year_part.isdigit():
                        search_year = year_part
                elif "-" in seduta:
                    year_part = seduta.split("-")[0]
                    if len(year_part) == 4 and year_part.isdigit():
                        search_year = year_part
            except:
                pass
        
        # Search for this specific deliberation
        hidden_fields = self.get_form_tokens()
        
        for term in search_terms:
            try:
                form_data = {
                    'select_1': search_year,  # Year
                    'unnamed_1': term,  # Search term
                    'chkSearchType': '2',  # Exact phrase search
                    **hidden_fields
                }
                
                response = self.session.post(
                    f"{self.base_url}/index.php",
                    data=form_data,
                    timeout=15
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for matches
                    page_text = soup.get_text().lower()
                    
                    if numero.lower() in page_text and any(word in page_text for word in ['delibera', 'dgr', 'decreto']):
                        return {
                            'found': True,
                            'search_term': term,
                            'year': search_year,
                            'numero': numero,
                            'verification_url': response.url,
                            'match_context': self.extract_match_context(soup, numero)
                        }
                
            except Exception as e:
                print(f"  Error verifying with term '{term}': {str(e)}")
            
            time.sleep(0.5)
        
        return {
            'found': False,
            'numero': numero,
            'searched_terms': search_terms,
            'searched_year': search_year
        }
    
    def extract_match_context(self, soup: BeautifulSoup, numero: str) -> str:
        """Extract context around a number match."""
        
        for element in soup.find_all(text=True):
            text = element.strip()
            if numero.lower() in text.lower() and len(text) > 20:
                return text[:150]
        
        return "Match found but no context extracted"

def main():
    """Test the decreto scraper with year and type filtering."""
    
    scraper = DecretoScraperFinal()
    
    # Test with recent years that should have data according to form analysis
    test_years = ["2020", "2019", "2018"]
    
    results = scraper.search_deliberations_for_years(test_years)
    
    # Save results
    output_file = "decreto_search_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"🎯 SEARCH COMPLETED")
    print(f"Results saved to: {output_file}")
    
    # Summary
    total_documents = sum(len(docs) for docs in results.values())
    print(f"Total documents found: {total_documents}")
    
    for year, docs in results.items():
        if docs:
            print(f"  {year}: {len(docs)} documents")

if __name__ == "__main__":
    main()
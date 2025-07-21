#!/usr/bin/env python3
"""
Working Decreto Scraper for decretidigitali.regione.liguria.it

This scraper uses the actual search endpoints discovered through analysis:
- Main search: /components/com_lddocs_iterg/getSearch.php
- Uses Elasticsearch queries posted as JSON
- Returns HTML results that need to be parsed

Based on comprehensive website analysis conducted on 2025-07-18.

Author: Website Analysis Team
Date: 2025-07-18
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('decreto_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DecretoScraper:
    """
    Working scraper for decretidigitali.regione.liguria.it
    
    Uses the actual Elasticsearch-based search endpoints discovered through analysis.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        self.base_url = "https://decretidigitali.regione.liguria.it"
        self.search_endpoint = f"{self.base_url}/components/com_lddocs_iterg/getSearch.php"
        
        # Default search parameters
        self.default_size = 10
        self.max_size = 50
        
        # Available fields for search results
        self.result_fields = [
            "dimensioneFileDecretoWeb",
            "ld:identificativoAtto",
            "ld:oggetto",
            "ld:tipoRegistro",
            "ld:tipoAtto",
            "materia",
            "argomento",
            "ld:nomeFileDecretoWeb",
            "ld:soggettoEmanante",
            "ld:numeroAttoRicercaWeb",
            "ld:annoAttoRicercaWeb",
            "ld:strutturaProponente",
            "ld:dataPubblicazioneRicercaWeb",
            "ld:dataRegistro"
        ]
    
    def build_elasticsearch_query(self, 
                                 keyword: str = "",
                                 year: str = "",
                                 document_type: str = "",
                                 issuing_authority: str = "",
                                 registry_number: str = "",
                                 subject_matter: str = "",
                                 topic: str = "",
                                 date_from: str = "",
                                 date_to: str = "",
                                 size: int = 10,
                                 from_offset: int = 0) -> str:
        """
        Build Elasticsearch query based on search parameters
        
        Args:
            keyword: Search term for document content
            year: Publication year (e.g., "2024")
            document_type: Type of document (e.g., "Delibera")
            issuing_authority: Authority that issued the document
            registry_number: Registry number of the document
            subject_matter: Subject matter category
            topic: Topic category
            date_from: Start date for date range (YYYY-MM-DD)
            date_to: End date for date range (YYYY-MM-DD)
            size: Number of results to return (max 50)
            from_offset: Starting offset for pagination
            
        Returns:
            JSON string containing the Elasticsearch query
        """
        
        query = {
            "_source": self.result_fields,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"indicizzato": 1}}  # Only indexed documents
                    ]
                }
            },
            "sort": [
                {"ld:dataPubblicazioneRicercaWeb": {"order": "desc"}}
            ],
            "from": from_offset,
            "size": min(size, self.max_size)
        }
        
        # Add keyword search
        if keyword.strip():
            # Support for different search types (all words, any word, exact phrase)
            query["query"]["bool"]["must"].append({
                "match": {
                    "ld:oggetto": {
                        "query": keyword.strip(),
                        "operator": "and"  # Default to "all words"
                    }
                }
            })
        
        # Add year filter
        if year.strip():
            query["query"]["bool"]["must"].append({
                "term": {"ld:annoAttoRicercaWeb": year.strip()}
            })
        
        # Add document type filter
        if document_type.strip():
            query["query"]["bool"]["must"].append({
                "term": {"ld:tipoAtto": document_type.strip()}
            })
        
        # Add issuing authority filter
        if issuing_authority.strip():
            query["query"]["bool"]["must"].append({
                "match": {"ld:soggettoEmanante": issuing_authority.strip()}
            })
        
        # Add registry number filter
        if registry_number.strip():
            query["query"]["bool"]["must"].append({
                "term": {"ld:numeroAttoRicercaWeb": registry_number.strip()}
            })
        
        # Add subject matter filter
        if subject_matter.strip():
            query["query"]["bool"]["must"].append({
                "term": {"materia.raw": subject_matter.strip()}
            })
        
        # Add topic filter
        if topic.strip():
            query["query"]["bool"]["must"].append({
                "term": {"argomento.raw": topic.strip()}
            })
        
        # Add date range filter
        if date_from.strip() or date_to.strip():
            date_range = {
                "range": {
                    "ld:dataPubblicazioneRicercaWeb": {}
                }
            }
            
            if date_from.strip():
                date_range["range"]["ld:dataPubblicazioneRicercaWeb"]["gte"] = f"{date_from.strip()}T00:00:00Z"
            
            if date_to.strip():
                date_range["range"]["ld:dataPubblicazioneRicercaWeb"]["lte"] = f"{date_to.strip()}T23:59:59Z"
            
            if date_range["range"]["ld:dataPubblicazioneRicercaWeb"]:
                date_range["range"]["ld:dataPubblicazioneRicercaWeb"]["format"] = "strict_date_optional_time||epoch_millis"
                query["query"]["bool"]["must"].append(date_range)
        
        return json.dumps(query, separators=(',', ':'))
    
    def execute_search(self, query_json: str, size: int = 10, from_offset: int = 0) -> Optional[str]:
        """
        Execute search query against the Elasticsearch endpoint
        
        Args:
            query_json: JSON string containing the Elasticsearch query
            size: Number of results to return
            from_offset: Starting offset for pagination
            
        Returns:
            HTML response containing search results, or None if failed
        """
        
        url = f"{self.search_endpoint}?size={size}&from={from_offset}"
        
        try:
            logger.info(f"Executing search: size={size}, from={from_offset}")
            logger.debug(f"Query: {query_json}")
            
            response = self.session.post(
                url,
                data=query_json,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self.base_url
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Search successful, response length: {len(response.text)}")
                return response.text
            else:
                logger.error(f"Search failed with status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return None
    
    def parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse HTML search results to extract decreto information
        
        Args:
            html_content: HTML content returned by search
            
        Returns:
            List of dictionaries containing decreto information
        """
        
        results = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for decreto entries in the HTML
        # The exact structure needs to be determined from actual search results
        
        # Common patterns to look for:
        patterns = [
            # Look for divs with decreto-related classes
            soup.find_all('div', class_=re.compile(r'decreto|risultato|atto', re.I)),
            # Look for table rows
            soup.find_all('tr'),
            # Look for list items
            soup.find_all('li'),
            # Look for articles
            soup.find_all('article'),
            # Look for any div with an ID containing result-related terms
            soup.find_all('div', id=re.compile(r'result|decreto|atto', re.I))
        ]
        
        all_potential_elements = []
        for pattern in patterns:
            all_potential_elements.extend(pattern)
        
        # Remove duplicates
        unique_elements = []
        seen = set()
        for elem in all_potential_elements:
            if elem not in seen:
                unique_elements.append(elem)
                seen.add(elem)
        
        # Extract information from each potential element
        for element in unique_elements:
            if not element:
                continue
                
            text = element.get_text().strip()
            if not text or len(text) < 10:  # Skip very short texts
                continue
            
            # Look for links within the element
            links = element.find_all('a', href=True)
            
            # Extract potential decreto information
            decreto_info = {
                'raw_text': text,
                'html': str(element),
                'links': [{'href': link.get('href'), 'text': link.get_text().strip()} 
                         for link in links if link.get('href')],
                'element_type': element.name,
                'element_class': element.get('class', []),
                'element_id': element.get('id', ''),
                'extracted_info': self._extract_decreto_fields(text)
            }
            
            # Only add if it looks like it contains decree information
            if self._looks_like_decreto(decreto_info):
                results.append(decreto_info)
        
        logger.info(f"Parsed {len(results)} potential decreto entries from HTML")
        return results
    
    def _extract_decreto_fields(self, text: str) -> Dict[str, str]:
        """
        Extract common decreto fields from text using regex patterns
        
        Args:
            text: Raw text to extract fields from
            
        Returns:
            Dictionary of extracted fields
        """
        
        extracted = {}
        
        # Common patterns for decreto information
        patterns = {
            'number': r'[Nn]\.?\s*(\d+)',
            'year': r'(?:del|anno)\s*(\d{4})',
            'date': r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            'type': r'(Delibera|Decreto|Determina|Ordinanza|Circolare)',
            'subject': r'[Oo]ggetto[:\s]+([^\n]+)',
            'authority': r'[Aa]utorit[aà][:\s]+([^\n]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1).strip()
        
        return extracted
    
    def _looks_like_decreto(self, decreto_info: Dict[str, Any]) -> bool:
        """
        Determine if parsed information looks like a decreto entry
        
        Args:
            decreto_info: Dictionary containing parsed information
            
        Returns:
            True if it looks like a decreto, False otherwise
        """
        
        text = decreto_info['raw_text'].lower()
        
        # Check for decreto-related keywords
        decreto_keywords = [
            'delibera', 'decreto', 'determina', 'ordinanza', 'circolare',
            'oggetto', 'numero', 'data', 'pubblicazione', 'giunta', 'consiglio'
        ]
        
        keyword_count = sum(1 for keyword in decreto_keywords if keyword in text)
        
        # Check for links (decreti usually have download links)
        has_links = len(decreto_info['links']) > 0
        
        # Check for extracted fields
        has_extracted_fields = len(decreto_info['extracted_info']) > 0
        
        # Minimum criteria for considering it a decreto
        return (keyword_count >= 2 or has_links or has_extracted_fields) and len(text) > 20
    
    def search(self, 
               keyword: str = "",
               year: str = "",
               document_type: str = "",
               size: int = 10,
               **kwargs) -> List[Dict[str, Any]]:
        """
        Perform a complete search operation
        
        Args:
            keyword: Search term
            year: Publication year
            document_type: Type of document
            size: Number of results to return
            **kwargs: Additional search parameters
            
        Returns:
            List of parsed decreto information
        """
        
        # Build the query
        query_json = self.build_elasticsearch_query(
            keyword=keyword,
            year=year,
            document_type=document_type,
            size=size,
            **kwargs
        )
        
        # Execute the search
        html_response = self.execute_search(query_json, size=size)
        
        if html_response:
            # Parse the results
            results = self.parse_search_results(html_response)
            
            # Save raw response for debugging
            if results:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"search_response_{timestamp}.html"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html_response)
                    logger.info(f"Saved raw response to {filename}")
                except Exception as e:
                    logger.error(f"Failed to save response: {e}")
            
            return results
        else:
            logger.error("Search failed - no response received")
            return []
    
    def get_available_years(self) -> List[str]:
        """
        Get available years from the combo endpoint
        
        Returns:
            List of available years
        """
        
        url = f"{self.base_url}/components/com_lddocs_iterg/getSearchAnniCombo.php"
        
        # Build aggregation query for years
        query = {
            "size": 0,
            "aggs": {
                "anno": {
                    "terms": {
                        "field": "ld:annoAttoRicercaWeb",
                        "size": 0,
                        "order": {"_term": "asc"}
                    }
                }
            }
        }
        
        try:
            response = self.session.post(
                url,
                data=json.dumps(query),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                # Parse HTML response to extract years
                soup = BeautifulSoup(response.text, 'html.parser')
                options = soup.find_all('option')
                years = [opt.get('value') for opt in options if opt.get('value') and opt.get('value').isdigit()]
                return sorted(years)
            
        except Exception as e:
            logger.error(f"Failed to get available years: {e}")
        
        return []
    
    def get_available_document_types(self) -> List[str]:
        """
        Get available document types from the combo endpoint
        
        Returns:
            List of available document types
        """
        
        url = f"{self.base_url}/components/com_lddocs_iterg/getSearchTipoAttoCombo.php"
        
        # Build aggregation query for document types
        query = {
            "size": 0,
            "aggs": {
                "tipoatto": {
                    "terms": {
                        "field": "ld:tipoAtto.raw",
                        "size": 0,
                        "order": {"_term": "asc"}
                    }
                }
            }
        }
        
        try:
            response = self.session.post(
                url,
                data=json.dumps(query),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                # Parse HTML response to extract document types
                soup = BeautifulSoup(response.text, 'html.parser')
                options = soup.find_all('option')
                types = [opt.get('value') for opt in options if opt.get('value') and opt.get('value').strip()]
                return [t for t in types if t]
            
        except Exception as e:
            logger.error(f"Failed to get available document types: {e}")
        
        return []


def main():
    """
    Example usage of the decreto scraper
    """
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    scraper = DecretoScraper()
    
    # Test search for "delibera" in 2024
    logger.info("Testing search for 'delibera' in 2024...")
    results = scraper.search(
        keyword="delibera",
        year="2024",
        size=5
    )
    
    print(f"\n🔍 Search Results: {len(results)} found")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        print(f"\n📄 Result {i}:")
        print(f"   Type: {result['element_type']} ({result['element_class']})")
        print(f"   Links: {len(result['links'])}")
        print(f"   Extracted: {result['extracted_info']}")
        print(f"   Text: {result['raw_text'][:100]}...")
        
        if result['links']:
            print(f"   First link: {result['links'][0]['href']}")
    
    # Test getting available years
    logger.info("Getting available years...")
    years = scraper.get_available_years()
    print(f"\n📅 Available years: {years[:10]}...")  # Show first 10
    
    # Test getting available document types
    logger.info("Getting available document types...")
    types = scraper.get_available_document_types()
    print(f"\n📝 Available document types: {types}")
    
    print("\n✅ Scraper testing completed!")


if __name__ == "__main__":
    main()
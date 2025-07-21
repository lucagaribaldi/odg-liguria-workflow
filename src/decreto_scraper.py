"""
Decreto Scraper for checking publication status on decretidigitali.regione.liguria.it
Verifies if decreti from ODG are published on the official website.
"""

import logging
import requests
import time
from typing import Tuple, Optional, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import random


class DecretoScraper:
    """Scraper for checking decreto publication status on Regione Liguria website."""

    def __init__(
        self,
        base_url: str = "https://decretidigitali.regione.liguria.it",
        rate_limit: float = 1.0,
        max_retries: int = 3,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Initialize the decreto scraper.

        Args:
            base_url: Base URL for the decreto website
            rate_limit: Minimum seconds between requests
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.last_request_time = 0

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        # Browser-like headers to avoid blocking
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        # Common search patterns for decreto identification
        self.decreto_patterns = {
            "dgr": r"(?:DGR|D\.G\.R\.)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
            "dcr": r"(?:DCR|D\.C\.R\.)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
            "decreto": r"(?:DECRETO|Decreto)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
            "deliberazione": r"(?:Deliberazione|DELIBERAZIONE)\s*(?:n\.|N\.|num\.|NUM\.)\s*(\d+)",
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Configure SSL verification
        if not self.verify_ssl:
            self.session.verify = False
            # Disable SSL warnings when verification is disabled
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.logger.info(f"DecretoScraper initialized with base_url: {base_url}")

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(self, url: str, params: dict = None) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic and rate limiting.

        Args:
            url: URL to request
            params: Optional query parameters

        Returns:
            Response object or None if all retries failed
        """
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(
                    f"Making request to {url} " f"(attempt {attempt + 1}/{self.max_retries})"
                )

                response = self.session.get(
                    url, params=params, timeout=self.timeout, allow_redirects=True
                )

                response.raise_for_status()
                self.logger.debug(f"Request successful: {response.status_code}")
                return response

            except requests.exceptions.RequestException as e:
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): " f"{str(e)}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    backoff_time = (2**attempt) + random.uniform(0, 1)
                    self.logger.debug(f"Backing off for {backoff_time:.2f} seconds")
                    time.sleep(backoff_time)
                else:
                    self.logger.error(f"All retry attempts failed for {url}")
                    return None

        return None

    def verify_decreto_publication(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify if a decreto is published on the official website.

        Args:
            seduta: Session number
            numero: Decreto number
            oggetto: Decreto subject/object
            data_seduta: Session date (YYYY-MM-DD format)

        Returns:
            Dictionary with publication info: {
                'found': bool,
                'url': str|None,
                'data_pubblicazione': str|None,
                'dgr_numero': str|None,
                'dgr_anno': str|None
            }
        """
        self.logger.info(f"Verifying publication for decreto {numero} from seduta {seduta}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            # Try the working scraper implementation first
            try:
                working_result = self._search_with_working_scraper(seduta, numero, oggetto, data_seduta)
                if working_result.get("found"):
                    self.logger.info(f"Decreto {numero} found with working scraper: {working_result}")
                    return working_result
            except Exception as e:
                self.logger.warning(f"Working scraper failed: {str(e)}")
                # Continue with original strategies
            
            # Try multiple search strategies with enhanced info extraction
            search_strategies = [
                self._search_by_numero_and_date,
                self._search_by_oggetto_and_date,
                self._search_by_seduta_and_numero,
                self._search_by_numero,  # Fallback
            ]

            for strategy in search_strategies:
                try:
                    strategy_result = strategy(seduta, numero, oggetto, data_seduta)
                    if strategy_result.get("found"):
                        result.update(strategy_result)
                        self.logger.info(f"Decreto {numero} found: {result}")
                        return result
                except Exception as e:
                    self.logger.warning(f"Search strategy failed: {str(e)}")
                    continue

            self.logger.info(f"Decreto {numero} not found on website")
            return result

        except Exception as e:
            self.logger.error(f"Error verifying decreto {numero}: {str(e)}")
            return result

    def _search_by_numero_and_date(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by number and session date."""
        self.logger.debug(f"Searching by numero {numero} and date {data_seduta}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        # Build search params with date range
        params = {"numero": numero}
        if data_seduta:
            # Search in a date range around the session date
            params["data_da"] = data_seduta
            # Add 30 days for publication delay
            try:
                session_date = datetime.strptime(data_seduta, "%Y-%m-%d")
                end_date = session_date + timedelta(days=30)
                params["data_a"] = end_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        search_urls = [
            f"{self.base_url}/ricerca",
            f"{self.base_url}/search",
            f"{self.base_url}/decreti",
        ]

        for search_url in search_urls:
            try:
                response = self._make_request(search_url, params)
                if response:
                    found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                    if found_result.get("found"):
                        result.update(found_result)
                        return result
            except Exception as e:
                self.logger.debug(f"Search by numero and date failed for {search_url}: {str(e)}")
                continue

        return result

    def _search_by_oggetto_and_date(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by object and session date."""
        self.logger.debug(f"Searching by oggetto and date {data_seduta}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        # Extract key terms from oggetto
        key_terms = self._extract_key_terms(oggetto)

        for term in key_terms:
            try:
                params = {"oggetto": term, "query": term}
                if data_seduta:
                    params["data_da"] = data_seduta
                    try:
                        session_date = datetime.strptime(data_seduta, "%Y-%m-%d")
                        end_date = session_date + timedelta(days=30)
                        params["data_a"] = end_date.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                response = self._make_request(f"{self.base_url}/ricerca", params)
                if response:
                    found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                    if found_result.get("found"):
                        result.update(found_result)
                        return result
            except Exception as e:
                self.logger.debug(f"Search by oggetto and date failed for term '{term}': {str(e)}")
                continue

        return result

    def _search_by_numero(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by number."""
        self.logger.debug(f"Searching by numero: {numero}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        # Try different search endpoints
        search_urls = [
            f"{self.base_url}/ricerca",
            f"{self.base_url}/search",
            f"{self.base_url}/decreti",
        ]

        for search_url in search_urls:
            try:
                # Search parameters
                params = {"numero": numero, "query": numero, "search": numero}

                response = self._make_request(search_url, params)
                if response:
                    found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                    if found_result.get("found"):
                        result.update(found_result)
                        return result

            except Exception as e:
                self.logger.debug(f"Search by numero failed for {search_url}: {str(e)}")
                continue

        return result

    def _search_by_oggetto(
        self, seduta: str, numero: str, oggetto: str
    ) -> Tuple[bool, Optional[str]]:
        """Search decreto by object/subject."""
        self.logger.debug(f"Searching by oggetto: {oggetto[:50]}...")

        # Extract key terms from oggetto
        key_terms = self._extract_key_terms(oggetto)

        for term in key_terms:
            try:
                params = {"oggetto": term, "query": term, "search": term}

                response = self._make_request(f"{self.base_url}/ricerca", params)
                if response:
                    found, url = self._parse_search_results(response, numero, oggetto)
                    if found:
                        return found, url

            except Exception as e:
                self.logger.debug(f"Search by oggetto failed for term '{term}': {str(e)}")
                continue

        return False, None

    def _search_by_seduta_and_numero(
        self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decreto by session and number combination."""
        self.logger.debug(f"Searching by seduta {seduta} and numero {numero}")

        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            params = {
                "seduta": seduta,
                "numero": numero,
                "query": f"seduta {seduta} numero {numero}",
            }

            response = self._make_request(f"{self.base_url}/ricerca", params)
            if response:
                found_result = self._parse_search_results_enhanced(response, numero, oggetto)
                if found_result.get("found"):
                    result.update(found_result)

        except Exception as e:
            self.logger.debug(f"Search by seduta and numero failed: {str(e)}")

        return result

    def _parse_search_results(
        self, response: requests.Response, numero: str, oggetto: str
    ) -> Tuple[bool, Optional[str]]:
        """Parse search results to find matching decreto."""
        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for decreto links or entries
            potential_matches = []

            # Common selectors for decreto listings
            selectors = [
                'a[href*="decreto"]',
                'a[href*="dgr"]',
                'a[href*="dcr"]',
                ".decreto-item a",
                ".result-item a",
                ".search-result a",
            ]

            for selector in selectors:
                links = soup.select(selector)
                potential_matches.extend(links)

            # If no specific selectors work, try all links
            if not potential_matches:
                potential_matches = soup.find_all("a", href=True)

            # Score and filter matches
            best_match = None
            best_score = 0

            for link in potential_matches:
                score = self._calculate_match_score(link, numero, oggetto)
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_score = score
                    best_match = link

            if best_match:
                href = best_match.get("href")
                if href:
                    if href.startswith("/"):
                        full_url = urljoin(self.base_url, href)
                    else:
                        full_url = href

                    self.logger.debug(f"Found match with score {best_score:.2f}: {full_url}")
                    return True, full_url

            return False, None

        except Exception as e:
            self.logger.warning(f"Error parsing search results: {str(e)}")
            return False, None

    def _calculate_match_score(self, link_element, numero: str, oggetto: str) -> float:
        """Calculate match score for a potential decreto link."""
        score = 0.0

        # Get link text and href
        link_text = link_element.get_text(strip=True).lower()
        link_href = link_element.get("href", "").lower()

        # Check for numero match
        if numero.lower() in link_text or numero.lower() in link_href:
            score += 0.5

        # Check for oggetto keywords
        oggetto_words = set(word.lower() for word in oggetto.split() if len(word) > 3)
        link_words = set(word.lower() for word in link_text.split())

        if oggetto_words and link_words:
            word_overlap = len(oggetto_words.intersection(link_words))
            score += (word_overlap / len(oggetto_words)) * 0.3

        # Check for decreto-related keywords
        decreto_keywords = ["decreto", "dgr", "dcr", "deliberazione"]
        for keyword in decreto_keywords:
            if keyword in link_text or keyword in link_href:
                score += 0.2
                break

        return score

    def _extract_key_terms(self, oggetto: str) -> list:
        """Extract key terms from oggetto for search."""
        # Remove common words and extract meaningful terms
        stop_words = {
            "di",
            "da",
            "in",
            "con",
            "su",
            "per",
            "tra",
            "fra",
            "a",
            "e",
            "il",
            "lo",
            "la",
            "i",
            "gli",
            "le",
            "un",
            "una",
            "uno",
            "del",
            "dello",
            "della",
            "dei",
            "degli",
            "delle",
            "al",
            "allo",
            "alla",
            "ai",
            "agli",
            "alle",
            "dal",
            "dallo",
            "dalla",
            "dai",
            "dagli",
            "dalle",
            "nel",
            "nello",
            "nella",
            "nei",
            "negli",
            "nelle",
            "sul",
            "sullo",
            "sulla",
            "sui",
            "sugli",
            "sulle",
        }

        words = re.findall(r"\b[a-zA-Zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]{4,}\b", oggetto.lower())
        key_terms = [word for word in words if word not in stop_words]

        # Return top 5 most relevant terms
        return key_terms[:5]

    def _parse_search_results_enhanced(
        self, response: requests.Response, numero: str, oggetto: str
    ) -> Dict[str, Any]:
        """Parse search results with enhanced extraction of DGR info and dates."""
        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for decreto links or entries
            potential_matches = []

            # Common selectors for decreto listings
            selectors = [
                'a[href*="decreto"]',
                'a[href*="dgr"]',
                'a[href*="dcr"]',
                ".decreto-item",
                ".result-item",
                ".search-result",
                ".deliberazione-item",
            ]

            for selector in selectors:
                elements = soup.select(selector)
                potential_matches.extend(elements)

            # If no specific selectors work, try all links
            if not potential_matches:
                potential_matches = soup.find_all("a", href=True)

            # Score and filter matches
            best_match = None
            best_score = 0

            for element in potential_matches:
                match_info = self._extract_match_info_enhanced(element, numero, oggetto)

                if match_info["score"] > best_score and match_info["score"] > 0.3:
                    best_score = match_info["score"]
                    best_match = match_info

            if best_match:
                result["found"] = True
                result["url"] = best_match["url"]
                result["data_pubblicazione"] = best_match.get("data_pubblicazione")
                result["dgr_numero"] = best_match.get("dgr_numero")
                result["dgr_anno"] = best_match.get("dgr_anno")

                self.logger.debug(f"Found match with score {best_score:.2f}")

            return result

        except Exception as e:
            self.logger.warning(f"Error parsing enhanced search results: {str(e)}")
            return result

    def _extract_match_info_enhanced(self, element, numero: str, oggetto: str) -> Dict[str, Any]:
        """Extract enhanced match information including DGR number and dates."""
        info = {
            "score": 0.0,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }

        try:
            # Get element text and href
            element_text = element.get_text(strip=True).lower()
            element_href = element.get("href", "").lower()

            # Build full URL
            if element_href:
                if element_href.startswith("/"):
                    info["url"] = f"{self.base_url}{element_href}"
                elif element_href.startswith("http"):
                    info["url"] = element_href
                else:
                    info["url"] = f"{self.base_url}/{element_href}"

            # Score based on numero match
            if numero.lower() in element_text or numero.lower() in element_href:
                info["score"] += 0.5

            # Score based on oggetto keywords
            oggetto_words = set(word.lower() for word in oggetto.split() if len(word) > 3)
            element_words = set(word.lower() for word in element_text.split())

            if oggetto_words and element_words:
                word_overlap = len(oggetto_words.intersection(element_words))
                info["score"] += (word_overlap / len(oggetto_words)) * 0.3

            # Check for decreto-related keywords
            decreto_keywords = ["decreto", "dgr", "dcr", "deliberazione"]
            for keyword in decreto_keywords:
                if keyword in element_text or keyword in element_href:
                    info["score"] += 0.2
                    break

            # Extract DGR information from text
            dgr_info = self._extract_dgr_info(element_text)
            if dgr_info:
                info["dgr_numero"] = dgr_info.get("numero")
                info["dgr_anno"] = dgr_info.get("anno")
                info["score"] += 0.1

            # Extract publication date
            date_info = self._extract_date_info(element_text)
            if date_info:
                info["data_pubblicazione"] = date_info
                info["score"] += 0.1

            return info

        except Exception as e:
            self.logger.debug(f"Error extracting match info: {str(e)}")
            return info

    def _extract_dgr_info(self, text: str) -> Optional[Dict[str, str]]:
        """Extract DGR number and year from text."""
        dgr_patterns = [
            r"DGR\s+n\.\s*(\d+)\s*/\s*(\d{4})",
            r"DGR\s+(\d+)\s*/\s*(\d{4})",
            r"Deliberazione\s+n\.\s*(\d+)\s*/\s*(\d{4})",
            r"Delibera\s+n\.\s*(\d+)\s*/\s*(\d{4})",
            r"n\.\s*(\d+)\s*/\s*(\d{4})",
            r"(\d+)\s*/\s*(\d{4})",
        ]

        for pattern in dgr_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {"numero": match.group(1), "anno": match.group(2)}

        return None

    def _extract_date_info(self, text: str) -> Optional[str]:
        """Extract publication date from text."""
        date_patterns = [
            r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
            r"(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
            r"pubblicat[oa]\s+il\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
            r"data\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
            r"del\s+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Normalize date format
                normalized_date = self._normalize_date_string(date_str)
                if normalized_date:
                    return normalized_date

        return None

    def _normalize_date_string(self, date_str: str) -> Optional[str]:
        """Normalize date string to YYYY-MM-DD format."""
        try:
            # Handle different date formats
            date_patterns = [
                r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})",
                r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})",
            ]

            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    parts = match.groups()
                    if len(parts[2]) == 4:  # Year is last
                        day, month, year = parts
                    else:  # Year is first
                        year, month, day = parts

                    # Normalize to ISO format
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            return None

        except Exception as e:
            self.logger.debug(f"Error normalizing date '{date_str}': {str(e)}")
            return None

    def _search_with_working_scraper(self, seduta: str, numero: str, oggetto: str, data_seduta: Optional[str] = None) -> Dict[str, Any]:
        """Search using the working scraper implementation."""
        self.logger.debug(f"Searching with working scraper for decreto {numero}")
        
        result = {
            "found": False,
            "url": None,
            "data_pubblicazione": None,
            "dgr_numero": None,
            "dgr_anno": None,
        }
        
        try:
            # Import the working scraper functionality
            from datetime import datetime
            
            # Extract year for search
            year = None
            if data_seduta:
                try:
                    date_obj = datetime.strptime(data_seduta, "%Y-%m-%d")
                    year = date_obj.year
                except:
                    year = 2025  # Default fallback
            else:
                year = 2025  # Default fallback
            
            # Search endpoint
            search_url = f"{self.base_url}/components/com_lddocs_iterg/getSearch.php"
            
            # Prepare search query
            search_terms = []
            if numero:
                search_terms.append(f"numero {numero}")
            if seduta:
                search_terms.append(f"seduta {seduta}")
            
            # Extract key terms from oggetto
            key_terms = self._extract_key_terms(oggetto)
            search_terms.extend(key_terms[:2])  # Add first 2 key terms
            
            query_text = " ".join(search_terms)
            
            # Elasticsearch query
            query_data = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": ["title", "content", "numero", "oggetto"],
                                    "type": "best_fields",
                                    "operator": "or"
                                }
                            },
                            {
                                "range": {
                                    "anno": {
                                        "gte": year - 1,
                                        "lte": year + 1
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 10,
                "sort": [{"data_pubblicazione": {"order": "desc"}}]
            }
            
            # Make the search request
            response = self._make_enhanced_request(search_url, method="POST", json_data=query_data)
            
            if response and response.status_code == 200:
                # Parse the response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for decreto results
                decreto_links = soup.find_all('a', href=True)
                
                for link in decreto_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Check if this looks like a decreto
                    if any(keyword in text.lower() for keyword in ['decreto', 'deliberazione', 'dgr', 'dcr']):
                        # Extract information
                        if numero in text or seduta in text:
                            result["found"] = True
                            result["url"] = href if href.startswith('http') else f"{self.base_url}{href}"
                            
                            # Try to extract DGR number and date
                            dgr_match = re.search(r'(\d+)/(\d{4})', text)
                            if dgr_match:
                                result["dgr_numero"] = dgr_match.group(1)
                                result["dgr_anno"] = dgr_match.group(2)
                            
                            # Try to extract date
                            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
                            if date_match:
                                result["data_pubblicazione"] = self._normalize_date_string(date_match.group(1))
                            
                            break
            
            return result
            
        except Exception as e:
            self.logger.debug(f"Working scraper search failed: {str(e)}")
            return result

    def _make_enhanced_request(self, url: str, params: dict = None, method: str = "GET", json_data: dict = None) -> Optional[requests.Response]:
        """Enhanced request method supporting POST with JSON data."""
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{self.max_retries})")
                
                if method.upper() == "POST":
                    if json_data:
                        response = self.session.post(
                            url, 
                            json=json_data, 
                            timeout=self.timeout, 
                            allow_redirects=True
                        )
                    else:
                        response = self.session.post(
                            url, 
                            data=params, 
                            timeout=self.timeout, 
                            allow_redirects=True
                        )
                else:
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=self.timeout, 
                        allow_redirects=True
                    )

                response.raise_for_status()
                self.logger.debug(f"Request successful: {response.status_code}")
                return response

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    backoff_time = (2**attempt) + random.uniform(0, 1)
                    self.logger.debug(f"Backing off for {backoff_time:.2f} seconds")
                    time.sleep(backoff_time)
                else:
                    self.logger.error(f"All retry attempts failed for {url}")
                    return None

        return None

    def get_decreto_details(self, decreto_url: str) -> dict:
        """
        Get detailed information about a decreto from its URL.

        Args:
            decreto_url: URL of the decreto page

        Returns:
            Dictionary with decreto details
        """
        self.logger.info(f"Getting details for decreto: {decreto_url}")

        try:
            response = self._make_request(decreto_url)
            if not response:
                return {}

            soup = BeautifulSoup(response.text, "html.parser")

            details = {
                "url": decreto_url,
                "title": None,
                "numero": None,
                "data_pubblicazione": None,
                "oggetto": None,
                "status": None,
            }

            # Extract title
            title_element = soup.find("title") or soup.find("h1")
            if title_element:
                details["title"] = title_element.get_text(strip=True)

            # Try to extract structured data
            # This would need to be customized based on actual website structure

            return details

        except Exception as e:
            self.logger.error(f"Error getting decreto details: {str(e)}")
            return {}


def main():
    """Example usage of the DecretoScraper."""
    scraper = DecretoScraper()

    # Example verification
    try:
        found, url = scraper.verify_decreto_publication(
            seduta="3929",
            numero="1",
            oggetto="AZIENDA PUBBLICA DI SERVIZI ALLA PERSONA OPERE PIE RIUNITE DEVOTO MARINI SIVORI",
        )

        if found:
            print(f"Decreto found at: {url}")

            # Get additional details
            details = scraper.get_decreto_details(url)
            print(f"Details: {details}")
        else:
            print("Decreto not found")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()

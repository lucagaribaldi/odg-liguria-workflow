#!/usr/bin/env python3
"""
Form Analyzer for ODG Liguria Website
Analyzes the search form structure and extracts dropdown options, field mappings, and validation rules.
"""

import logging
import requests
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time


class FormAnalyzer:
    """Analyzer for decreto search form structure and validation rules."""
    
    def __init__(
        self,
        base_url: str = "https://decretidigitali.regione.liguria.it",
        verify_ssl: bool = True,
        allow_unverified_ssl: bool = True,
        timeout: int = 30
    ):
        """Initialize form analyzer.
        
        Args:
            base_url: Base URL of the decreto website
            verify_ssl: Whether to verify SSL certificates
            allow_unverified_ssl: Allow fallback to unverified SSL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.allow_unverified_ssl = allow_unverified_ssl
        self.timeout = timeout
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Setup session
        self.session = requests.Session()
        self._setup_session()
        
        # Analysis results
        self.form_analysis = {
            "analysis_timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "form_fields": {},
            "dropdown_options": {},
            "dynamic_dropdown_options": {},
            "validation_rules": {},
            "required_fields": [],
            "optional_fields": [],
            "field_mappings": {},
            "search_types": {},
            "errors": []
        }
    
    def _setup_session(self):
        """Setup requests session with appropriate configuration."""
        # Browser-like headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                     "image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configure SSL
        if not self.verify_ssl:
            self.session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def analyze_form(self) -> Dict[str, Any]:
        """Perform complete form analysis and return results.
        
        Returns:
            Dictionary with complete form analysis results
        """
        self.logger.info("Starting form analysis...")
        
        try:
            # Step 1: Fetch the main page
            main_page_content = self._fetch_main_page()
            if not main_page_content:
                self.form_analysis["errors"].append("Failed to fetch main page")
                return self.form_analysis
            
            # Step 2: Parse form structure
            self._parse_form_structure(main_page_content)
            
            # Step 3: Extract dropdown options
            self._extract_dropdown_options(main_page_content)
            
            # Step 4: Analyze validation rules
            self._analyze_validation_rules(main_page_content)
            
            # Step 5: Identify required vs optional fields
            self._identify_field_requirements(main_page_content)
            
            # Step 6: Extract dynamic dropdown options
            self._extract_dynamic_dropdown_options(main_page_content)
            
            # Step 7: Analyze search types
            self._analyze_search_types(main_page_content)
            
            # Step 8: Create field mappings
            self._create_field_mappings()
            
            self.logger.info("Form analysis completed successfully")
            
        except Exception as e:
            error_msg = f"Form analysis failed: {str(e)}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
        
        return self.form_analysis
    
    def _fetch_main_page(self) -> Optional[str]:
        """Fetch the main page content with form."""
        try:
            self.logger.info(f"Fetching main page: {self.base_url}")
            
            # Try with SSL verification first
            try:
                response = self.session.get(self.base_url, timeout=self.timeout)
                response.raise_for_status()
                
                self.logger.info(f"Main page fetched successfully: {response.status_code}")
                return response.text
                
            except requests.exceptions.SSLError as e:
                if self.allow_unverified_ssl:
                    self.logger.warning(f"SSL error, trying unverified connection: {e}")
                    return self._fetch_with_unverified_ssl()
                else:
                    raise
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch main page: {e}")
            return None
    
    def _fetch_with_unverified_ssl(self) -> Optional[str]:
        """Fetch page with unverified SSL as fallback."""
        try:
            # Create session with SSL verification disabled
            unverified_session = requests.Session()
            unverified_session.headers.update(self.session.headers)
            unverified_session.verify = False
            
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = unverified_session.get(self.base_url, timeout=self.timeout * 2)
            response.raise_for_status()
            
            self.logger.info("Main page fetched with unverified SSL")
            return response.text
            
        except Exception as e:
            self.logger.error(f"Unverified SSL fetch failed: {e}")
            return None
    
    def _parse_form_structure(self, html_content: str):
        """Parse the HTML to find form structure."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for forms
            forms = soup.find_all('form')
            self.logger.info(f"Found {len(forms)} forms on page")
            
            for i, form in enumerate(forms):
                form_info = {
                    "index": i,
                    "method": form.get('method', 'GET').upper(),
                    "action": form.get('action', ''),
                    "id": form.get('id', ''),
                    "class": form.get('class', []),
                    "fields": []
                }
                
                # Find all input fields
                inputs = form.find_all(['input', 'select', 'textarea'])
                
                for input_field in inputs:
                    field_info = {
                        "tag": input_field.name,
                        "type": input_field.get('type', ''),
                        "name": input_field.get('name', ''),
                        "id": input_field.get('id', ''),
                        "class": input_field.get('class', []),
                        "placeholder": input_field.get('placeholder', ''),
                        "required": input_field.has_attr('required'),
                        "value": input_field.get('value', ''),
                        "maxlength": input_field.get('maxlength', ''),
                        "pattern": input_field.get('pattern', ''),
                        "options": []
                    }
                    
                    # For select fields, extract options
                    if input_field.name == 'select':
                        options = input_field.find_all('option')
                        for option in options:
                            field_info["options"].append({
                                "value": option.get('value', ''),
                                "text": option.get_text(strip=True),
                                "selected": option.has_attr('selected')
                            })
                    
                    form_info["fields"].append(field_info)
                
                self.form_analysis["form_fields"][f"form_{i}"] = form_info
                
        except Exception as e:
            error_msg = f"Error parsing form structure: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _extract_dropdown_options(self, html_content: str):
        """Extract all dropdown options from the page."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all select elements
            selects = soup.find_all('select')
            self.logger.info(f"Found {len(selects)} dropdown fields")
            
            for select in selects:
                field_name = select.get('name', select.get('id', 'unknown'))
                field_info = {
                    "field_name": field_name,
                    "field_id": select.get('id', ''),
                    "field_class": select.get('class', []),
                    "multiple": select.has_attr('multiple'),
                    "required": select.has_attr('required'),
                    "options": []
                }
                
                # Extract options
                options = select.find_all('option')
                for option in options:
                    option_info = {
                        "value": option.get('value', ''),
                        "text": option.get_text(strip=True),
                        "selected": option.has_attr('selected'),
                        "disabled": option.has_attr('disabled')
                    }
                    field_info["options"].append(option_info)
                
                self.form_analysis["dropdown_options"][field_name] = field_info
                
                # Log specific fields of interest
                if any(keyword in field_name.lower() for keyword in 
                       ['tipo', 'atto', 'materia', 'argomento', 'area']):
                    self.logger.info(f"Found important dropdown '{field_name}' with {len(field_info['options'])} options")
                    
        except Exception as e:
            error_msg = f"Error extracting dropdown options: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _analyze_validation_rules(self, html_content: str):
        """Analyze validation rules from form fields and JavaScript."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Analyze input field validation attributes
            inputs = soup.find_all(['input', 'select', 'textarea'])
            
            for input_field in inputs:
                field_name = input_field.get('name', input_field.get('id', 'unknown'))
                
                validation_rules = {
                    "required": input_field.has_attr('required'),
                    "pattern": input_field.get('pattern', ''),
                    "maxlength": input_field.get('maxlength', ''),
                    "minlength": input_field.get('minlength', ''),
                    "min": input_field.get('min', ''),
                    "max": input_field.get('max', ''),
                    "type": input_field.get('type', ''),
                    "step": input_field.get('step', ''),
                    "data_validation": {}
                }
                
                # Extract data-* attributes that might contain validation rules
                for attr_name, attr_value in input_field.attrs.items():
                    if attr_name.startswith('data-'):
                        validation_rules["data_validation"][attr_name] = attr_value
                
                # Analyze field type-specific rules
                field_type = input_field.get('type', '').lower()
                if field_type == 'date':
                    validation_rules["format"] = "YYYY-MM-DD"
                elif field_type == 'email':
                    validation_rules["format"] = "email"
                elif field_type == 'number':
                    validation_rules["format"] = "numeric"
                
                # Special analysis for date fields
                if any(keyword in field_name.lower() for keyword in ['data', 'date']):
                    validation_rules["date_field"] = True
                    validation_rules["likely_format"] = self._detect_date_format(input_field)
                
                # Special analysis for year fields
                if 'anno' in field_name.lower() or 'year' in field_name.lower():
                    validation_rules["year_field"] = True
                    validation_rules["likely_range"] = self._detect_year_range(input_field)
                
                self.form_analysis["validation_rules"][field_name] = validation_rules
                
            # Look for JavaScript validation
            self._extract_javascript_validation(html_content)
            
        except Exception as e:
            error_msg = f"Error analyzing validation rules: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _detect_date_format(self, input_field) -> str:
        """Detect likely date format from field attributes."""
        placeholder = input_field.get('placeholder', '').lower()
        pattern = input_field.get('pattern', '')
        
        if 'dd/mm/yyyy' in placeholder or 'gg/mm/aaaa' in placeholder:
            return "DD/MM/YYYY"
        elif 'yyyy-mm-dd' in placeholder:
            return "YYYY-MM-DD"
        elif 'mm/dd/yyyy' in placeholder:
            return "MM/DD/YYYY"
        elif pattern:
            if '\\d{2}/\\d{2}/\\d{4}' in pattern:
                return "DD/MM/YYYY"
            elif '\\d{4}-\\d{2}-\\d{2}' in pattern:
                return "YYYY-MM-DD"
        
        return "DD/MM/YYYY"  # Default Italian format
    
    def _detect_year_range(self, input_field) -> Dict[str, Any]:
        """Detect year range from field attributes."""
        min_year = input_field.get('min', '')
        max_year = input_field.get('max', '')
        
        range_info = {
            "min": min_year if min_year else "1990",  # Default
            "max": max_year if max_year else str(datetime.now().year + 1),  # Default
            "current_year": datetime.now().year
        }
        
        return range_info
    
    def _extract_javascript_validation(self, html_content: str):
        """Extract validation rules from JavaScript code."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            scripts = soup.find_all('script')
            
            js_validation = {
                "validation_functions": [],
                "field_rules": {},
                "error_messages": []
            }
            
            for script in scripts:
                if script.string:
                    js_content = script.string
                    
                    # Look for validation patterns
                    validation_patterns = [
                        r'function\s+validate\w*\([^)]*\)',
                        r'\.validate\s*\(',
                        r'required\s*:\s*true',
                        r'pattern\s*:\s*["\']([^"\']+)["\']',
                        r'min\s*:\s*(\d+)',
                        r'max\s*:\s*(\d+)',
                    ]
                    
                    for pattern in validation_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE)
                        if matches:
                            js_validation["validation_functions"].extend(matches)
                    
                    # Look for error messages
                    error_patterns = [
                        r'["\']([^"\']*campo[^"\']*obbligatorio[^"\']*)["\']',
                        r'["\']([^"\']*required[^"\']*)["\']',
                        r'["\']([^"\']*formato[^"\']*non[^"\']*valido[^"\']*)["\']',
                    ]
                    
                    for pattern in error_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE)
                        js_validation["error_messages"].extend(matches)
            
            self.form_analysis["validation_rules"]["javascript"] = js_validation
            
        except Exception as e:
            self.logger.warning(f"Could not extract JavaScript validation: {e}")
    
    def _identify_field_requirements(self, html_content: str):
        """Identify which fields are required vs optional."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            inputs = soup.find_all(['input', 'select', 'textarea'])
            
            required_fields = []
            optional_fields = []
            
            for input_field in inputs:
                field_name = input_field.get('name', input_field.get('id', 'unknown'))
                
                if field_name == 'unknown':
                    continue
                
                # Check if field is required
                is_required = (
                    input_field.has_attr('required') or
                    'required' in str(input_field.get('class', [])).lower() or
                    '*' in str(input_field.parent).replace(str(input_field), '') if input_field.parent else False
                )
                
                if is_required:
                    required_fields.append(field_name)
                else:
                    optional_fields.append(field_name)
            
            self.form_analysis["required_fields"] = required_fields
            self.form_analysis["optional_fields"] = optional_fields
            
            self.logger.info(f"Identified {len(required_fields)} required fields and {len(optional_fields)} optional fields")
            
        except Exception as e:
            error_msg = f"Error identifying field requirements: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _create_field_mappings(self):
        """Create mappings between field names and their purposes."""
        try:
            field_mappings = {}
            
            # Common field mapping patterns
            mapping_patterns = {
                'parola_chiave': ['txtOggetto', 'oggetto', 'keyword', 'search', 'query'],
                'anno': ['txtAnno', 'anno', 'year'],
                'tipo_atto': ['txtTipoAtto', 'tipo', 'type', 'atto'],
                'numero': ['txtNumero', 'numero', 'number', 'n'],
                'soggetto_emanante': ['txtSoggettoEmanante', 'soggetto', 'emanante', 'issuer'],
                'data_sottoscrizione': ['DataSottoscrizione', 'data_sottoscrizione', 'subscription_date'],
                'data_pubblicazione': ['DataPubblicazione', 'data_pubblicazione', 'publication_date'],
                'materia': ['txtMateria', 'materia', 'subject', 'matter'],
                'argomento': ['txtArgomento', 'argomento', 'topic', 'argument'],
                'area_tematica': ['area_tematica', 'area', 'theme', 'category']
            }
            
            # Map actual field names to purposes
            for form_name, form_data in self.form_analysis["form_fields"].items():
                for field in form_data["fields"]:
                    field_name = field["name"]
                    if not field_name:
                        continue
                    
                    for purpose, patterns in mapping_patterns.items():
                        if any(pattern.lower() in field_name.lower() for pattern in patterns):
                            field_mappings[purpose] = {
                                "html_name": field_name,
                                "html_id": field["id"],
                                "field_type": field["type"],
                                "tag": field["tag"],
                                "required": field["required"]
                            }
                            break
            
            self.form_analysis["field_mappings"] = field_mappings
            
            self.logger.info(f"Created mappings for {len(field_mappings)} field purposes")
            
        except Exception as e:
            error_msg = f"Error creating field mappings: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _extract_dynamic_dropdown_options(self, html_content: str):
        """Extract options for dropdowns that are populated dynamically."""
        try:
            self.logger.info("Attempting to extract dynamic dropdown options...")
            
            # Look for JavaScript that populates dropdowns
            soup = BeautifulSoup(html_content, 'html.parser')
            scripts = soup.find_all('script')
            
            # Common endpoints for dropdown data
            ajax_endpoints = [
                '/components/com_lddocs/ajax/getTipoAtto.php',
                '/components/com_lddocs/ajax/getMaterie.php', 
                '/components/com_lddocs/ajax/getArgomenti.php',
                '/ajax/dropdown_options.php',
                '/api/dropdown_data.php'
            ]
            
            # Try to find AJAX endpoints in JavaScript
            for script in scripts:
                if script.string:
                    js_content = script.string
                    
                    # Look for AJAX calls
                    ajax_patterns = [
                        r'url[\s]*:[\s]*["\']([^"\']*)["\']',
                        r'\$\.get\(["\']([^"\']*)["\']',
                        r'\$\.post\(["\']([^"\']*)["\']',
                        r'fetch\(["\']([^"\']*)["\']'
                    ]
                    
                    for pattern in ajax_patterns:
                        matches = re.findall(pattern, js_content)
                        for match in matches:
                            if any(keyword in match.lower() for keyword in 
                                   ['tipo', 'atto', 'materia', 'argomento', 'dropdown']):
                                ajax_endpoints.append(match)
            
            # Try each potential endpoint
            for endpoint in set(ajax_endpoints):  # Remove duplicates
                try:
                    self._fetch_dropdown_data(endpoint)
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    self.logger.debug(f"Could not fetch dropdown data from {endpoint}: {e}")
                    continue
            
            # Try alternative approaches
            self._try_javascript_execution(html_content)
            
        except Exception as e:
            error_msg = f"Error extracting dynamic dropdown options: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _fetch_dropdown_data(self, endpoint: str):
        """Fetch dropdown data from AJAX endpoint."""
        try:
            if not endpoint.startswith('http'):
                if endpoint.startswith('/'):
                    url = f"{self.base_url}{endpoint}"
                else:
                    url = f"{self.base_url}/{endpoint}"
            else:
                url = endpoint
            
            self.logger.debug(f"Trying dropdown endpoint: {url}")
            
            # Try with different request types
            for method in ['GET', 'POST']:
                try:
                    if method == 'GET':
                        response = self.session.get(url, timeout=10)
                    else:
                        response = self.session.post(url, timeout=10)
                    
                    if response.status_code == 200:
                        self._parse_dropdown_response(endpoint, response)
                        break
                        
                except Exception as e:
                    self.logger.debug(f"{method} request to {url} failed: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Failed to fetch dropdown data from {endpoint}: {e}")
    
    def _parse_dropdown_response(self, endpoint: str, response: requests.Response):
        """Parse response from dropdown endpoint."""
        try:
            content_type = response.headers.get('content-type', '').lower()
            
            if 'json' in content_type:
                # JSON response
                data = response.json()
                self.form_analysis["dynamic_dropdown_options"][endpoint] = {
                    "type": "json",
                    "data": data,
                    "options_count": len(data) if isinstance(data, list) else 0
                }
                self.logger.info(f"Found JSON dropdown data at {endpoint}: {len(data) if isinstance(data, list) else 'object'}")
                
            elif 'html' in content_type:
                # HTML response - might contain select options
                soup = BeautifulSoup(response.text, 'html.parser')
                options = soup.find_all('option')
                
                if options:
                    option_data = []
                    for option in options:
                        option_data.append({
                            "value": option.get('value', ''),
                            "text": option.get_text(strip=True)
                        })
                    
                    self.form_analysis["dynamic_dropdown_options"][endpoint] = {
                        "type": "html_options",
                        "data": option_data,
                        "options_count": len(option_data)
                    }
                    self.logger.info(f"Found HTML dropdown options at {endpoint}: {len(option_data)} options")
                    
            else:
                # Try to parse as plain text
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    self.form_analysis["dynamic_dropdown_options"][endpoint] = {
                        "type": "text_lines",
                        "data": lines,
                        "options_count": len(lines)
                    }
                    self.logger.info(f"Found text dropdown data at {endpoint}: {len(lines)} lines")
                    
        except Exception as e:
            self.logger.debug(f"Could not parse dropdown response from {endpoint}: {e}")
    
    def _try_javascript_execution(self, html_content: str):
        """Try to understand JavaScript dropdown population logic."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            scripts = soup.find_all('script')
            
            js_analysis = {
                "dropdown_functions": [],
                "ajax_calls": [],
                "option_arrays": []
            }
            
            for script in scripts:
                if script.string:
                    js_content = script.string
                    
                    # Look for functions that populate dropdowns
                    function_patterns = [
                        r'function\s+(\w*[Dd]ropdown\w*|\w*[Pp]opulate\w*)\s*\(',
                        r'function\s+(\w*[Oo]ption\w*)\s*\(',
                        r'(\w+)\s*=\s*function.*dropdown',
                    ]
                    
                    for pattern in function_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE)
                        js_analysis["dropdown_functions"].extend(matches)
                    
                    # Look for option arrays or objects
                    array_patterns = [
                        r'var\s+(\w+)\s*=\s*\[.*?\]',
                        r'(\w+)\s*=\s*\{[^}]*option[^}]*\}',
                        r'options\s*:\s*\[([^\]]+)\]'
                    ]
                    
                    for pattern in array_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE | re.DOTALL)
                        js_analysis["option_arrays"].extend(matches)
                    
                    # Look for AJAX calls
                    ajax_patterns = [
                        r'\$\.ajax\s*\(\s*\{[^}]*url[^}]*\}',
                        r'\$\.(get|post)\s*\([^)]+\)',
                        r'fetch\s*\([^)]+\)'
                    ]
                    
                    for pattern in ajax_patterns:
                        matches = re.findall(pattern, js_content, re.IGNORECASE)
                        js_analysis["ajax_calls"].extend(matches)
            
            if any(js_analysis.values()):
                self.form_analysis["dynamic_dropdown_options"]["javascript_analysis"] = js_analysis
                self.logger.info(f"Found JavaScript dropdown logic: {len(js_analysis['dropdown_functions'])} functions, {len(js_analysis['ajax_calls'])} AJAX calls")
                
        except Exception as e:
            self.logger.debug(f"JavaScript analysis failed: {e}")
    
    def _analyze_search_types(self, html_content: str):
        """Analyze the different search types available (chkSearchType radio buttons)."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find radio buttons for search type
            search_type_radios = soup.find_all('input', {'name': 'chkSearchType'})
            
            search_types = {}
            
            for radio in search_type_radios:
                value = radio.get('value', '')
                radio_id = radio.get('id', '')
                
                # Look for labels or nearby text
                label_text = ''
                
                # Try to find associated label
                if radio_id:
                    label = soup.find('label', {'for': radio_id})
                    if label:
                        label_text = label.get_text(strip=True)
                
                # If no label found, look at parent or nearby elements
                if not label_text and radio.parent:
                    parent_text = radio.parent.get_text(strip=True)
                    # Extract relevant text around the radio button
                    words = parent_text.split()
                    radio_index = -1
                    for i, word in enumerate(words):
                        if 'radio' in word.lower() or value in word:
                            radio_index = i
                            break
                    
                    if radio_index >= 0:
                        # Get surrounding words
                        start = max(0, radio_index - 3)
                        end = min(len(words), radio_index + 4)
                        label_text = ' '.join(words[start:end])
                
                search_types[value] = {
                    "value": value,
                    "id": radio_id,
                    "label": label_text,
                    "description": self._infer_search_type_description(value, label_text)
                }
            
            self.form_analysis["search_types"] = search_types
            self.logger.info(f"Found {len(search_types)} search type options")
            
        except Exception as e:
            error_msg = f"Error analyzing search types: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
    
    def _infer_search_type_description(self, value: str, label_text: str) -> str:
        """Infer what each search type does based on value and context."""
        descriptions = {
            "0": "Ricerca semplice/base",
            "1": "Ricerca avanzata/dettagliata", 
            "2": "Ricerca per testo libero"
        }
        
        # Try to infer from label text
        if label_text:
            label_lower = label_text.lower()
            if any(word in label_lower for word in ['semplice', 'base', 'normale']):
                return "Ricerca semplice"
            elif any(word in label_lower for word in ['avanzata', 'dettagliata', 'completa']):
                return "Ricerca avanzata"
            elif any(word in label_lower for word in ['testo', 'libero', 'parole']):
                return "Ricerca per testo libero"
        
        return descriptions.get(value, f"Modalità ricerca {value}")
    
    def save_analysis(self, output_file: str = "logs/form_analysis.json") -> bool:
        """Save analysis results to JSON file.
        
        Args:
            output_file: Path to output file
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure output directory exists
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save analysis results
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.form_analysis, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Analysis results saved to {output_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to save analysis results: {e}"
            self.logger.error(error_msg)
            self.form_analysis["errors"].append(error_msg)
            return False
    
    def print_summary(self):
        """Print a summary of the analysis results."""
        print("\n" + "="*60)
        print("FORM ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"\nBase URL: {self.form_analysis['base_url']}")
        print(f"Analysis Date: {self.form_analysis['analysis_timestamp']}")
        
        # Form structure summary
        print(f"\nFORMS FOUND: {len(self.form_analysis['form_fields'])}")
        for form_name, form_data in self.form_analysis['form_fields'].items():
            print(f"  {form_name}: {form_data['method']} -> {form_data['action']}")
            print(f"    Fields: {len(form_data['fields'])}")
        
        # Dropdown options summary
        print(f"\nSTATIC DROPDOWN FIELDS: {len(self.form_analysis['dropdown_options'])}")
        for field_name, field_data in self.form_analysis['dropdown_options'].items():
            print(f"  {field_name}: {len(field_data['options'])} options")
            # Show first few options for important fields
            if any(keyword in field_name.lower() for keyword in ['tipo', 'atto', 'materia', 'argomento']):
                for i, option in enumerate(field_data['options'][:5]):
                    if option['text'].strip():
                        print(f"    - {option['text']} ({option['value']})")
                if len(field_data['options']) > 5:
                    print(f"    ... and {len(field_data['options']) - 5} more")
        
        # Dynamic dropdown options summary
        if self.form_analysis['dynamic_dropdown_options']:
            print(f"\nDYNAMIC DROPDOWN DATA: {len(self.form_analysis['dynamic_dropdown_options'])}")
            for endpoint, data in self.form_analysis['dynamic_dropdown_options'].items():
                if endpoint == 'javascript_analysis':
                    js_data = data
                    print(f"  JavaScript Analysis:")
                    print(f"    - Functions: {len(js_data.get('dropdown_functions', []))}")
                    print(f"    - AJAX calls: {len(js_data.get('ajax_calls', []))}")
                    print(f"    - Option arrays: {len(js_data.get('option_arrays', []))}")
                else:
                    print(f"  {endpoint}: {data.get('options_count', 0)} options ({data.get('type', 'unknown')})")
                    if data.get('type') == 'json' and isinstance(data.get('data'), list):
                        for item in data['data'][:3]:  # Show first 3 items
                            print(f"    - {item}")
                        if len(data['data']) > 3:
                            print(f"    ... and {len(data['data']) - 3} more")
        
        # Search types summary
        if self.form_analysis['search_types']:
            print(f"\nSEARCH TYPES: {len(self.form_analysis['search_types'])}")
            for value, search_type in self.form_analysis['search_types'].items():
                print(f"  Type {value}: {search_type['description']}")
                if search_type['label']:
                    print(f"    Label: {search_type['label']}")
        
        # Field requirements
        print(f"\nFIELD REQUIREMENTS:")
        print(f"  Required fields: {len(self.form_analysis['required_fields'])}")
        for field in self.form_analysis['required_fields']:
            print(f"    - {field}")
        print(f"  Optional fields: {len(self.form_analysis['optional_fields'])}")
        
        # Field mappings
        print(f"\nFIELD MAPPINGS: {len(self.form_analysis['field_mappings'])}")
        for purpose, mapping in self.form_analysis['field_mappings'].items():
            print(f"  {purpose}: {mapping['html_name']} ({mapping['field_type']})")
        
        # Validation rules summary
        date_fields = []
        year_fields = []
        for field_name, rules in self.form_analysis['validation_rules'].items():
            if rules.get('date_field'):
                date_fields.append((field_name, rules.get('likely_format', 'Unknown')))
            if rules.get('year_field'):
                year_range = rules.get('likely_range', {})
                year_fields.append((field_name, f"{year_range.get('min', '?')}-{year_range.get('max', '?')}"))
        
        if date_fields:
            print(f"\nDATE FIELDS:")
            for field, format_type in date_fields:
                print(f"  {field}: {format_type}")
        
        if year_fields:
            print(f"\nYEAR FIELDS:")
            for field, year_range in year_fields:
                print(f"  {field}: {year_range}")
        
        # Errors
        if self.form_analysis['errors']:
            print(f"\nERRORS: {len(self.form_analysis['errors'])}")
            for error in self.form_analysis['errors']:
                print(f"  - {error}")
        else:
            print(f"\nANALYSIS COMPLETED SUCCESSFULLY ✓")
        
        print("="*60)


def main():
    """Main function to run form analysis."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting form analysis...")
    
    try:
        # Create analyzer
        analyzer = FormAnalyzer(
            verify_ssl=False,  # Use unverified SSL to avoid connection issues
            allow_unverified_ssl=True
        )
        
        # Perform analysis
        results = analyzer.analyze_form()
        
        # Save results
        analyzer.save_analysis()
        
        # Print summary
        analyzer.print_summary()
        
        logger.info("Form analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Form analysis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
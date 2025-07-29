"""
Decreto Scraper Advanced - Form Scraping Automatico
Sistema avanzato per il scraping automatico del sito decretidigitali.regione.liguria.it

Caratteristiche principali:
- Analisi automatica della struttura dei form
- Estrazione dinamica delle opzioni dropdown
- Auto-fill intelligente dei campi
- Parsing avanzato dei risultati
- Gestione errori e retry automatici
- Sistema di confidence scoring
"""

import logging
import requests
import time
from typing import Tuple, Optional, Dict, Any, Union, List
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from pathlib import Path
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import difflib
import urllib3
from contextlib import contextmanager


# Disable SSL warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DecretoScraperError(Exception):
    """Base exception for decreto scraper errors."""
    pass


class DecretoFormAnalysisError(DecretoScraperError):
    """Raised when form analysis fails."""
    pass


class DecretoFieldMappingError(DecretoScraperError):
    """Raised when field mapping fails."""
    pass


class DecretoSubmissionError(DecretoScraperError):
    """Raised when form submission fails."""
    pass


class DecretoParsingError(DecretoScraperError):
    """Raised when result parsing fails."""
    pass


class LogLevel(Enum):
    """Logging levels for decreto scraper."""
    SILENT = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


@dataclass
class FormField:
    """Rappresenta un campo del form."""
    name: str
    field_type: str  # select, input, textarea, etc.
    required: bool = False
    options: Dict[str, str] = field(default_factory=dict)  # value -> label
    default_value: Optional[str] = None
    placeholder: Optional[str] = None


@dataclass
class FormStructure:
    """Struttura completa del form analizzato."""
    action_url: str
    method: str = "GET"
    fields: Dict[str, FormField] = field(default_factory=dict)
    hidden_fields: Dict[str, str] = field(default_factory=dict)
    csrf_token: Optional[str] = None


@dataclass
class SearchResult:
    """Risultato di una ricerca."""
    title: str
    url: str
    date: Optional[str] = None
    document_type: Optional[str] = None
    number: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class SearchParameters:
    """Parametri per la ricerca."""
    seduta: str
    numero: str
    oggetto: str
    anno: Optional[str] = None
    data_sottoscrizione: Optional[str] = None
    tipo_atto: Optional[str] = None


class DecretoScraperAdvanced:
    """
    Scraper avanzato per decreto digitali con form scraping automatico.
    
    Caratteristiche:
    - Analisi automatica form structure
    - Selezione intelligente valori dropdown
    - Auto-fill e submission automatica
    - Parsing avanzato risultati con confidence scoring
    """

    def __init__(
        self,
        base_url: str = "https://decretidigitali.regione.liguria.it",
        search_endpoint: str = "/",
        rate_limit: float = 2.0,
        max_retries: int = 3,
        timeout: int = 30,
        verify_ssl: bool = True,
        debug_mode: bool = False,
        log_level: LogLevel = LogLevel.INFO,
        user_agents: Optional[List[str]] = None,
    ):
        """
        Inizializza il decreto scraper avanzato.
        
        Args:
            base_url: URL base del sito decreto
            search_endpoint: Endpoint per la ricerca
            rate_limit: Secondi tra le richieste
            max_retries: Numero massimo di retry
            timeout: Timeout richieste in secondi
            verify_ssl: Verifica certificati SSL
            debug_mode: Modalità debug dettagliata
            log_level: Livello di logging
            user_agents: Lista user agents per rotation
        """
        self.base_url = base_url.rstrip('/')
        self.search_endpoint = search_endpoint
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.debug_mode = debug_mode
        self.log_level = log_level
        
        # Setup logging
        self._setup_logging()
        
        # Setup session with browser-like headers
        self.session = self._create_session()
        
        # User agents for rotation
        self.user_agents = user_agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        
        # Cache per form structure
        self.form_structure: Optional[FormStructure] = None
        self.form_analysis_timestamp: Optional[datetime] = None
        self.form_cache_duration = timedelta(hours=1)  # Cache per 1 ora
        
        # Performance metrics
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        self.logger.info(f"DecretoScraperAdvanced initialized - Base URL: {self.base_url}")

    def _setup_logging(self):
        """Setup sistema di logging."""
        self.logger = logging.getLogger(f"{__name__}.DecretoScraperAdvanced")
        
        if self.log_level == LogLevel.SILENT:
            self.logger.setLevel(logging.CRITICAL + 1000)
        elif self.log_level == LogLevel.ERROR:
            self.logger.setLevel(logging.ERROR)
        elif self.log_level == LogLevel.WARN:
            self.logger.setLevel(logging.WARNING)
        elif self.log_level == LogLevel.INFO:
            self.logger.setLevel(logging.INFO)
        elif self.log_level == LogLevel.DEBUG:
            self.logger.setLevel(logging.DEBUG)
        elif self.log_level == LogLevel.TRACE:
            self.logger.setLevel(5)  # Custom trace level
            
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _create_session(self) -> requests.Session:
        """Crea sessione HTTP con configurazione ottimizzata."""
        session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers browser-like
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        
        return session

    def _rotate_user_agent(self):
        """Ruota user agent per evitare detection."""
        import random
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({'User-Agent': user_agent})
        self.logger.debug(f"Rotated user agent: {user_agent[:50]}...")

    def _make_request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """
        Esegue richiesta HTTP con gestione errori e rate limiting.
        
        Args:
            url: URL da richiedere
            method: Metodo HTTP
            **kwargs: Parametri aggiuntivi per requests
            
        Returns:
            Response object
            
        Raises:
            DecretoScraperError: Per errori di connessione
        """
        self._rotate_user_agent()
        
        # Rate limiting
        if hasattr(self, '_last_request_time'):
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self._last_request_time = time.time()
        
        # Default parameters
        params = {
            'timeout': self.timeout,
            'verify': self.verify_ssl,
        }
        params.update(kwargs)
        
        try:
            self.request_count += 1
            start_time = time.time()
            
            if method.upper() == "GET":
                response = self.session.get(url, **params)
            elif method.upper() == "POST":
                response = self.session.post(url, **params)
            else:
                raise DecretoScraperError(f"Unsupported HTTP method: {method}")
            
            response_time = time.time() - start_time
            self.total_response_time += response_time
            
            response.raise_for_status()
            self.success_count += 1
            
            self.logger.debug(f"Request successful: {method} {url} - {response.status_code} - {response_time:.2f}s")
            return response
            
        except requests.exceptions.SSLError as e:
            self.error_count += 1
            self.logger.error(f"SSL error for {url}: {e}")
            raise DecretoScraperError(f"SSL verification failed: {e}")
            
        except requests.exceptions.ConnectionError as e:
            self.error_count += 1
            self.logger.error(f"Connection error for {url}: {e}")
            raise DecretoScraperError(f"Connection failed: {e}")
            
        except requests.exceptions.Timeout as e:
            self.error_count += 1
            self.logger.error(f"Timeout error for {url}: {e}")
            raise DecretoScraperError(f"Request timeout: {e}")
            
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            self.logger.error(f"Request error for {url}: {e}")
            raise DecretoScraperError(f"Request failed: {e}")

    def analyze_form_structure(self, force_refresh: bool = False) -> FormStructure:
        """
        Analizza struttura completa del form di ricerca.
        
        Args:
            force_refresh: Forza refresh del cache
            
        Returns:
            FormStructure object con tutti i campi analizzati
            
        Raises:
            DecretoFormAnalysisError: Se analisi form fallisce
        """
        # Check cache
        if (not force_refresh and 
            self.form_structure and 
            self.form_analysis_timestamp and
            datetime.now() - self.form_analysis_timestamp < self.form_cache_duration):
            self.logger.debug("Using cached form structure")
            return self.form_structure
        
        self.logger.info("Analyzing form structure...")
        
        try:
            # GET della pagina principale
            search_url = urljoin(self.base_url, self.search_endpoint)
            response = self._make_request(search_url)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trova il form di ricerca
            form = self._find_search_form(soup)
            if not form:
                raise DecretoFormAnalysisError("Could not find search form on page")
            
            # Estrai action e method
            action = form.get('action', '')
            if action and not action.startswith('http'):
                action = urljoin(search_url, action)
            method = form.get('method', 'GET').upper()
            
            form_structure = FormStructure(action_url=action, method=method)
            
            # Analizza tutti i campi del form
            self._analyze_form_fields(form, form_structure)
            
            # Cache del risultato
            self.form_structure = form_structure
            self.form_analysis_timestamp = datetime.now()
            
            self.logger.info(f"Form analysis complete - {len(form_structure.fields)} fields found")
            if self.debug_mode:
                self._log_form_structure(form_structure)
            
            return form_structure
            
        except Exception as e:
            self.logger.error(f"Form analysis failed: {e}")
            raise DecretoFormAnalysisError(f"Failed to analyze form structure: {e}")

    def _find_search_form(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """
        Trova il form di ricerca nella pagina.
        
        Args:
            soup: BeautifulSoup object della pagina
            
        Returns:
            Form element o None se non trovato
        """
        # Cerca form con parole chiave nella classe o id
        keywords = ['ricerca', 'search', 'form', 'decreto']
        
        for keyword in keywords:
            # Cerca per class
            form = soup.find('form', class_=lambda x: x and keyword.lower() in x.lower())
            if form:
                self.logger.debug(f"Found form by class containing '{keyword}'")
                return form
            
            # Cerca per id
            form = soup.find('form', id=lambda x: x and keyword.lower() in x.lower())
            if form:
                self.logger.debug(f"Found form by id containing '{keyword}'")
                return form
        
        # Fallback: prendi il primo form con campi select
        forms = soup.find_all('form')
        for form in forms:
            if form.find('select'):
                self.logger.debug("Found form with select elements")
                return form
        
        # Ultimo fallback: primo form nella pagina
        if forms:
            self.logger.debug("Using first form found on page")
            return forms[0]
        
        return None

    def _analyze_form_fields(self, form: BeautifulSoup, form_structure: FormStructure):
        """
        Analizza tutti i campi del form.
        
        Args:
            form: Form element da analizzare
            form_structure: Struttura form da popolare
        """
        # Analizza campi select (dropdown)
        for select in form.find_all('select'):
            field = self._analyze_select_field(select)
            if field:
                form_structure.fields[field.name] = field
        
        # Analizza campi input
        for input_elem in form.find_all('input'):
            field = self._analyze_input_field(input_elem, form_structure)
            if field:
                form_structure.fields[field.name] = field
        
        # Analizza textarea
        for textarea in form.find_all('textarea'):
            field = self._analyze_textarea_field(textarea)
            if field:
                form_structure.fields[field.name] = field

    def _analyze_select_field(self, select: BeautifulSoup) -> Optional[FormField]:
        """
        Analizza un campo select.
        
        Args:
            select: Select element
            
        Returns:
            FormField object o None
        """
        name = select.get('name')
        if not name:
            return None
        
        field = FormField(
            name=name,
            field_type='select',
            required=select.has_attr('required')
        )
        
        # Estrai opzioni
        field.options = self.extract_dropdown_options(select)
        
        # Default value
        selected_option = select.find('option', selected=True)
        if selected_option:
            field.default_value = selected_option.get('value', '')
        
        self.logger.debug(f"Analyzed select field '{name}' with {len(field.options)} options")
        return field

    def _analyze_input_field(self, input_elem: BeautifulSoup, form_structure: FormStructure) -> Optional[FormField]:
        """
        Analizza un campo input.
        
        Args:
            input_elem: Input element
            form_structure: Struttura form per campi hidden
            
        Returns:
            FormField object o None
        """
        name = input_elem.get('name')
        if not name:
            return None
        
        input_type = input_elem.get('type', 'text').lower()
        
        # Gestisci campi hidden separatamente
        if input_type == 'hidden':
            value = input_elem.get('value', '')
            form_structure.hidden_fields[name] = value
            
            # Check for CSRF token
            if 'csrf' in name.lower() or 'token' in name.lower():
                form_structure.csrf_token = value
            
            return None
        
        # Skip submit/button inputs
        if input_type in ['submit', 'button', 'reset']:
            return None
        
        field = FormField(
            name=name,
            field_type=input_type,
            required=input_elem.has_attr('required'),
            default_value=input_elem.get('value', ''),
            placeholder=input_elem.get('placeholder', '')
        )
        
        self.logger.debug(f"Analyzed input field '{name}' type '{input_type}'")
        return field

    def _analyze_textarea_field(self, textarea: BeautifulSoup) -> Optional[FormField]:
        """
        Analizza un campo textarea.
        
        Args:
            textarea: Textarea element
            
        Returns:
            FormField object o None
        """
        name = textarea.get('name')
        if not name:
            return None
        
        field = FormField(
            name=name,
            field_type='textarea',
            required=textarea.has_attr('required'),
            default_value=textarea.get_text(strip=True),
            placeholder=textarea.get('placeholder', '')
        )
        
        self.logger.debug(f"Analyzed textarea field '{name}'")
        return field

    def extract_dropdown_options(self, select_element: BeautifulSoup) -> Dict[str, str]:
        """
        Estrae opzioni da un dropdown.
        
        Args:
            select_element: Select element da analizzare
            
        Returns:
            Dict con mapping value -> label
        """
        options = {}
        
        for option in select_element.find_all('option'):
            value = option.get('value', '')
            label = option.get_text(strip=True) or value
            
            # Skip opzioni vuote o di default
            if value and value != '' and label.lower() not in ['seleziona', 'choose', 'select', '---']:
                options[value] = label
        
        return options

    def smart_field_selection(self, field_name: str, search_params: SearchParameters, form_structure: FormStructure) -> Optional[str]:
        """
        Selezione intelligente valori dropdown basata sui parametri di ricerca.
        
        Args:
            field_name: Nome del campo
            search_params: Parametri ricerca
            form_structure: Struttura form
            
        Returns:
            Valore selezionato o None
        """
        if field_name not in form_structure.fields:
            return None
        
        field = form_structure.fields[field_name]
        if field.field_type != 'select' or not field.options:
            return None
        
        field_lower = field_name.lower()
        
        # Selezione per anno
        if 'anno' in field_lower or 'year' in field_lower:
            target_year = search_params.anno or "2025"
            return self._find_best_match_in_options(target_year, field.options)
        
        # Selezione per tipo atto
        if any(keyword in field_lower for keyword in ['tipo', 'atto', 'type']):
            targets = ['deliberazione', 'delibera', 'decree', 'resolution']
            for target in targets:
                match = self._find_best_match_in_options(target, field.options)
                if match:
                    return match
        
        # Selezione per area tematica/materia
        if any(keyword in field_lower for keyword in ['area', 'tematica', 'materia', 'subject', 'category']):
            # Usa parole chiave dall'oggetto
            oggetto_words = search_params.oggetto.lower().split()
            for word in oggetto_words:
                if len(word) > 3:  # Solo parole significative
                    match = self._find_best_match_in_options(word, field.options)
                    if match:
                        return match
        
        # Selezione per numero
        if 'numero' in field_lower or 'number' in field_lower:
            return self._find_best_match_in_options(search_params.numero, field.options)
        
        # Default: prima opzione non vuota
        for value, label in field.options.items():
            if value and value.strip():
                self.logger.debug(f"Using default option for {field_name}: {value} ({label})")
                return value
        
        return None

    def _find_best_match_in_options(self, target: str, options: Dict[str, str]) -> Optional[str]:
        """
        Trova il miglior match per target nelle opzioni disponibili.
        
        Args:
            target: Valore target da cercare
            options: Dict value -> label delle opzioni
            
        Returns:
            Valore migliore match o None
        """
        target_lower = target.lower()
        
        # Exact match nel value
        for value, label in options.items():
            if value.lower() == target_lower:
                self.logger.debug(f"Exact value match: {target} -> {value}")
                return value
        
        # Exact match nel label
        for value, label in options.items():
            if label.lower() == target_lower:
                self.logger.debug(f"Exact label match: {target} -> {label} ({value})")
                return value
        
        # Substring match nel label
        for value, label in options.items():
            if target_lower in label.lower() or label.lower() in target_lower:
                self.logger.debug(f"Substring match: {target} -> {label} ({value})")
                return value
        
        # Fuzzy matching usando difflib
        best_ratio = 0.0
        best_match = None
        
        for value, label in options.items():
            # Match con label
            ratio = difflib.SequenceMatcher(None, target_lower, label.lower()).ratio()
            if ratio > best_ratio and ratio > 0.6:  # Soglia minima 60%
                best_ratio = ratio
                best_match = value
            
            # Match con value
            ratio = difflib.SequenceMatcher(None, target_lower, value.lower()).ratio()
            if ratio > best_ratio and ratio > 0.6:
                best_ratio = ratio
                best_match = value
        
        if best_match:
            label = options[best_match]
            self.logger.debug(f"Fuzzy match: {target} -> {label} ({best_match}) [ratio: {best_ratio:.2f}]")
        
        return best_match

    def build_form_data(self, search_params: SearchParameters) -> Dict[str, str]:
        """
        Costruisce form data per POST basato sui parametri di ricerca.
        
        Args:
            search_params: Parametri ricerca
            
        Returns:
            Dict con form data per submission
            
        Raises:
            DecretoFieldMappingError: Se mapping campi fallisce
        """
        if not self.form_structure:
            raise DecretoFieldMappingError("Form structure not analyzed")
        
        form_data = {}
        
        # Aggiungi campi hidden
        form_data.update(self.form_structure.hidden_fields)
        
        # Mappa campi con selezione intelligente
        for field_name, field in self.form_structure.fields.items():
            value = None
            
            if field.field_type == 'select':
                value = self.smart_field_selection(field_name, search_params, self.form_structure)
            
            elif field.field_type in ['text', 'search']:
                # Campi di testo - mapping basato su nome campo
                field_lower = field_name.lower()
                
                if 'oggetto' in field_lower or 'title' in field_lower or 'subject' in field_lower:
                    value = search_params.oggetto
                elif 'numero' in field_lower and 'number' in field_lower:
                    value = search_params.numero
                elif 'data' in field_lower or 'date' in field_lower:
                    value = search_params.data_sottoscrizione
            
            # Usa valore di default se nessun valore specifico
            if value is None:
                value = field.default_value or ''
            
            form_data[field_name] = str(value) if value is not None else ''
            
            if value:
                self.logger.debug(f"Mapped field {field_name}: {value}")
        
        self.logger.info(f"Built form data with {len(form_data)} fields")
        return form_data

    def submit_search_form(self, form_data: Dict[str, str]) -> requests.Response:
        """
        Invia form di ricerca.
        
        Args:
            form_data: Dati form da inviare
            
        Returns:
            Response della ricerca
            
        Raises:
            DecretoSubmissionError: Se submission fallisce
        """
        if not self.form_structure:
            raise DecretoSubmissionError("Form structure not available")
        
        try:
            url = self.form_structure.action_url or urljoin(self.base_url, self.search_endpoint)
            method = self.form_structure.method
            
            self.logger.info(f"Submitting form to {url} via {method}")
            
            if method == "GET":
                response = self._make_request(url, method="GET", params=form_data)
            else:
                response = self._make_request(url, method="POST", data=form_data)
            
            self.logger.info(f"Form submission successful - Status: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"Form submission failed: {e}")
            raise DecretoSubmissionError(f"Failed to submit search form: {e}")

    def parse_search_results(self, html_response: str, search_params: SearchParameters) -> List[SearchResult]:
        """
        Parse risultati ricerca con confidence scoring.
        
        Args:
            html_response: HTML response della ricerca
            search_params: Parametri ricerca originali
            
        Returns:
            Lista SearchResult ordinata per confidence score
            
        Raises:
            DecretoParsingError: Se parsing fallisce
        """
        try:
            soup = BeautifulSoup(html_response, 'html.parser')
            results = []
            
            # Strategie multiple per trovare risultati
            result_containers = self._find_result_containers(soup)
            
            for container in result_containers:
                result = self._parse_single_result(container, search_params)
                if result:
                    results.append(result)
            
            # Ordina per confidence score
            results.sort(key=lambda x: x.confidence_score, reverse=True)
            
            self.logger.info(f"Parsed {len(results)} search results")
            return results
            
        except Exception as e:
            self.logger.error(f"Result parsing failed: {e}")
            raise DecretoParsingError(f"Failed to parse search results: {e}")

    def _find_result_containers(self, soup: BeautifulSoup) -> List[BeautifulSoup]:
        """
        Trova containers dei risultati nella pagina.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Lista di containers risultati
        """
        containers = []
        
        # Strategie multiple per trovare risultati
        selectors = [
            'div.result',
            'div.search-result',
            'tr',  # Tabella
            'li',  # Lista
            'div[class*="item"]',
            'div[class*="record"]',
        ]
        
        for selector in selectors:
            found = soup.select(selector)
            if found:
                self.logger.debug(f"Found {len(found)} results with selector: {selector}")
                containers.extend(found)
                break
        
        return containers

    def _parse_single_result(self, container: BeautifulSoup, search_params: SearchParameters) -> Optional[SearchResult]:
        """
        Parse un singolo risultato.
        
        Args:
            container: Container del risultato
            search_params: Parametri ricerca per confidence scoring
            
        Returns:
            SearchResult o None
        """
        # Estrai titolo
        title = self._extract_title(container)
        if not title:
            return None
        
        # Estrai URL
        url = self._extract_url(container)
        
        # Estrai altri campi
        date = self._extract_date(container)
        document_type = self._extract_document_type(container)
        number = self._extract_number(container)
        description = self._extract_description(container)
        
        # Calcola confidence score
        confidence_score = self._calculate_confidence_score(
            title, search_params, date, document_type, number, description
        )
        
        result = SearchResult(
            title=title,
            url=url or '',
            date=date,
            document_type=document_type,
            number=number,
            description=description,
            confidence_score=confidence_score
        )
        
        self.logger.debug(f"Parsed result: {title[:50]}... (confidence: {confidence_score:.2f})")
        return result

    def _extract_title(self, container: BeautifulSoup) -> Optional[str]:
        """Estrae titolo dal container."""
        # Strategie multiple per titolo
        selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.subject', 'a', 'strong', 'b']
        
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 10:  # Titolo significativo
                    return title
        
        # Fallback: tutto il testo del container
        text = container.get_text(strip=True)
        if text and len(text) > 10:
            return text[:200] + ('...' if len(text) > 200 else '')
        
        return None

    def _extract_url(self, container: BeautifulSoup) -> Optional[str]:
        """Estrae URL dal container."""
        # Cerca link nel container
        link = container.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('http'):
                return href
            else:
                return urljoin(self.base_url, href)
        
        return None

    def _extract_date(self, container: BeautifulSoup) -> Optional[str]:
        """Estrae data dal container."""
        text = container.get_text()
        
        # Pattern per date italiane
        date_patterns = [
            r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b',  # dd/mm/yyyy
            r'\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b',  # yyyy/mm/dd
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None

    def _extract_document_type(self, container: BeautifulSoup) -> Optional[str]:
        """Estrae tipo documento dal container."""
        text = container.get_text().lower()
        
        types = ['deliberazione', 'delibera', 'decreto', 'ordinanza', 'determina']
        for doc_type in types:
            if doc_type in text:
                return doc_type.title()
        
        return None

    def _extract_number(self, container: BeautifulSoup) -> Optional[str]:
        """Estrae numero dal container."""
        text = container.get_text()
        
        # Pattern per numeri
        patterns = [
            r'\bn[\.\s]*(\d+)',  # n. 123
            r'\bnum[\.\s]*(\d+)',  # num 123
            r'\b(\d+)[\/\-](\d{4})',  # 123/2025
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if len(match.groups()) == 1 else match.group(0)
        
        return None

    def _extract_description(self, container: BeautifulSoup) -> Optional[str]:
        """Estrae descrizione dal container."""
        # Prendi tutto il testo, limitato
        text = container.get_text(strip=True)
        if text:
            return text[:500] + ('...' if len(text) > 500 else '')
        return None

    def _calculate_confidence_score(
        self, 
        title: str, 
        search_params: SearchParameters,
        date: Optional[str] = None,
        document_type: Optional[str] = None,
        number: Optional[str] = None,
        description: Optional[str] = None
    ) -> float:
        """
        Calcola confidence score per un risultato.
        
        Args:
            title: Titolo del risultato
            search_params: Parametri ricerca originali
            date, document_type, number, description: Campi estratti
            
        Returns:
            Confidence score 0.0-1.0
        """
        score = 0.0
        max_score = 0.0
        
        title_lower = title.lower()
        oggetto_lower = search_params.oggetto.lower()
        
        # Match oggetto (peso maggiore)
        oggetto_words = set(w for w in oggetto_lower.split() if len(w) > 3)
        title_words = set(w for w in title_lower.split() if len(w) > 3)
        
        if oggetto_words and title_words:
            word_match_ratio = len(oggetto_words & title_words) / len(oggetto_words | title_words)
            score += word_match_ratio * 0.4
        max_score += 0.4
        
        # Match numero
        if number and search_params.numero in number:
            score += 0.3
        max_score += 0.3
        
        # Match tipo documento
        if document_type and 'delibera' in document_type.lower():
            score += 0.1
        max_score += 0.1
        
        # Match anno (se presente)
        if date and search_params.anno and search_params.anno in date:
            score += 0.1
        max_score += 0.1
        
        # Fuzzy match complessivo titolo-oggetto
        fuzzy_ratio = difflib.SequenceMatcher(None, title_lower, oggetto_lower).ratio()
        score += fuzzy_ratio * 0.1
        max_score += 0.1
        
        # Normalizza score
        final_score = score / max_score if max_score > 0 else 0.0
        
        return min(1.0, final_score)

    def verify_decreto_publication(
        self, 
        seduta: str, 
        numero: str, 
        oggetto: str,
        anno: Optional[str] = None,
        data_sottoscrizione: Optional[str] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Verifica pubblicazione decreto - metodo principale.
        
        Args:
            seduta: Numero seduta
            numero: Numero deliberazione
            oggetto: Oggetto deliberazione
            anno: Anno (opzionale)
            data_sottoscrizione: Data sottoscrizione (opzionale)
            
        Returns:
            Tuple (trovato: bool, url: str, confidence: float)
        """
        self.logger.info(f"Verifying decreto publication - Seduta: {seduta}, Numero: {numero}")
        
        try:
            # 1. Analizza form se necessario
            if not self.form_structure:
                self.analyze_form_structure()
            
            # 2. Costruisci parametri ricerca
            search_params = SearchParameters(
                seduta=seduta,
                numero=numero,
                oggetto=oggetto,
                anno=anno or "2025",
                data_sottoscrizione=data_sottoscrizione,
                tipo_atto="Deliberazione"
            )
            
            # 3. Costruisci form data
            form_data = self.build_form_data(search_params)
            
            # 4. Invia ricerca
            response = self.submit_search_form(form_data)
            
            # 5. Parse risultati
            results = self.parse_search_results(response.text, search_params)
            
            # 6. Trova migliore match
            if results:
                best_result = results[0]  # Già ordinati per confidence
                self.logger.info(f"Best match found: {best_result.title[:50]}... (confidence: {best_result.confidence_score:.2f})")
                return True, best_result.url, best_result.confidence_score
            else:
                self.logger.info("No matching results found")
                return False, None, 0.0
                
        except Exception as e:
            self.logger.error(f"Decreto verification failed: {e}")
            return False, None, 0.0

    def _log_form_structure(self, form_structure: FormStructure):
        """Log struttura form per debug."""
        self.logger.debug("=== FORM STRUCTURE ===")
        self.logger.debug(f"Action: {form_structure.action_url}")
        self.logger.debug(f"Method: {form_structure.method}")
        
        if form_structure.hidden_fields:
            self.logger.debug("Hidden fields:")
            for name, value in form_structure.hidden_fields.items():
                self.logger.debug(f"  {name}: {value}")
        
        self.logger.debug("Form fields:")
        for name, field in form_structure.fields.items():
            if field.field_type == 'select':
                self.logger.debug(f"  {name} (select): {len(field.options)} options")
                if self.log_level == LogLevel.TRACE:
                    for value, label in list(field.options.items())[:5]:  # Show first 5
                        self.logger.debug(f"    {value}: {label}")
            else:
                self.logger.debug(f"  {name} ({field.field_type}): {field.placeholder or 'N/A'}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche performance."""
        avg_response_time = (
            self.total_response_time / self.request_count if self.request_count > 0 else 0.0
        )
        
        return {
            'total_requests': self.request_count,
            'successful_requests': self.success_count,
            'failed_requests': self.error_count,
            'success_rate': self.success_count / max(1, self.request_count),
            'average_response_time': avg_response_time,
            'form_structure_cached': self.form_structure is not None,
            'cache_age_minutes': (
                (datetime.now() - self.form_analysis_timestamp).total_seconds() / 60
                if self.form_analysis_timestamp else None
            )
        }

    @contextmanager
    def session_context(self):
        """Context manager per gestione sessione."""
        start_time = time.time()
        self.logger.debug("Starting decreto scraper session")
        
        try:
            yield self
        finally:
            duration = time.time() - start_time
            stats = self.get_performance_stats()
            self.logger.info(f"Session completed in {duration:.2f}s - Stats: {stats}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(f"Session ended with error: {exc_type.__name__}: {exc_val}")
        else:
            self.logger.debug("Session completed successfully")


# Compatibility class per backward compatibility
class DecretoScraper(DecretoScraperAdvanced):
    """Alias per backward compatibility."""
    pass


if __name__ == "__main__":
    # Test example
    with DecretoScraperAdvanced(debug_mode=True, log_level=LogLevel.DEBUG) as scraper:
        found, url, confidence = scraper.verify_decreto_publication(
            seduta="3929",
            numero="17",
            oggetto="Approvazione piano triennale lavori pubblici"
        )
        
        print(f"Found: {found}")
        print(f"URL: {url}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Stats: {scraper.get_performance_stats()}")